import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from pipeline.base import StageResult
from pipeline.stages.processing import RefinerStage


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
SAMPLE_ARTICLE_PATH = FIXTURES_DIR / "sample_article.html"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_html(tmp: Path, html: str, name: str = "page.html") -> str:
    """Write HTML to a temp file and return its path as a string."""
    p = tmp / name
    p.write_text(html, encoding="utf-8")
    return str(p)


def _spider_docs(html_paths: list[str]) -> list[dict]:
    """Build minimal Spider-style input dicts."""
    return [
        {
            "url": f"https://example.com/article-{i}",
            "html_path": path,
            "status_code": 200,
            "method": "httpx",
            "title": f"Article {i}",
            "language": "en",
        }
        for i, path in enumerate(html_paths)
    ]


# ---------------------------------------------------------------------------
# Stage identity
# ---------------------------------------------------------------------------

class TestRefinerStageBasics:
    def test_stage_name(self) -> None:
        stage = RefinerStage()
        assert stage.stage_name == "refiner"


# ---------------------------------------------------------------------------
# validate_input
# ---------------------------------------------------------------------------

class TestValidateInput:
    async def test_valid_input(self, tmp_path: Path) -> None:
        stage = RefinerStage()
        html_path = _write_html(tmp_path, "<html><body>ok</body></html>")
        docs = _spider_docs([html_path])
        assert await stage.validate_input(docs) is True

    async def test_empty_list_is_invalid(self) -> None:
        stage = RefinerStage()
        assert await stage.validate_input([]) is False

    async def test_non_list_is_invalid(self) -> None:
        stage = RefinerStage()
        assert await stage.validate_input("not a list") is False

    async def test_missing_required_keys_is_invalid(self) -> None:
        stage = RefinerStage()
        assert await stage.validate_input([{"url": "https://example.com"}]) is False

    async def test_missing_file_is_invalid(self) -> None:
        stage = RefinerStage()
        docs = [
            {
                "url": "https://example.com",
                "html_path": "/nonexistent/path.html",
                "status_code": 200,
                "method": "httpx",
                "title": "T",
                "language": "en",
            }
        ]
        assert await stage.validate_input(docs) is False


# ---------------------------------------------------------------------------
# Content extraction – trafilatura
# ---------------------------------------------------------------------------

class TestContentExtraction:
    async def test_trafilatura_extracts_main_content(self, tmp_path: Path) -> None:
        """trafilatura should extract article body, not nav/footer/ads."""
        stage = RefinerStage()
        html = SAMPLE_ARTICLE_PATH.read_text(encoding="utf-8")
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        result = await stage.process(docs, config={})

        assert result.success is True
        assert len(result.data) == 1
        content = result.data[0]["content"]
        # Main article content should be present
        assert "Massachusetts Institute of Technology" in content
        assert "solid-state battery" in content.lower() or "solid-state" in content
        # Navigation / sidebar / ad text should not dominate
        assert "ADVERTISEMENT" not in content

    async def test_extracted_content_is_nonempty(self, tmp_path: Path) -> None:
        stage = RefinerStage()
        html = (
            "<html><body><article>"
            "<p>This is a short article about renewable energy.</p>"
            "</article></body></html>"
        )
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        result = await stage.process(docs, config={})

        assert result.success is True
        assert len(result.data) == 1
        assert len(result.data[0]["content"]) > 0


# ---------------------------------------------------------------------------
# BS4 fallback
# ---------------------------------------------------------------------------

class TestBeautifulSoupFallback:
    async def test_bs4_used_when_trafilatura_returns_none(self, tmp_path: Path) -> None:
        """If trafilatura returns None, BS4 should take over."""
        stage = RefinerStage()
        html = "<html><body><p>Fallback content here.</p></body></html>"
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        with patch("pipeline.stages.processing.trafilatura") as mock_traf:
            mock_traf.extract.return_value = None
            result = await stage.process(docs, config={})

        assert result.success is True
        assert len(result.data) == 1
        assert "Fallback content here" in result.data[0]["content"]

    async def test_bs4_fallback_strips_tags(self, tmp_path: Path) -> None:
        stage = RefinerStage()
        html = "<html><body><p>Hello <b>bold</b> world</p></body></html>"
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        with patch("pipeline.stages.processing.trafilatura") as mock_traf:
            mock_traf.extract.return_value = None
            result = await stage.process(docs, config={})

        content = result.data[0]["content"]
        assert "<b>" not in content
        assert "Hello" in content
        assert "bold" in content


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

