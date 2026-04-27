"""
rag/retriever.py
================
Queries the word-frequency index produced by :mod:`rag.indexer` and returns
the most relevant document sections for a given natural-language query.

Relevance is computed with a TF-IDF scoring function so that common terms
are down-weighted relative to distinctive pet-care keywords.  The top-k
sections are returned along with their scores so downstream consumers
(agent, reliability) can make threshold-based decisions.

Functions
---------
retrieve(query, index, top_k)
    Return the *top_k* index sections most relevant to *query*.

score_section(query, section, word_freq)
    Score a single section against a query using an IDF-weighted term match.
"""

from __future__ import annotations

import math
import re

from logger import logger

# ---------------------------------------------------------------------------
# Stop-words — must match the set used in rag.indexer.
# ---------------------------------------------------------------------------
STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "for", "to", "of",
    "and", "or", "in", "on", "at", "by", "with",
})


def _tokenise(text: str) -> list[str]:
    """Return lowercase alpha tokens from *text* with stop-words removed."""
    tokens = re.findall(r"[a-z]+", text.lower())
    return [t for t in tokens if t not in STOPWORDS]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_section(query: str, section: dict, word_freq: dict) -> float:
    """Score the relevance of *section* to *query* using *word_freq*.

    *word_freq* should contain IDF-weighted term values pre-computed by
    :func:`retrieve`.  The function tokenises *query*, removes stop-words,
    then sums the IDF-weighted frequencies of each query token found in
    *word_freq* and normalises by the number of distinct query tokens so that
    longer queries do not artificially outscore shorter ones.

    Parameters
    ----------
    query:
        Free-text question or keyword string
        (e.g. ``"how often should I walk a large dog"``).
    section:
        Section dict from the index (keys: ``filename``, ``section_title``,
        ``content``, ``word_count``).  Not directly used here but kept in the
        signature so callers can pass it for future content-based features.
    word_freq:
        Dict mapping lowercase tokens to their IDF-weighted TF score for this
        specific section.  Produced inside :func:`retrieve` before this
        function is called.

    Returns
    -------
    float
        Relevance score >= 0.0.  Returns ``0.0`` when the query is empty,
        *word_freq* is empty, or no query token matches any indexed token.
    """
    query_tokens = _tokenise(query)
    if not query_tokens or not word_freq:
        return 0.0

    raw_score = sum(word_freq.get(token, 0.0) for token in query_tokens)
    # Normalise by unique query tokens to keep scores comparable across queries
    # of different lengths.
    return raw_score / len(set(query_tokens))


def retrieve(query: str, index: dict, top_k: int = 3) -> list[dict]:
    """Return the *top_k* sections from *index* most relevant to *query*.

    Scoring pipeline
    ~~~~~~~~~~~~~~~~
    1. Compute document frequency (df) for every term across all sections.
    2. For each section compute a TF-IDF weighted dict:
       ``tf = raw_count / total_tokens_in_section``
       ``idf = log((1 + N) / (1 + df(term))) + 1``   (smoothed, always > 0)
       ``tfidf = tf * idf``
    3. Call :func:`score_section` with the TF-IDF dict.
    4. Sort descending, drop zero-score entries, return top *top_k*.

    Parameters
    ----------
    query:
        A free-text query string describing what information is needed.
    index:
        The index dict produced by :func:`rag.indexer.build_index`.
        Expected keys: ``sections`` (list), ``word_freq`` (list), ``doc_count`` (int).
    top_k:
        Maximum number of sections to return.  Defaults to ``3``.

    Returns
    -------
    list[dict]
        Each dict contains ``section_title``, ``filename``, ``content``,
        ``score``.  Returns an empty list when all scores are ``0.0`` or
        the index is empty.
    """
    sections: list[dict] = index.get("sections", [])
    word_freq_list: list[dict] = index.get("word_freq", [])
    doc_count: int = index.get("doc_count", 0)

    if not sections or doc_count == 0:
        return []

    # ------------------------------------------------------------------
    # Step 1: compute document frequency for every token in the corpus.
    # ------------------------------------------------------------------
    doc_freq: dict[str, int] = {}
    for freq_dict in word_freq_list:
        for word in freq_dict:
            doc_freq[word] = doc_freq.get(word, 0) + 1

    # ------------------------------------------------------------------
    # Step 2: score each section.
    # ------------------------------------------------------------------
    results: list[dict] = []

    for i, section in enumerate(sections):
        raw_freq: dict = word_freq_list[i] if i < len(word_freq_list) else {}

        # Build TF-IDF weighted freq dict for this section.
        total_tokens = sum(raw_freq.values()) or 1
        tfidf_freq: dict[str, float] = {}
        for word, count in raw_freq.items():
            tf = count / total_tokens
            # Smoothed IDF: always positive, rewards rare terms.
            idf = math.log((1 + doc_count) / (1 + doc_freq.get(word, 0))) + 1.0
            tfidf_freq[word] = tf * idf

        score = score_section(query, section, tfidf_freq)

        results.append({
            "section_title": section["section_title"],
            "filename": section["filename"],
            "content": section["content"],
            "score": score,
        })

    # ------------------------------------------------------------------
    # Step 3: filter out zero scores, sort, return top_k.
    # ------------------------------------------------------------------
    results = [r for r in results if r["score"] > 0.0]
    if not results:
        logger.info("retrieve: query '%s' — no matching sections found", query)
        return []

    results.sort(key=lambda r: r["score"], reverse=True)
    top_results = results[:top_k]

    logger.info(
        "retrieve: query '%s' | top result: '%s' (score=%.4f)",
        query,
        top_results[0]["section_title"],
        top_results[0]["score"],
    )

    return top_results
