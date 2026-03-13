"""
In-memory mock DB keyed by UUID, mirroring the schema in models.py.
Populated from the same content as frontend static-data (trails, papers, edges).
No DB connection required.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

# Deterministic UUIDs so we can reference across modules
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "papertrail.mock")

def _id(s: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, s)


"""
NOTE: User data has moved to the real database (models.User).
This module now only holds mock trails/papers/user_papers for
graph-related endpoints.
"""

# Mock list for GET /papers/user (View Papers page). Replace with DB when ready.
# Each dict matches UserPaperOut: id, title, authors, year, abstract, url, isRead, isStarred, note?, trailTopics?
MOCK_USER_PAPERS: list[dict[str, Any]] = [
    {
        "id": "a1b2c3d4-0001-4000-8000-000000000001",
        "title": "Attention Is All You Need",
        "authors": ["Vaswani", "Shazeer", "Parmar"],
        "year": 2017,
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms.",
        "url": "https://arxiv.org/abs/1706.03762",
        "isRead": True,
        "isStarred": True,
        "note": "Foundational for LLMs.",
        "trailTopics": ["Transformer Architecture", "Deep Learning"],
    },
    {
        "id": "a1b2c3d4-0002-4000-8000-000000000002",
        "title": "BERT: Pre-training of Deep Bidirectional Transformers",
        "authors": ["Devlin", "Chang", "Lee", "Toutanova"],
        "year": 2018,
        "abstract": "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers.",
        "url": "https://arxiv.org/abs/1810.04805",
        "isRead": True,
        "isStarred": False,
        "note": None,
        "trailTopics": ["Transformer Architecture"],
    },
    {
        "id": "a1b2c3d4-0003-4000-8000-000000000003",
        "title": "Language Models are Few-Shot Learners",
        "authors": ["Brown", "Mann", "Ryder", "Subbiah"],
        "year": 2020,
        "abstract": "Recent work has demonstrated substantial gains on many NLP tasks by pre-training on a large corpus of text followed by fine-tuning on a specific task.",
        "url": "https://arxiv.org/abs/2005.14165",
        "isRead": False,
        "isStarred": True,
        "note": None,
        "trailTopics": ["LLM Alignment", "Transformer Architecture"],
    },
]
