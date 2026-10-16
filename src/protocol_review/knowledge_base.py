"""Knowledge base loader + lightweight retrieval ("RAG-lite").

The KB is a folder of markdown files (SPIRIT 2025, ICH-GCP E6(R3) key points,
administrative checklists). Documents are small, so each agent receives the full
documents of its domain; `retrieve()` additionally ranks paragraphs by keyword
overlap for targeted questions (critic verification).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import settings


@dataclass
class KBDoc:
    domain: str
    name: str
    text: str


def load_kb(base: Path | None = None) -> list[KBDoc]:
    base = base or settings.knowledge_base_path
    docs: list[KBDoc] = []
    if not base.exists():
        return docs
    for domain_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        for f in sorted(domain_dir.glob("*.md")):
            docs.append(KBDoc(domain=domain_dir.name, name=f.stem, text=f.read_text(encoding="utf-8")))
    return docs


def kb_text(domain: str, base: Path | None = None) -> str:
    parts = [f"## {d.name}\n{d.text}" for d in load_kb(base) if d.domain == domain]
    return "\n\n".join(parts)


_WORD = re.compile(r"[a-zA-Z][a-zA-Z\-]{2,}")
_CODE = re.compile(r"\b(?:ADMIN-CHK-\d{2}|SPIRIT-\d{1,2}[a-c]?|GCP-\d{2})\b")


def retrieve(query: str, domain: str | None = None, k: int = 5, base: Path | None = None) -> list[str]:
    """Return the k paragraphs with the highest keyword overlap with `query`."""
    q = {w.lower() for w in _WORD.findall(query)}
    scored: list[tuple[int, str]] = []
    for d in load_kb(base):
        if domain and d.domain != domain:
            continue
        for para in re.split(r"\n\s*\n", d.text):
            words = {w.lower() for w in _WORD.findall(para)}
            score = len(q & words)
            if score:
                scored.append((score, f"[{d.name}] {para.strip()}"))
    scored.sort(key=lambda t: -t[0])
    return [p for _, p in scored[:k]]


def rule_codes(base: Path | None = None) -> set[str]:
    """All rule codes defined in the KB (e.g. ADMIN-CHK-03, SPIRIT-14, GCP-02)."""
    codes: set[str] = set()
    for d in load_kb(base):
        codes.update(_CODE.findall(d.text))
    return codes
