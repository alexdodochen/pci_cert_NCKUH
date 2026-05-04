"""Fetch all eforms (NISlist2 EForms type=2) for a chart, then download each
embedded PDF. Run after switching chart context via top.aspx (top.aspx must be
POST'd first or list returns empty)."""
import io
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from config import BASE, EMR_PDF_DIR, EMR_RAW_DIR, load_cases
from fetch_emr import fetch, fetch_text, post_top, html_to_text, pdf_to_text, fetch_pdf_from_eform

SUBTYPES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def fetch_one_chart(chart, pci_date):
    """Sweep all eform GSubtypes for one chart, around its PCI date.

    Window: ±90 days around pci_date.
    """
    from datetime import date, timedelta
    y, m, d = pci_date.split("/")
    pci = date(int(y), int(m), int(d))
    start = (pci - timedelta(days=90)).isoformat()
    stop = (pci + timedelta(days=90)).isoformat()

    print(f"=== Fetching eforms for {chart} ({start} ~ {stop}), GSubtypes {SUBTYPES} ===")
    _, p2 = post_top(chart, start, stop)
    print(f"   p2 = {p2[:30]}...")
    time.sleep(0.3)

    seen = set()  # dedup by (medicalsn, TemplateCode, Sequence)
    sections = [f"############ EFORMS for {chart} ({start}~{stop}) ############\n"]

    for subtype in SUBTYPES:
        url = f"{BASE}/NISlist2.aspx?ChartNo={chart}&Gtype=EForms&GSubtype={subtype}&GStartDate={start}&GStopDate={stop}&MedicalSn="
        try:
            html = fetch_text(url)
        except Exception as e:
            print(f"\n--- GSubtype={subtype}: FETCH ERROR {e}")
            continue
        (EMR_RAW_DIR / f"{chart}_eform_index_g{subtype}.html").write_text(html, encoding="utf-8")

        links = re.findall(r"<a href='([^']+)'[^>]*>([^<]+)</a>", html)
        if not links:
            links = re.findall(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', html)
        # filter eform links only
        eform_links = [(h, t) for h, t in links if "eform_ncku" in h or "type=eform" in h]
        print(f"\n--- GSubtype={subtype}: {len(eform_links)} eform link(s)")
        sections.append(f"\n\n############ GSubtype={subtype} ({len(eform_links)} eforms) ############")

        for href, text in eform_links:
            text = text.strip()
            full_url = href if href.startswith("http") else f"{BASE}/{href}"
            # dedup by medicalsn + TemplateCode
            sn_m = re.search(r"medicalsn=([^&]+)", href)
            tc_m = re.search(r"TemplateCode=([^&]+)", href)
            seq_m = re.search(r"Sequence=(\d+)", href)
            key = (sn_m.group(1) if sn_m else href, tc_m.group(1) if tc_m else "", seq_m.group(1) if seq_m else "")
            if key in seen:
                continue
            seen.add(key)

            tc = tc_m.group(1) if tc_m else "?"
            print(f"   [{tc}] {text[:50]}")

            pdf_url, pdf_bytes = fetch_pdf_from_eform(full_url)
            if pdf_url and pdf_bytes and pdf_bytes[:4] == b"%PDF":
                fn = pdf_url.rsplit("fn=", 1)[-1].split("&", 1)[0]
                safe_fn = re.sub(r"[^\w.\-]", "_", fn)
                pdf_path = EMR_PDF_DIR / f"{chart}_g{subtype}_{tc}_{safe_fn}"
                try:
                    pdf_path.write_bytes(pdf_bytes)
                except Exception as e:
                    print(f"     WRITE ERROR: {e}")
                body = pdf_to_text(pdf_bytes)
                sections.append(f"\n=== [g{subtype}/{tc}] {text} ===\nURL: {full_url}\nPDF: {pdf_url}\nSAVED: {pdf_path.name}\n{body}")
            else:
                try:
                    shell_html = fetch_text(full_url)
                    body = html_to_text(shell_html)
                except Exception as e:
                    body = f"FETCH ERROR: {e}"
                sections.append(f"\n=== [g{subtype}/{tc}] {text} ===\nURL: {full_url}\n{body}")
            time.sleep(0.3)

    out = EMR_RAW_DIR / f"{chart}_eforms_raw.txt"
    out.write_text("\n".join(sections), encoding="utf-8")
    print(f"\n-> {out} ({sum(len(s) for s in sections):,} chars)")
    print(f"   Unique forms: {len(seen)}")


def main():
    for case in load_cases():
        fetch_one_chart(case["chart"], case["pci_date"])


if __name__ == "__main__":
    main()
