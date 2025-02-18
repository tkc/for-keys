import requests
import datetime
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
from pydantic import ValidationError
from data_models import CommitRecord, PRRecord
import json

BASE_URL: str = "https://api.github.com"


class GithubClient:
    """
    GitHub API クライアントクラス。
    """

    def __init__(self, github_token: str):
        """
        コンストラクタ。GitHub Personal Access Token を設定します。
        """
        self.headers: Dict[str, str] = {"Authorization": f"token {github_token}"}

    def _get_paginated_data(
        self, url: str, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        ページネーションされた API レスポンスを処理する共通メソッド。
        """
        data: List[Dict[str, Any]] = []
        page: int = 1
        while True:
            current_params = params.copy()
            current_params["page"] = page
            response = requests.get(url, headers=self.headers, params=current_params)
            try:
                response.raise_for_status()  # HTTPエラーをチェック
                page_data = response.json()
                if not page_data:
                    break  # 空データはページの終わり
                data.extend(page_data)
                page += 1
            except requests.exceptions.RequestException as e:
                logging.error(f"APIリクエストエラー ({url}): {e}")
                logging.error(f"レスポンス内容: {response.text}")
                break  # エラー発生時はページネーションを中断
        return data

    def _extract_total_from_link_header(self, link_header: str) -> Optional[int]:
        """
        Link ヘッダーから "last" リンクの page パラメータを抽出し、総ページ数の概算を返す。
        """
        if not link_header:
            return None
        links = link_header.split(",")
        for link in links:
            if 'rel="last"' in link:
                parts = link.split(";")[0].strip()
                url = parts.strip("<>")
                parsed = urlparse(url)
                qs = parse_qs(parsed.query)
                if "page" in qs:
                    return int(qs["page"][0])
        return None

    def get_org_repos(self, org: str) -> List[Dict[str, Any]]:
        """
        指定した組織内のリポジトリ一覧を取得する（ページネーション対応、per_page=100）。
        """
        url = f"{BASE_URL}/orgs/{org}/repos"
        params = {"per_page": 100}
        return self._get_paginated_data(url, params)

    def get_commit_count(self, owner: str, repo: str) -> Optional[int]:
        """
        /stats/contributors エンドポイントから、全てのコントリビュータのコミット数を合計する。
        統計情報がまだ生成中の場合は None を返す。
        """
        url = f"{BASE_URL}/repos/{owner}/{repo}/stats/contributors"
        response = requests.get(url, headers=self.headers)
        try:
            response.raise_for_status()
            if response.status_code == 202:
                return None  # 統計情報がまだ生成中
            data = response.json()
            total_commits: int = 0
            for contributor in data:
                total_commits += sum(
                    week_info.get("c", 0) for week_info in contributor.get("weeks", [])
                )
            return total_commits
        except requests.exceptions.RequestException as e:
            logging.error(f"APIリクエストエラー (コミット数取得 {repo}): {e}")
            logging.error(f"レスポンス内容: {response.text}")
            return None
        except json.JSONDecodeError as e:
            logging.error(f"JSONデコードエラー (コミット数取得 {repo}): {e}")
            logging.error(f"レスポンス内容: {response.text}")
            return None

    def get_pr_count(self, owner: str, repo: str, state: str) -> Optional[int]:
        """
        指定リポジトリのプルリクエストの件数を取得する (Link ヘッダーを使用)。
        state: 'open' または 'closed'
        """
        url = f"{BASE_URL}/repos/{owner}/{repo}/pulls"
        params = {"state": state, "per_page": 1}
        response = requests.get(
            url, headers=self.headers, params=params, allow_redirects=True
        )
        try:
            response.raise_for_status()
            link_header: str = response.headers.get("Link", "")
            total_count: Optional[int] = self._extract_total_from_link_header(
                link_header
            )
            return total_count
        except requests.exceptions.RequestException as e:
            logging.error(f"APIリクエストエラー (PR数取得 {repo} - {state}): {e}")
            logging.error(f"レスポンス内容: {response.text}")
            return None

    def get_commit_records(self, owner: str, repo: str) -> List[CommitRecord]:
        """
        /stats/contributors エンドポイントから、各コントリビュータの週間コミット数の記録を取得する。
        各 contributor の "weeks" 配列から、各週のコミット数 (c) を記録します。
        統計情報がまだ生成中の場合は空リストを返します。
        """
        url = f"{BASE_URL}/repos/{owner}/{repo}/stats/contributors"
        response = requests.get(url, headers=self.headers)
        try:
            response.raise_for_status()
            if response.status_code == 202 or not response.text.strip():
                return []  # 統計情報がまだ生成中
            data = response.json()
            records: List[CommitRecord] = []
            for contributor in data:
                user: str = contributor.get("author", {}).get("login", "unknown")
                for week_info in contributor.get("weeks", []):
                    # week_info["w"] は Unix タイムスタンプ (秒)
                    week_start: datetime.date = datetime.datetime.fromtimestamp(
                        week_info.get("w")
                    ).date()
                    commit_count: int = week_info.get("c", 0)
                    try:
                        record = CommitRecord(
                            repo=repo,
                            user=user,
                            week=week_start.isoformat(),
                            commit_count=commit_count,
                        )
                        records.append(record)
                    except ValidationError as e:
                        logging.warning(
                            f"Validation error in commit record: {e}"
                        )  # バリデーションエラーは警告としてログ出力
            return records
        except requests.exceptions.RequestException as e:
            logging.error(f"APIリクエストエラー (コミット記録取得 {repo}): {e}")
            logging.error(f"レスポンス内容: {response.text}")
            return []
        except json.JSONDecodeError as e:
            logging.error(f"JSONデコードエラー (コミット記録取得 {repo}): {e}")
            logging.error(f"レスポンス内容: {response.text}")
            return []

    def get_pr_records(self, owner: str, repo: str) -> List[PRRecord]:
        """
        指定リポジトリの全プルリクエスト (state=all) を取得し、各 PR の作成日をもとに
        1週間単位・ユーザー単位で記録する。
        戻り値は PRRecord のリストです。
        """
        pr_records: List[PRRecord] = []
        url = f"{BASE_URL}/repos/{owner}/{repo}/pulls"
        params = {"state": "all", "per_page": 100}
        prs_data = self._get_paginated_data(url, params)
        for pr in prs_data:
            user: str = pr.get("user", {}).get("login", "unknown")
            created_at_str: Optional[str] = pr.get("created_at")
            if created_at_str:
                created_dt: datetime.datetime = datetime.datetime.fromisoformat(
                    created_at_str.replace("Z", "+00:00")
                )
                # 週の開始日（月曜日）を求める
                week_start: datetime.date = created_dt.date() - datetime.timedelta(
                    days=created_dt.weekday()
                )
                week_str: str = week_start.isoformat()
            else:
                week_str = "unknown"
            pr_state: str = pr.get("state", "unknown").lower()
            # 各 PR を 1件とカウント。closedなら pr_closed=1、そうでなければ 0。
            try:
                record = PRRecord(
                    repo=repo,
                    user=user,
                    week=week_str,
                    pr_created=1,
                    pr_closed=1 if pr_state == "closed" else 0,
                )
                pr_records.append(record)
            except ValidationError as e:
                logging.warning(
                    f"Validation error in PR record: {e}"
                )  # バリデーションエラーは警告としてログ出力
        return pr_records
