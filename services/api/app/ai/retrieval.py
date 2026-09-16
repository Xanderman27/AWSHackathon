"""Retrieval over the approved corpus.

Two implementations behind one interface. The local one scores documents by term overlap and
applies the same metadata filters a Bedrock Knowledge Base query would; the Bedrock one calls
`retrieve` with a metadata filter. Same call signature and same return shape, so the golden
tests run against either and the pipeline never learns which it got.

The ingestion gate (PRD §10) lives here too: a document without tier, citation, reviewer and
approval date is not retrievable, however good its text is.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[4] / "corpus" / "manifest.json"
REQUIRED = ("id", "tier", "doc_type", "title", "text", "source_org", "source_url",
            "citation", "approved_by", "approved_on")


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    doc_type: str
    tier: int
    text: str
    source_org: str
    source_url: str
    citation: str
    # Which skills this document actually speaks to. Empty means general guidance (tone,
    # accessibility) that supports any draft but can never be the whole grounding for one.
    skill_ids: tuple[str, ...] = ()
    score: float = 0.0

    def as_citation(self) -> dict:
        """What a teacher and a judge see next to a generated draft."""
        return {"id": self.id, "title": self.title, "doc_type": self.doc_type, "tier": self.tier,
                "source_org": self.source_org, "source_url": self.source_url,
                "citation": self.citation, "excerpt": self.text[:240]}


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


STOP = set(_words(
    "the a an and or of to in on for with is are be as by that this it at from not you your"
))


@lru_cache(maxsize=1)
def _documents() -> list[dict]:
    rows = json.loads(CORPUS.read_text(encoding="utf-8"))
    approved = []
    for row in rows:
        # The gate: provenance or it does not ship.
        if all(row.get(field) for field in REQUIRED):
            approved.append(row)
    return approved


def _score(query_terms: Counter, doc: dict) -> float:
    terms = Counter(w for w in _words(f"{doc['title']} {doc['text']}") if w not in STOP)
    if not terms:
        return 0.0
    overlap = sum(min(count, terms[term]) for term, count in query_terms.items())
    # Length-normalised so a long document does not win on volume alone.
    return overlap / math.sqrt(sum(terms.values()))


def retrieve(query: str, *, skill_id: str | None = None, doc_types: tuple[str, ...] = (),
             limit: int = 4) -> list[Source]:
    """Approved sources for this query, filtered the way a KB metadata filter would."""
    query_terms = Counter(w for w in _words(query) if w not in STOP)
    hits: list[Source] = []
    for doc in _documents():
        if doc_types and doc["doc_type"] not in doc_types:
            continue
        # A document tagged to specific skills only answers for those skills; one tagged to
        # none (accessibility, tone) is general and always eligible.
        if skill_id and doc.get("skill_ids") and skill_id not in doc["skill_ids"]:
            continue
        score = _score(query_terms, doc)
        if score <= 0 and doc.get("skill_ids") and skill_id not in doc.get("skill_ids", []):
            continue
        hits.append(Source(
            id=doc["id"], title=doc["title"], doc_type=doc["doc_type"], tier=doc["tier"],
            text=doc["text"], source_org=doc["source_org"], source_url=doc["source_url"],
            citation=doc["citation"], skill_ids=tuple(doc.get("skill_ids") or ()),
            score=round(score, 4),
        ))
    hits.sort(key=lambda s: (-s.score, s.tier, s.id))
    return hits[:limit]


def by_id(source_id: str) -> Source | None:
    return next((s for s in retrieve("", limit=999) if s.id == source_id), None)
