from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader


def normalize_whitespace(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def is_heading(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if len(s) > 120:
        return False

    # Avoid treating numbered objective bullets as headings (e.g., "1. To ...").
    if re.match(r"^\d+(?:\.\d+)*[\.)]?\s+To\s+", s):
        return False
    # Common proposal headings
    keywords = (
        "abstract",
        "introduction",
        "background",
        "motivation",
        "problem statement",
        "objectives",
        "research questions",
        "literature review",
        "methodology",
        "data",
        "results",
        "timeline",
        "work plan",
        "references",
    )
    low = s.lower().strip(":")
    if low in keywords:
        return True

    # ALL CAPS short lines are often headings
    letters = sum(ch.isalpha() for ch in s)
    if letters >= 6 and s.upper() == s and letters / max(1, len(s)) > 0.4:
        return True

    # Numbered headings like "1. Introduction" or "2 Literature Review"
    if re.match(r"^\d+(?:\.\d+)*[\.)]?\s+[A-Za-z].{2,}$", s):
        return True

    return False


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    pdf_path = root / "Thesis_Proposal_Yield_Curve_Modeling.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    reader = PdfReader(str(pdf_path))
    pages_text: list[str] = []
    for page in reader.pages:
        t = page.extract_text() or ""
        pages_text.append(t)

    full = normalize_whitespace("\n\n".join(pages_text))

    out_text = pdf_path.with_suffix(".extracted.txt")
    out_text.write_text(full + "\n", encoding="utf-8")

    # Extract candidate headings in reading order
    headings: list[str] = []
    for raw_line in full.splitlines():
        line = raw_line.strip()
        if is_heading(line):
            headings.append(line)

    # De-dupe while preserving order
    seen: set[str] = set()
    headings_unique: list[str] = []
    for h in headings:
        key = re.sub(r"\s+", " ", h.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        headings_unique.append(h)

    out_headings = pdf_path.with_suffix(".headings.txt")
    out_headings.write_text("\n".join(headings_unique) + "\n", encoding="utf-8")

    print(f"Wrote: {out_text}")
    print(f"Wrote: {out_headings}")
    print("--- Headings (preview) ---")
    for h in headings_unique[:60]:
        print(h)


if __name__ == "__main__":
    main()
