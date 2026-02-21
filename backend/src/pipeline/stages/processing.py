"""Refiner stage: extract clean text from raw HTML, chunk, count tokens, deduplicate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import tiktoken
import trafilatura
from bs4 import BeautifulSoup
from datasketch import MinHash, MinHashLSH
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from pipeline.base import PipelineStage, StageResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REQUIRED_INPUT_KEYS = {"url", "html_path", "status_code", "method", "title", "language"}


def _get_encoding() -> tiktoken.Encoding:
    """Return the cl100k_base encoding used for token counting.

    We use ``cl100k_base`` explicitly so that the splitter and the token
    counter share the same vocabulary (``from_tiktoken_encoder`` also
    receives ``encoding_name="cl100k_base"``).
    """
    return tiktoken.get_encoding("cl100k_base")


def _detect_language(text: str) -> str | None:
    """Detect language of *text* using trafilatura utilities.

    Returns an ISO-639-1 language code or ``None`` if detection fails.
    """
    try:
        from trafilatura.utils import detect_language as _traf_detect
        return _traf_detect(text)
    except Exception:
        return None


def _extract_content(html: str) -> tuple[str | None, dict[str, Any]]:
    """Extract main content from *html* via trafilatura.

    Returns ``(text, metadata_dict)``.  If trafilatura returns nothing the
    text will be ``None`` (caller should fall back to BS4).

    Uses a single ``output_format="json"`` call to get both text and metadata,
    falling back to a plain-text call only if JSON parsing fails.
    """
    metadata: dict[str, Any] = {}
    text: str | None = None

    try:
        json_result = trafilatura.extract(
            html, output_format="json", include_comments=False, include_tables=True
        )
        if json_result:
            parsed = json.loads(json_result)
            text = parsed.get("text")
            metadata = parsed
    except Exception:
        pass

    # Fallback to plain-text extraction if JSON approach failed
    if text is None:
        text = trafilatura.extract(
            html, include_comments=False, include_tables=True, output_format="txt"
        )

    return text, metadata


def _bs4_fallback(html: str) -> str:
    """Fallback: extract visible text via BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)


def _build_splitter(chunk_size: int, chunk_overlap: int) -> RecursiveCharacterTextSplitter:
    """Build a RecursiveCharacterTextSplitter backed by tiktoken."""
    return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def _count_tokens(text: str, enc: tiktoken.Encoding) -> int:
    return len(enc.encode(text))


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _shingle(text: str, k: int = 3) -> set[str]:
    """Return the set of word-level k-shingles for *text*."""
    words = text.lower().split()
    if len(words) < k:
        return {" ".join(words)}
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


def _deduplicate_chunks(
    chunks: list[dict[str, Any]],
    jaccard_threshold: float = 0.8,
    num_perm: int = 128,
) -> tuple[list[dict[str, Any]], int]:
    """Remove exact and near-duplicate chunks.

    Returns ``(unique_chunks, num_removed)``.
    """
    if not chunks:
        return chunks, 0

    seen_hashes: set[str] = set()
    unique_after_exact: list[dict[str, Any]] = []

    # --- exact deduplication ---
    for chunk in chunks:
        h = hashlib.sha256(chunk["content"].encode("utf-8")).hexdigest()
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique_after_exact.append(chunk)

    exact_removed = len(chunks) - len(unique_after_exact)

    # --- near-duplicate deduplication via MinHash LSH ---
    if len(unique_after_exact) <= 1:
        return unique_after_exact, exact_removed

    lsh = MinHashLSH(threshold=jaccard_threshold, num_perm=num_perm)
    minhashes: list[MinHash] = []

    for idx, chunk in enumerate(unique_after_exact):
        m = MinHash(num_perm=num_perm)
        for s in _shingle(chunk["content"]):
            m.update(s.encode("utf-8"))
        minhashes.append(m)
        try:
            lsh.insert(str(idx), m)
        except ValueError:
            pass  # identical MinHash signature — handled in removal pass below

    removed: set[int] = set()
    for idx in range(len(unique_after_exact)):
        if idx in removed:
            continue
        neighbours = lsh.query(minhashes[idx])
        group = sorted(int(n) for n in neighbours)
        # Keep the first (lowest index), mark rest as near-duplicates
        for g in group[1:]:
            removed.add(g)

    unique_final = [c for i, c in enumerate(unique_after_exact) if i not in removed]
    near_removed = len(unique_after_exact) - len(unique_final)

    # Re-index
    for new_idx, chunk in enumerate(unique_final):
        chunk["chunk_index"] = new_idx

    return unique_final, exact_removed + near_removed


# ---------------------------------------------------------------------------
# RefinerStage
# ---------------------------------------------------------------------------

class RefinerStage(PipelineStage):
    """Stage 2 (Refiner): extract, chunk, count tokens, deduplicate."""

    stage_name = "refiner"

    async def validate_input(self, input_data: Any) -> bool:
        """Input must be a non-empty list of Spider output dicts with existing files."""
        if not isinstance(input_data, list) or len(input_data) == 0:
            return False
        for doc in input_data:
            if not isinstance(doc, dict):
                return False
            if not _REQUIRED_INPUT_KEYS.issubset(doc.keys()):
                return False
            if not Path(doc["html_path"]).is_file():
                return False
        return True

    async def process(self, input_data: list[dict], config: dict) -> StageResult:
        """Process raw HTML documents into chunked, deduplicated text."""
        chunk_size = config.get("chunk_size", 512)
        chunk_overlap = config.get("chunk_overlap", 50)

        enc = _get_encoding()
        splitter = _build_splitter(chunk_size, chunk_overlap)

        results: list[dict[str, Any]] = []
        errors: list[str] = []
        total_chunks = 0
        total_duplicates_removed = 0

        for doc in input_data:
            url = doc["url"]
            html_path = doc["html_path"]

            # --- read file ---
            try:
                html = Path(html_path).read_text(encoding="utf-8")
            except Exception as exc:
                msg = f"Cannot read {html_path}: {exc}"
                logger.warning(msg)
                errors.append(msg)
                continue

            # --- extract content ---
            text, metadata = _extract_content(html)

            if text is None or text.strip() == "":
                # Fallback to BS4
                text = _bs4_fallback(html)
                if not text.strip():
                    logger.info(f"No extractable content for {url}")
                    continue

            # --- language detection ---
            language = metadata.get("language") or _detect_language(text)
            if not language:
                language = doc.get("language") or "en"

            # --- title ---
            title = metadata.get("title") or doc.get("title", "")

            # --- chunk ---
            raw_chunks_text = splitter.split_text(text)
            raw_chunks = [
                {
                    "content": c,
                    "token_count": _count_tokens(c, enc),
                    "chunk_index": i,
                    "metadata": {
                        "source_url": url,
                        "language": language,
                        "title": title,
                    },
                }
                for i, c in enumerate(raw_chunks_text)
            ]

            # --- deduplicate ---
            unique_chunks, n_removed = _deduplicate_chunks(raw_chunks)
            total_duplicates_removed += n_removed

            total_chunks += len(unique_chunks)

            results.append(
                {
                    "url": url,
                    "title": title,
                    "language": language,
                    "content": text,
                    "chunks": unique_chunks,
                }
            )

        stats = {
            "total_documents": len(input_data),
            "processed": len(results),
            "failed": len(errors),
            "total_chunks": total_chunks,
            "duplicates_removed": total_duplicates_removed,
        }

        return StageResult(
            success=True,
            data=results,
            errors=errors,
            stats=stats,
        )
