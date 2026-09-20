import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main
from app.database import Base, get_db
from app.extraction import ExtractedArticle, ExtractionError

# --- isolated, file-based test database (fresh for every test run) ---
TEST_DB_URL = "sqlite:///./test_content_analyzer.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


main.app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


client = TestClient(main.app)

SAMPLE_ARTICLE = ExtractedArticle(
    url="https://example.com/great-news",
    title="Great News For Everyone",
    text=(
        "This is genuinely wonderful news for the whole team. "
        "We are thrilled about the results and I could not be happier. "
        "The launch went smoothly and customers love the product."
    ),
)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_analyze_success(monkeypatch):
    monkeypatch.setattr(main, "extract_article", lambda url: SAMPLE_ARTICLE)

    res = client.post("/analyze", json={"url": "https://example.com/great-news"})
    assert res.status_code == 200

    body = res.json()
    assert body["title"] == SAMPLE_ARTICLE.title
    assert body["metrics"]["word_count"] > 0
    assert body["metrics"]["sentiment"]["compound"] > 0


def test_analyze_extraction_failure_returns_422(monkeypatch):
    def raise_error(url):
        raise ExtractionError("could not find article content")

    monkeypatch.setattr(main, "extract_article", raise_error)

    res = client.post("/analyze", json={"url": "https://example.com/nope"})
    assert res.status_code == 422
    assert "could not find article content" in res.json()["detail"]


def test_list_and_get_analysis(monkeypatch):
    monkeypatch.setattr(main, "extract_article", lambda url: SAMPLE_ARTICLE)

    created = client.post("/analyze", json={"url": "https://example.com/great-news"}).json()

    listed = client.get("/analyses").json()
    assert any(item["id"] == created["id"] for item in listed)

    fetched = client.get(f"/analyses/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["text"] == SAMPLE_ARTICLE.text


def test_get_nonexistent_analysis_returns_404():
    res = client.get("/analyses/999999")
    assert res.status_code == 404


def test_analyze_rejects_invalid_url():
    res = client.post("/analyze", json={"url": "not-a-url"})
    assert res.status_code == 422
