from __future__ import annotations

from pathlib import Path

from docx import Document


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    docx_path = root / "Thesis_Proposal_Yield_Curve_Modeling.docx"
    if not docx_path.exists():
        raise FileNotFoundError(docx_path)

    doc = Document(str(docx_path))

    lines: list[str] = []
    for p in doc.paragraphs:
        text = (p.text or "").strip()
        if not text:
            continue
        style = getattr(p.style, "name", "") or ""
        lines.append(f"[{style}] {text}")

    out = docx_path.with_suffix(".extracted.txt")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {out}")
    print("--- Preview (first 80 non-empty paragraphs) ---")
    for line in lines[:80]:
        print(line)


if __name__ == "__main__":
    main()
