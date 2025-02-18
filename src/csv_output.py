# src/csv_output.py
import pandas as pd
import logging


def output_repo_stats_csv(df: pd.DataFrame, filename: str) -> None:
    """
    リポジトリ統計 DataFrame を CSV ファイルに出力する。
    """
    try:
        df.to_csv(filename, index=False, encoding="utf-8")
        logging.info(f"CSVファイル出力完了: {filename}")
    except Exception as e:
        logging.error(f"CSVファイル出力エラー ({filename}): {e}")


def output_user_stats_csv(df: pd.DataFrame, filename: str) -> None:
    """
    ユーザー統計 DataFrame を CSV ファイルに出力する。
    """
    try:
        df.to_csv(filename, index=False, encoding="utf-8")
        logging.info(f"CSVファイル出力完了: {filename}")
    except Exception as e:
        logging.error(f"CSVファイル出力エラー ({filename}): {e}")
