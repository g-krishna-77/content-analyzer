from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class AnalyzeRequest(BaseModel):
    url: HttpUrl


class AnalysisSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: str
    created_at: datetime


class AnalysisDetail(AnalysisSummary):
    model_config = ConfigDict(from_attributes=True)

    text: str
    metrics: dict
