# src/data_models.py
from typing import Optional
from pydantic import BaseModel, Field


class CommitRecord(BaseModel):
    repo: str
    user: str
    week: str  # ISO 8601 (YYYY-MM-DD)
    commit_count: int


class PRRecord(BaseModel):
    repo: str
    user: str
    week: str  # ISO 8601 (YYYY-MM-DD)
    pr_created: int
    pr_closed: int

    @property
    def pr_consumption_rate(self) -> Optional[float]:
        return self.pr_closed / self.pr_created if self.pr_created > 0 else None


class RepoUserWeeklyMetrics(BaseModel):
    repo: str
    user: str
    week: str  # ISO 8601 (YYYY-MM-DD)
    commit_count: int = Field(0, ge=0)
    pr_created: int = Field(0, ge=0)
    pr_closed: int = Field(0, ge=0)
    pr_consumption_rate: Optional[float] = None

    def calculate_consumption_rate(self) -> None:
        if self.pr_created > 0:
            self.pr_consumption_rate = self.pr_closed / self.pr_created
        else:
            self.pr_consumption_rate = None


class RepoOverallMetrics(BaseModel):
    repo: str
    commit_count: Optional[int]
    open_pr_count: Optional[int]
    closed_pr_count: Optional[int]
    total_pr_count: int
    pr_consumption_rate: Optional[float]
