"""
rag/
====
Retrieval-Augmented Generation (RAG) package for PawPal+.

Provides document indexing and semantic retrieval over the pet care
guidelines stored in docs/.  Other packages (agent, reliability) import
from here to ground agent decisions in curated knowledge.

Modules
-------
indexer   : Build and persist a word-frequency index from markdown docs.
retriever : Query the index and return ranked, relevant sections.
"""
