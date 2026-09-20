import pytest

from app.analysis import analyze_text


def test_word_and_sentence_counts():
    text = "This is a short sentence. Here is another one."
    metrics = analyze_text(text)
    assert metrics["word_count"] == 9
    assert metrics["sentence_count"] == 2


def test_personal_pronouns_excludes_country_us():
    text = "We went to the US for a conference. I told my colleagues about it."
    metrics = analyze_text(text)
    # "We", "I", "my" should count; the all-caps "US" (country) should not.
    assert metrics["personal_pronouns"] == 3


def test_sentiment_detects_positive_text():
    text = "This is wonderful, amazing, and truly excellent work by the whole team."
    metrics = analyze_text(text)
    assert metrics["sentiment"]["compound"] > 0.5


def test_sentiment_detects_negative_text():
    text = "This is terrible, disappointing, and a complete failure in every way."
    metrics = analyze_text(text)
    assert metrics["sentiment"]["compound"] < -0.5


def test_empty_text_raises():
    with pytest.raises(ValueError):
        analyze_text("")
    with pytest.raises(ValueError):
        analyze_text("   ")


def test_readability_metrics_present():
    text = "The quick brown fox jumps over the lazy dog. " * 5
    metrics = analyze_text(text)
    for key in (
        "flesch_reading_ease",
        "flesch_kincaid_grade",
        "gunning_fog",
        "smog_index",
        "automated_readability_index",
    ):
        assert key in metrics["readability"]