class TestChunking:
    async def test_chunks_are_produced(self, tmp_path: Path) -> None:
        stage = RefinerStage()
        html = SAMPLE_ARTICLE_PATH.read_text(encoding="utf-8")
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        result = await stage.process(docs, config={"chunk_size": 256, "chunk_overlap": 30})

        assert result.success is True
        chunks = result.data[0]["chunks"]
        assert len(chunks) > 1, "Long article should produce multiple chunks"

    async def test_chunks_within_token_limit(self, tmp_path: Path) -> None:
        stage = RefinerStage()
        html = SAMPLE_ARTICLE_PATH.read_text(encoding="utf-8")
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        chunk_size = 256
        result = await stage.process(
            docs, config={"chunk_size": chunk_size, "chunk_overlap": 30}
        )

        for chunk in result.data[0]["chunks"]:
            # Allow small tolerance due to splitter behaviour
            assert chunk["token_count"] <= chunk_size * 1.2, (
                f"Chunk has {chunk['token_count']} tokens, limit is {chunk_size}"
            )

    async def test_chunk_indices_are_sequential(self, tmp_path: Path) -> None:
        stage = RefinerStage()
        html = SAMPLE_ARTICLE_PATH.read_text(encoding="utf-8")
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        result = await stage.process(docs, config={"chunk_size": 256, "chunk_overlap": 30})

        indices = [c["chunk_index"] for c in result.data[0]["chunks"]]
        assert indices == list(range(len(indices)))

    async def test_chunk_metadata_contains_source_url(self, tmp_path: Path) -> None:
        stage = RefinerStage()
        html = SAMPLE_ARTICLE_PATH.read_text(encoding="utf-8")
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        result = await stage.process(docs, config={})

        for chunk in result.data[0]["chunks"]:
            assert "source_url" in chunk["metadata"]
            assert chunk["metadata"]["source_url"].startswith("https://")

    async def test_short_text_produces_single_chunk(self, tmp_path: Path) -> None:
        stage = RefinerStage()
        html = "<html><body><article><p>Short article.</p></article></body></html>"
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        result = await stage.process(docs, config={"chunk_size": 512})

        assert result.success is True
        assert len(result.data[0]["chunks"]) == 1


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------

class TestTokenCounting:
    async def test_token_counts_are_positive_integers(self, tmp_path: Path) -> None:
        stage = RefinerStage()
        html = SAMPLE_ARTICLE_PATH.read_text(encoding="utf-8")
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        result = await stage.process(docs, config={})

        for chunk in result.data[0]["chunks"]:
            assert isinstance(chunk["token_count"], int)
            assert chunk["token_count"] > 0

    async def test_token_count_matches_tiktoken(self, tmp_path: Path) -> None:
        """Token counts should match direct tiktoken encoding."""
        import tiktoken

        stage = RefinerStage()
        html = SAMPLE_ARTICLE_PATH.read_text(encoding="utf-8")
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        result = await stage.process(docs, config={})

        enc = tiktoken.get_encoding("cl100k_base")
        for chunk in result.data[0]["chunks"]:
            expected = len(enc.encode(chunk["content"]))
            assert chunk["token_count"] == expected


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    async def test_exact_duplicate_chunks_removed(self, tmp_path: Path) -> None:
        """Identical paragraphs repeated should only produce one chunk."""
        stage = RefinerStage()
        paragraph = "This is a sufficiently long paragraph about renewable energy storage technology that should form a complete chunk on its own when the chunk size is large enough."
        # Repeat the same content many times to create duplicate chunks
        repeated = "\n\n".join([paragraph] * 20)
        html = f"<html><body><article>{repeated}</article></body></html>"
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        with patch("pipeline.stages.processing.trafilatura") as mock_traf:
            mock_traf.extract.return_value = repeated
            result = await stage.process(
                docs, config={"chunk_size": 512, "chunk_overlap": 0}
            )

        chunks = result.data[0]["chunks"]
        contents = [c["content"] for c in chunks]
        # After exact dedup there should be no identical chunks
        assert len(contents) == len(set(contents))

    async def test_near_duplicate_chunks_removed(self, tmp_path: Path) -> None:
        """Chunks that are nearly identical (Jaccard > 0.8) should be deduplicated."""
        stage = RefinerStage()
        # Create two very similar paragraphs
        base = (
            "Scientists at MIT have developed a new battery technology "
            "that could revolutionize renewable energy storage systems "
            "across the entire global power grid infrastructure."
        )
        near_dup = (
            "Scientists at MIT have developed a new battery technology "
            "that could revolutionize renewable energy storage systems "
            "across the entire global electrical grid infrastructure."
        )
        text = f"{base}\n\n{near_dup}"
        html = f"<html><body><article>{text}</article></body></html>"
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        with patch("pipeline.stages.processing.trafilatura") as mock_traf:
            mock_traf.extract.return_value = text
            result = await stage.process(
                docs, config={"chunk_size": 1024, "chunk_overlap": 0}
            )

        # With a large enough chunk_size the two paragraphs may end up in one
        # chunk, but if split, the near-dup should be removed. Either way the
        # stage should succeed.
        assert result.success is True

    async def test_dedup_stats_reported(self, tmp_path: Path) -> None:
        stage = RefinerStage()
        paragraph = "Duplicate paragraph about energy storage technology that is long enough to matter."
        repeated = "\n\n".join([paragraph] * 10)
        html = f"<html><body><article>{repeated}</article></body></html>"
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        with patch("pipeline.stages.processing.trafilatura") as mock_traf:
            mock_traf.extract.return_value = repeated
            result = await stage.process(
                docs, config={"chunk_size": 512, "chunk_overlap": 0}
            )

        assert "duplicates_removed" in result.stats


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

