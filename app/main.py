from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app import models
from app.analysis import analyze_text
from app.database import Base, engine, get_db
from app.extraction import ExtractionError, extract_article
from app.schemas import AnalysisDetail, AnalysisSummary, AnalyzeRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger("content_analyzer")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Content Analyzer",
    description="Extracts article text from any URL and runs sentiment + readability analysis on it.",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalysisDetail)
def analyze(payload: AnalyzeRequest, db: Session = Depends(get_db)):
    url = str(payload.url)
    try:
        article = extract_article(url)
    except ExtractionError as exc:
        logger.warning("Extraction failed for %s: %s", url, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        metrics = analyze_text(article.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    record = models.Analysis(url=url, title=article.title, text=article.text, metrics=metrics)
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info("Analyzed %s (id=%s)", url, record.id)
    return record


@app.get("/analyses", response_model=list[AnalysisSummary])
def list_analyses(limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 100))
    return (
        db.query(models.Analysis)
        .order_by(models.Analysis.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@app.get("/analyses/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    record = db.get(models.Analysis, analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return record


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")
