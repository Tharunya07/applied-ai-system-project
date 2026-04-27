"""
rag/indexer.py
==============
Builds a word-frequency index from the markdown documents in docs/.

The index is used by rag.retriever to score and rank document sections
against a free-text query.  Documents are split on heading boundaries so
that retrieval returns focused, paragraph-level context rather than whole
files.

Functions
---------
build_index(docs_folder)
    Read every .md file in *docs_folder*, tokenise the text, and return an
    index dict with keys: sections, word_freq, doc_count.

load_documents(docs_folder)
    Load each file as a list of section dicts with keys:
    filename, section_title, content, word_count.
"""

from __future__ import annotations

import os
import re
from collections import Counter

from logger import logger

# ---------------------------------------------------------------------------
# Stop-words excluded from the word-frequency index.
# ---------------------------------------------------------------------------
STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "for", "to", "of",
    "and", "or", "in", "on", "at", "by", "with",
})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _tokenise(text: str) -> list[str]:
    """Return lowercase alpha tokens from *text* with stop-words removed."""
    tokens = re.findall(r"[a-z]+", text.lower())
    return [t for t in tokens if t not in STOPWORDS]


def _split_into_sections(content: str, filename: str) -> list[dict]:
    """Split *content* on markdown heading lines and return a list of section dicts.

    Each dict has keys: filename, section_title, content, word_count.
    Content before the first heading is grouped under the title ``"_preamble"``.
    Empty sections (zero non-whitespace characters) are discarded.
    """
    sections: list[dict] = []
    current_title = "_preamble"
    current_lines: list[str] = []

    def _flush(title: str, lines: list[str]) -> None:
        body = "\n".join(lines).strip()
        if body:
            sections.append({
                "filename": filename,
                "section_title": title,
                "content": body,
                "word_count": len(body.split()),
            })

    for line in content.splitlines():
        if line.startswith("#"):
            _flush(current_title, current_lines)
            current_title = line.lstrip("#").strip() or "_unnamed"
            current_lines = []
        else:
            current_lines.append(line)

    _flush(current_title, current_lines)
    return sections


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_documents(docs_folder: str) -> list[dict]:
    """Load every .md file in *docs_folder* as a list of section dicts.

    Each returned dict has the following keys:

    ``filename``
        Base filename of the source file (e.g. ``"pet_care_guidelines.md"``).
    ``section_title``
        Text of the markdown heading that opens this section, or
        ``"_preamble"`` for content that precedes the first heading.
    ``content``
        Raw text of the section (heading line excluded).
    ``word_count``
        Number of whitespace-separated tokens in *content*.

    Empty sections (nothing but whitespace) are omitted.  One log entry is
    written per file showing how many sections were parsed.

    Parameters
    ----------
    docs_folder:
        Path to the directory containing ``.md`` files.

    Returns
    -------
    list[dict]
        Flat list of section dicts across all files.  Empty if the folder
        does not exist or contains no markdown files.
    """
    documents: list[dict] = []

    if not os.path.isdir(docs_folder):
        logger.warning("load_documents: docs_folder not found: %s", docs_folder)
        return documents

    for filename in sorted(os.listdir(docs_folder)):
        if not filename.endswith(".md"):
            continue

        filepath = os.path.join(docs_folder, filename)
        try:
            with open(filepath, encoding="utf-8") as fh:
                content = fh.read()
        except OSError as exc:
            logger.error("load_documents: could not read %s — %s", filepath, exc)
            continue

        sections = _split_into_sections(content, filename)
        documents.extend(sections)
        logger.info("load_documents: loaded %d section(s) from %s", len(sections), filename)

    return documents


def build_index(docs_folder: str) -> dict:
    """Build a word-frequency index from all markdown files in *docs_folder*.

    Returns a dict with three keys:

    ``sections``
        List of section dicts as returned by :func:`load_documents`.
    ``word_freq``
        Parallel list of word-frequency dicts (one per section).  Each dict
        maps lowercase tokens (stop-words excluded) to their raw count within
        that section.
    ``doc_count``
        Total number of sections indexed (``len(sections)``).

    Parameters
    ----------
    docs_folder:
        Path to the directory containing ``.md`` files.

    Returns
    -------
    dict
        Index dict with keys ``sections``, ``word_freq``, ``doc_count``.
    """
    sections = load_documents(docs_folder)

    word_freq: list[dict] = []
    for section in sections:
        tokens = _tokenise(section["content"])
        freq = dict(Counter(tokens))
        word_freq.append(freq)

    doc_count = len(sections)
    logger.info("build_index: indexed %d section(s) from %s", doc_count, docs_folder)

    return {
        "sections": sections,
        "word_freq": word_freq,
        "doc_count": doc_count,
    }