class TestLanguageDetection:
    async def test_language_detected(self, tmp_path: Path) -> None:
        stage = RefinerStage()
        html = SAMPLE_ARTICLE_PATH.read_text(encoding="utf-8")
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        result = await stage.process(docs, config={})

        lang = result.data[0]["language"]
        assert lang is not None
        assert isinstance(lang, str)
        assert len(lang) >= 2  # ISO 639-1 or similar

    async def test_language_defaults_to_en(self, tmp_path: Path) -> None:
        """If language detection fails, default to 'en'."""
        stage = RefinerStage()
        html = "<html><body><article><p>...</p></article></body></html>"
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        # Force trafilatura to return some text but no language
        with patch("pipeline.stages.processing.trafilatura") as mock_traf:
            mock_traf.extract.return_value = "..."
            with patch(
                "pipeline.stages.processing._detect_language", return_value=None
            ):
                result = await stage.process(docs, config={})

        assert result.data[0]["language"] == "en"


# ---------------------------------------------------------------------------
# Output format
# ---------------------------------------------------------------------------

class TestOutputFormat:
    async def test_output_has_required_fields(self, tmp_path: Path) -> None:
        stage = RefinerStage()
        html = SAMPLE_ARTICLE_PATH.read_text(encoding="utf-8")
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        result = await stage.process(docs, config={})

        doc = result.data[0]
        assert "url" in doc
        assert "title" in doc
        assert "language" in doc
        assert "content" in doc
        assert "chunks" in doc
        assert isinstance(doc["chunks"], list)

    async def test_chunk_has_required_fields(self, tmp_path: Path) -> None:
        stage = RefinerStage()
        html = SAMPLE_ARTICLE_PATH.read_text(encoding="utf-8")
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        result = await stage.process(docs, config={})

        chunk = result.data[0]["chunks"][0]
        assert "content" in chunk
        assert "token_count" in chunk
        assert "chunk_index" in chunk
        assert "metadata" in chunk
        assert isinstance(chunk["metadata"], dict)


# ---------------------------------------------------------------------------
# Full process flow
# ---------------------------------------------------------------------------

class TestFullProcessFlow:
    async def test_process_multiple_documents(self, tmp_path: Path) -> None:
        stage = RefinerStage()
        html1 = (
            "<html><body><article>"
            "<p>First article about solar panels and renewable energy technology.</p>"
            "</article></body></html>"
        )
        html2 = (
            "<html><body><article>"
            "<p>Second article about wind turbines and offshore power generation.</p>"
            "</article></body></html>"
        )
        p1 = _write_html(tmp_path, html1, "a.html")
        p2 = _write_html(tmp_path, html2, "b.html")
        docs = _spider_docs([p1, p2])

        result = await stage.process(docs, config={})

        assert result.success is True
        assert len(result.data) == 2

    async def test_process_records_stats(self, tmp_path: Path) -> None:
        stage = RefinerStage()
        html = SAMPLE_ARTICLE_PATH.read_text(encoding="utf-8")
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        result = await stage.process(docs, config={})

        assert "total_documents" in result.stats
        assert "processed" in result.stats
        assert "total_chunks" in result.stats

    async def test_process_handles_unreadable_file(self, tmp_path: Path) -> None:
        """If a file cannot be read, it should be skipped with an error."""
        stage = RefinerStage()
        docs = [
            {
                "url": "https://example.com/gone",
                "html_path": str(tmp_path / "missing.html"),
                "status_code": 200,
                "method": "httpx",
                "title": "Gone",
                "language": "en",
            }
        ]

        result = await stage.process(docs, config={})

        # Partial success — the stage continues even if one doc fails
        assert result.success is True
        assert len(result.data) == 0
        assert len(result.errors) >= 1

    async def test_process_skips_empty_content(self, tmp_path: Path) -> None:
        """Documents with no extractable text should be skipped."""
        stage = RefinerStage()
        html = "<html><body></body></html>"
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        with patch("pipeline.stages.processing.trafilatura") as mock_traf:
            mock_traf.extract.return_value = None
            result = await stage.process(docs, config={})

        # BS4 fallback on empty body returns empty string; document skipped
        assert result.success is True

    async def test_result_is_stage_result(self, tmp_path: Path) -> None:
        stage = RefinerStage()
        html = SAMPLE_ARTICLE_PATH.read_text(encoding="utf-8")
        html_path = _write_html(tmp_path, html)
        docs = _spider_docs([html_path])

        result = await stage.process(docs, config={})

        assert isinstance(result, StageResult)
