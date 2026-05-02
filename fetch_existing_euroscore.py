"""For each case in cases.csv, try to fetch the in-EMR EuroSCORE form
(TemplateCode=EMR-3-04-008) for that admission, extract the PDF text, and write
to _emr_pdfs/<chart>_<isn>_euroscore_seq{N}.pdf + a stub text file.

The form URL (per user 2026-05-02):
  viewer.aspx?type=eform_ncku&chartno=X&medicalsn=Y&TemplateCode=EMR-3-04-008&Sequence=N

Tries Sequence 1..3.

Run with EMR_SESSION env var set.
"""
import json
import re
import sys
import io
import urllib.request
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from config import BASE, ADMISSION_MAP, EMR_PDF_DIR
from fetch_emr import post_top, fetch, fetch_pdf_from_eform, pdf_to_text


def fetch_euroscore_form(chart, isn):
    """Try Sequence=1..3 for TemplateCode=EMR-3-04-008. Return list of (seq, pdf_url, pdf_bytes, text)."""
    found = []
    for seq in (1, 2, 3):
        url = (
            f"{BASE}/viewer.aspx?type=eform_ncku&chartno={chart}&medicalsn={isn}"
            f"&TemplateCode=EMR-3-04-008&Sequence={seq}"
            f"&GStartDate=2020-01-01&GStopDate=2026-12-31"
        )
        try:
            pdf_url, pdf_bytes = fetch_pdf_from_eform(url)
        except Exception as e:
            print(f"    seq{seq}: fetch error: {e}")
            continue
        if not pdf_url or not pdf_bytes or pdf_bytes[:4] != b"%PDF":
            continue
        text = pdf_to_text(pdf_bytes)
        # If pdftotext returned almost nothing meaningful, still save bytes; surface text length
        found.append((seq, pdf_url, pdf_bytes, text))
        print(f"    seq{seq}: PDF OK ({len(pdf_bytes)} bytes, {len(text)} chars)")
    return found


def main():
    amap = json.loads(ADMISSION_MAP.read_text(encoding="utf-8"))
    summary = {}
    for chart, info in amap.items():
        match = info.get("matched")
        if not match:
            print(f"\n=== {chart}: skip (no admission)")
            continue
        isn = match["isn"]
        print(f"\n=== {chart} / {isn} ===")
        # Switch session to chart first (consistent with fetch_emr.py)
        try:
            post_top(chart)
        except Exception as e:
            print(f"    switch error: {e}")
            continue
        results = fetch_euroscore_form(chart, isn)
        if not results:
            print("    no EuroSCORE form (EMR-3-04-008) found at Seq 1-3")
            summary[chart] = {"isn": isn, "found": False}
            continue
        chart_records = []
        for seq, pdf_url, pdf_bytes, text in results:
            fn = pdf_url.rsplit("fn=", 1)[-1].split("&", 1)[0]
            pdf_path = EMR_PDF_DIR / f"{chart}_{isn}_euroscore_seq{seq}_{fn}"
            pdf_path.write_bytes(pdf_bytes)
            txt_path = EMR_PDF_DIR / f"{chart}_{isn}_euroscore_seq{seq}.txt"
            txt_path.write_text(text, encoding="utf-8")
            print(f"    saved -> {pdf_path.name}")
            chart_records.append({
                "seq": seq,
                "pdf_url": pdf_url,
                "pdf_filename": pdf_path.name,
                "txt_filename": txt_path.name,
                "text_chars": len(text),
            })
        summary[chart] = {"isn": isn, "found": True, "records": chart_records}

    out = Path(__file__).parent / "_euroscore_existing.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
