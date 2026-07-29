"""
Chunking strategy (design decision you must defend in the doc — see
docs/DESIGN_DOC.md section 4 for the write-up).

Summary of the choice:
- Structure-aware first: we split on the document's own headings/pages/
  paragraphs (see parsers.py) so a chunk never straddles two unrelated
  policy sections.
- Fixed token budget second: within a section, we pack sentences into
  ~350-token windows with a 60-token overlap. Policy documents have
  short sections (a benefits table, a PTO clause) that comfortably fit
  one window, and the overlap protects any answer that depends on the
  sentence right at a window boundary (e.g. "employees must submit the
  form above within 5 business days" split from the sentence naming the
  form).
- Why not embed whole sections as one chunk regardless of length: some
  sections (e.g. "General Conduct Policy") run long, and long chunks
  dilute the embedding — a query about "dress code" retrieves the whole
  10-paragraph conduct policy instead of the one relevant paragraph.
  Capping at ~350 tokens keeps each chunk topically tight.
"""
from dataclasses import dataclass

import tiktoken

from app.core.config import get_settings

try:
    _enc = tiktoken.get_encoding("cl100k_base")
except Exception:  # noqa: BLE001
    # tiktoken downloads its BPE file from openaipublic.blob.core.windows.net
    # on first use. In an air-gapped/offline dev box (or a sandboxed CI
    # runner with restricted egress) that download can fail. Fall back to a
    # rough word-count-based estimate so chunking still works; token counts
    # will be approximate (~1.3 tokens per word) rather than exact.
    _enc = None


@dataclass
class ChunkCandidate:
    section_heading: str | None
    content: str
    token_count: int
    ordinal: int


def _token_len(text: str) -> int:
    if _enc is not None:
        return len(_enc.encode(text))
    return max(1, int(len(text.split()) * 1.3))


def chunk_sections(sections: list[tuple[str | None, str]]) -> list[ChunkCandidate]:
    settings = get_settings()
    size = settings.chunk_size_tokens
    overlap = settings.chunk_overlap_tokens

    chunks: list[ChunkCandidate] = []
    ordinal = 0

    for heading, text in sections:
        sentences = _split_sentences(text)
        window_tokens: list[str] = []
        window_len = 0

        def flush(carry_overlap: bool):
            nonlocal window_tokens, window_len, ordinal
            if not window_tokens:
                return
            content = " ".join(window_tokens).strip()
            if content:
                chunks.append(
                    ChunkCandidate(
                        section_heading=heading,
                        content=content,
                        token_count=_token_len(content),
                        ordinal=ordinal,
                    )
                )
                ordinal += 1
            if carry_overlap:
                # Keep the tail sentences (up to `overlap` tokens) as the
                # start of the next window.
                tail: list[str] = []
                tail_len = 0
                for s in reversed(window_tokens):
                    t = _token_len(s)
                    if tail_len + t > overlap:
                        break
                    tail.insert(0, s)
                    tail_len += t
                window_tokens = tail
                window_len = tail_len
            else:
                window_tokens = []
                window_len = 0

        for sentence in sentences:
            s_len = _token_len(sentence)
            if window_len + s_len > size and window_tokens:
                flush(carry_overlap=True)
            window_tokens.append(sentence)
            window_len += s_len

        flush(carry_overlap=False)

    return chunks


def _split_sentences(text: str) -> list[str]:
    # Lightweight sentence split — good enough for policy prose. Swap for
    # a proper sentence tokenizer (e.g. nltk/spacy) if the corpus grows
    # more linguistically complex.
    import re

    raw = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s for s in raw if s]
