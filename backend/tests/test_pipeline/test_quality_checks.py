"""Tests for coherence and length_balance quality checkers."""

import sys
import pytest
from unittest.mock import patch, MagicMock
import numpy as np

from pipeline.quality_checks.length_balance import LengthBalanceChecker
from pipeline.quality_checks.coherence import CoherenceChecker


# --- LengthBalanceChecker tests (no external deps) ---

async def test_length_balance_balanced() -> None:
    """Balanced input/output gets score 1.0."""
    checker = LengthBalanceChecker()
    example = {
        "input": "What is machine learning?",
        "output": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed.",
    }
    score, detail = await checker.check(example)
    assert score == 1.0
    assert "balanced" in detail


async def test_length_balance_empty_output() -> None:
    """Empty output gets score 0.0."""
    checker = LengthBalanceChecker()
    score, detail = await checker.check({"input": "some text", "output": ""})
    assert score == 0.0
    assert "empty output" in detail


async def test_length_balance_empty_input() -> None:
    """Empty input gets score 0.3."""
    checker = LengthBalanceChecker()
    score, detail = await checker.check({"input": "", "output": "some output text"})
    assert score == 0.3
    assert "empty input" in detail


async def test_length_balance_both_empty() -> None:
    """Both empty gets score 0.5."""
    checker = LengthBalanceChecker()
    score, detail = await checker.check({"input": "", "output": ""})
    assert score == 0.5


async def test_length_balance_very_long_output() -> None:
    """Very long output relative to input degrades score."""
    checker = LengthBalanceChecker()
    example = {
        "input": "Hello",
        "output": " ".join(["word"] * 500),  # 500 words vs 1 word = 500x ratio
    }
    score, detail = await checker.check(example)
    assert score < 1.0
    assert "too long" in detail


async def test_length_balance_very_short_output() -> None:
    """Very short output relative to input degrades score."""
    checker = LengthBalanceChecker()
    example = {
        "input": " ".join(["word"] * 100),  # 100 words
        "output": "yes",  # 1 word = 0.01x ratio
    }
    score, detail = await checker.check(example)
    assert score < 1.0
    assert "too short" in detail


# --- CoherenceChecker tests (mock sentence-transformers) ---

async def test_coherence_high_similarity() -> None:
    """High cosine similarity yields high coherence score."""
    checker = CoherenceChecker()

    # Mock the model to return similar embeddings
    mock_model = MagicMock()
    # Two very similar unit vectors
    vec1 = np.array([1.0, 0.0, 0.0])
    vec2 = np.array([0.95, 0.31, 0.0])  # cos_sim ≈ 0.95
    mock_model.encode.return_value = np.array([vec1, vec2])
    checker._model = mock_model

    score, detail = await checker.check({
        "input": "What is ML?",
        "output": "ML is machine learning.",
    })
    assert score >= 0.7
    assert "highly coherent" in detail


async def test_coherence_low_similarity() -> None:
    """Low cosine similarity yields low coherence score."""
    checker = CoherenceChecker()

    mock_model = MagicMock()
    # Two orthogonal vectors
    vec1 = np.array([1.0, 0.0, 0.0])
    vec2 = np.array([0.0, 1.0, 0.0])  # cos_sim = 0.0
    mock_model.encode.return_value = np.array([vec1, vec2])
    checker._model = mock_model

    score, detail = await checker.check({
        "input": "What is ML?",
        "output": "The weather is nice.",
    })
    assert score < 0.4
    assert "low coherence" in detail


async def test_coherence_missing_text() -> None:
    """Missing input or output returns 0.5."""
    checker = CoherenceChecker()
    score, detail = await checker.check({"input": "", "output": "some text"})
    assert score == 0.5
    assert "missing" in detail


async def test_coherence_lazy_model_load() -> None:
    """Model is loaded lazily on first _get_model call."""
    checker = CoherenceChecker()
    assert checker._model is None

    # sentence_transformers may not be installed in test env, so we
    # inject a fake module into sys.modules with a mock constructor.
    mock_st_class = MagicMock()
    mock_st_class.return_value = MagicMock()
    fake_module = MagicMock(SentenceTransformer=mock_st_class)

    with patch.dict(sys.modules, {"sentence_transformers": fake_module}):
        model = checker._get_model()
        mock_st_class.assert_called_once_with("all-MiniLM-L6-v2")
        assert model is not None
        # Second call doesn't re-instantiate -- cached on checker._model
        checker._get_model()
        mock_st_class.assert_called_once()  # Still just 1 call
