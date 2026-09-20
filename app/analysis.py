"""
Text analysis: sentiment and readability metrics for a piece of text.

Sentiment uses VADER (vaderSentiment), a rule-based sentiment model tuned for
general text. Readability uses textstat, which implements the standard
published formulas (Flesch Reading Ease, Flesch-Kincaid Grade, Gunning Fog,
SMOG, Automated Readability Index). A couple of small custom metrics
(personal pronoun count, average word length, syllables per word) are
computed directly since they're not part of textstat's API.
"""

from __future__ import annotations

import re

import textstat
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

# Case-sensitive on purpose: matches I/we/my/ours/us but not the all-caps
# country name "US".
PERSONAL_PRONOUN_RE = re.compile(r"\b(I|we|We|my|My|ours|Ours|us|Us)\b")

_WORD_RE = re.compile(r"[A-Za-z']+")


def _count_syllables(word: str) -> int:
    """Approximate syllable count via vowel-group counting."""
    word = word.lower()
    vowels = "aeiouy"
    count = 0
    prev_was_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_was_vowel:
            count += 1
        prev_was_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def analyze_text(text: str) -> dict:
    """Return a dict of sentiment + readability + basic count metrics for `text`."""
    if not text or not text.strip():
        raise ValueError("Cannot analyze empty text")

    words = _WORD_RE.findall(text)
    word_count = max(len(words), 1)

    sentence_count = max(textstat.sentence_count(text), 1)
    avg_sentence_length = word_count / sentence_count
    avg_word_length = sum(len(w) for w in words) / word_count
    syllables_per_word = sum(_count_syllables(w) for w in words) / word_count
    personal_pronouns = len(PERSONAL_PRONOUN_RE.findall(text))

    sentiment = _analyzer.polarity_scores(text)

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_sentence_length": round(avg_sentence_length, 2),
        "avg_word_length": round(avg_word_length, 2),
        "syllables_per_word": round(syllables_per_word, 2),
        "personal_pronouns": personal_pronouns,
        "sentiment": {
            "positive": sentiment["pos"],
            "neutral": sentiment["neu"],
            "negative": sentiment["neg"],
            "compound": sentiment["compound"],
        },
        "readability": {
            "flesch_reading_ease": textstat.flesch_reading_ease(text),
            "flesch_kincaid_grade": textstat.flesch_kincaid_grade(text),
            "gunning_fog": textstat.gunning_fog(text),
            "smog_index": textstat.smog_index(text),
            "automated_readability_index": textstat.automated_readability_index(text),
        },
    }
