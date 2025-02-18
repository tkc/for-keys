# src/analytics.py
import pandas as pd
from typing import List
from data_models import CommitRecord, PRRecord


def aggregate_commit_records(records: List[CommitRecord]) -> pd.DataFrame:
    """
    CommitRecord のリストをリポジトリ、ユーザー、週単位で集計し、合計コミット数を計算して DataFrame に変換する。
    """
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame([record.dict() for record in records])
    grouped = (
        df.groupby(["repo", "user", "week"], dropna=False)["commit_count"]
        .sum()
        .reset_index()
    )
    return grouped


def aggregate_pr_records(pr_records: List[PRRecord]) -> pd.DataFrame:
    """
    PRRecord のリストをリポジトリ、ユーザー、週単位で集計し、PR 作成件数、クローズ件数、および PR 消化率を計算して DataFrame に変換する。
    """
    if not pr_records:
        return pd.DataFrame()
    df = pd.DataFrame([record.dict() for record in pr_records])
    grouped = (
        df.groupby(["repo", "user", "week"], dropna=False)
        .agg({"pr_created": "sum", "pr_closed": "sum"})
        .reset_index()
    )
    grouped["pr_consumption_rate"] = grouped.apply(
        lambda row: row["pr_closed"] / row["pr_created"]
        if row["pr_created"] > 0
        else None,
        axis=1,
    )
    return grouped


def merge_metrics(df_commits: pd.DataFrame, df_pr: pd.DataFrame) -> pd.DataFrame:
    """
    コミット記録と PR 記録をリポジトリ、ユーザー、週単位でマージし、統合した DataFrame を返す。
    """
    merged = pd.merge(df_commits, df_pr, on=["repo", "user", "week"], how="outer")
    merged = merged.fillna(0)
    # PR 消化率を再計算（もし outer merge により一部欠損した場合）
    merged["pr_consumption_rate"] = merged.apply(
        lambda row: row["pr_closed"] / row["pr_created"]
        if row["pr_created"] > 0
        else None,
        axis=1,
    )
    return merged
