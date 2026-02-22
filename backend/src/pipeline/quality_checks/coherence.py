"""Coherence quality checker using sentence-transformers embeddings."""

from __future__ import annotations

from pipeline.quality_checks import QualityChecker


class CoherenceChecker(QualityChecker):
    """Measures semantic coherence between input and output using cosine similarity.

    Uses sentence-transformers with the all-MiniLM-L6-v2 model (79MB).
    The model is loaded lazily on first use to avoid startup overhead.
    """

    name = "coherence"

    def __init__(self) -> None:
        self._model = None

    def _get_model(self):
        """Lazy-load the sentence transformer model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    async def check(self, example: dict) -> tuple[float, str]:
        input_text = example.get("input", "").strip()
        output_text = example.get("output", "").strip()

        if not input_text or not output_text:
            return 0.5, "missing input or output text"

        model = self._get_model()
        embeddings = model.encode([input_text, output_text])

        # Cosine similarity between input and output embeddings
        import numpy as np
        cos_sim = float(np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        ))

        # Clamp to [0, 1]
        score = max(0.0, min(1.0, cos_sim))

        if score >= 0.7:
            detail = f"highly coherent (similarity: {cos_sim:.3f})"
        elif score >= 0.4:
            detail = f"moderately coherent (similarity: {cos_sim:.3f})"
        else:
            detail = f"low coherence (similarity: {cos_sim:.3f})"

        return score, detail
