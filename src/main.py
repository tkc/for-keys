import os
import logging
import pandas as pd
from typing import List, Dict, Any, Optional
from src.env import GITHUB_TOKEN
from src.github_client import GithubClient
from src.data_models import (
    CommitRecord,
    PRRecord,
    RepoOverallMetrics,
    RepoUserWeeklyMetrics,
)
from src.analytics import aggregate_commit_records, aggregate_pr_records, merge_metrics
from src.csv_output import output_repo_stats_csv, output_user_stats_csv
from tqdm import tqdm  # tqdm をインポート

# --- ロギング設定 ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

ORG_NAME: str = "langchain-ai"  # 組織名（例）


def main() -> None:
    """
    メイン処理関数。
    GitHub API から組織リポジトリの情報を取得し、集計して CSV ファイルに出力します。
    """
    logging.info("開始: GitHub Organization Stats 収集処理")

    github_client = GithubClient(GITHUB_TOKEN)

    try:
        # 組織内のリポジトリ一覧を取得
        repos: List[Dict[str, Any]] = github_client.get_org_repos(ORG_NAME)
        logging.info(f"取得リポジトリ数: {len(repos)}")

        all_commit_records: List[CommitRecord] = []
        all_pr_records: List[PRRecord] = []
        overall_repo_results: List[RepoOverallMetrics] = []

        # 各リポジトリについて処理 (tqdm で進捗表示)
        for repo in tqdm(repos, desc="Processing Repositories"):
            repo_name: str = repo["name"]
            owner: str = repo["owner"]["login"]
            logging.info(f"処理中リポジトリ: {owner}/{repo_name}")

            # コミット数集計 (リポジトリ全体)
            logging.info(f"run get_commit_count")
            commit_count: Optional[int] = github_client.get_commit_count(
                owner, repo_name
            )

            # PR 件数集計 (リポジトリ全体)
            logging.info(f"run open_pr_count")
            open_pr_count: Optional[int] = github_client.get_pr_count(
                owner, repo_name, "open"
            )
            logging.info(f"run closed_pr_count")
            closed_pr_count: Optional[int] = github_client.get_pr_count(
                owner, repo_name, "closed"
            )
            logging.info(f"run total_pr_count")
            total_pr_count: int = (open_pr_count or 0) + (closed_pr_count or 0)
            pr_rate: Optional[float] = (
                (closed_pr_count / total_pr_count) if total_pr_count > 0 else None
            )

            # RepoOverallMetrics モデル作成
            repo_overall_metrics = RepoOverallMetrics(
                repo=repo_name,
                commit_count=commit_count,
                open_pr_count=open_pr_count,
                closed_pr_count=closed_pr_count,
                total_pr_count=total_pr_count,
                pr_consumption_rate=pr_rate,
            )
            overall_repo_results.append(repo_overall_metrics)

            # 週間コミット記録を取得
            logging.info(f"run get_commit_records")
            commit_records: List[CommitRecord] = github_client.get_commit_records(
                owner, repo_name
            )
            all_commit_records.extend(commit_records)

            # 週間 PR 記録を取得
            logging.info(f"run get_pr_records")
            pr_records: List[PRRecord] = github_client.get_pr_records(owner, repo_name)
            all_pr_records.extend(pr_records)

        # データフレームに変換・集計
        df_commits: pd.DataFrame = aggregate_commit_records(all_commit_records)
        df_pr: pd.DataFrame = aggregate_pr_records(all_pr_records)
        df_merged_user: pd.DataFrame = merge_metrics(df_commits, df_pr)
        df_overall_repo: pd.DataFrame = pd.DataFrame(
            [result.dict() for result in overall_repo_results]
        )

        # CSV ファイル出力
        output_repo_stats_csv(df_overall_repo, "org_repo_stats.csv")
        output_user_stats_csv(df_merged_user, "org_user_stats.csv")

        logging.info("完了: CSV ファイル出力")

    except Exception as e:
        logging.error(f"エラー発生: {e}", exc_info=True)
        logging.error("処理を中断します。")

    logging.info("終了: GitHub Organization Stats 収集処理")


if __name__ == "__main__":
    main()
