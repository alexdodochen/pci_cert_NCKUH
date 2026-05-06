"""Survey every CV admission for a chart since 2020,
fetch each admission's 心導管室檢查後交班單(II) PDF, count stents,
and print a summary table — used to pick the max-stent session for PCI cert
when the user gives only a chart number without a specific PCI date.

Caveat: 心導管室交班單(II) PDFs from older years (≤2022 confirmed) use a
custom CID font with no ToUnicode CMap. pdftotext returns Caesar-shifted
mojibake (DES→EFT, LAD→MBE, LCX→MDY, RCA→SDB, ■→Ɏ, □→ɍ). For those years
the regex won't match — fall back to discharge note text to infer counts.

Usage:
    $env:EMR_SESSION = "<id>"
    py survey_max_stent.py <chart>
"""
import re
import sys
import io
import time
import urllib.request

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from config import BASE
from discover_admissions import switch_chart, parse_admissions
from fetch_emr import fetch_text, fetch_pdf_from_eform, pdf_to_text, expand_url


STENT_LINE = re.compile(
    r"[■☑](LAD|RCA|LCX|Left\s*Main|其他[^：]*)：?\s*"
    r"BMS[\s_]*(\d*)[\s_]*支[，,]\s*"
    r"DES[\s_]*(\d*)[\s_]*支[，,]\s*"
    r"DEB[\s_]*(\d*)[\s_]*支"
)


def parse_stents_from_pdf_text(text):
    """Return list of (vessel, BMS, DES, DEB) for ticked rows."""
    rows = []
    for m in STENT_LINE.finditer(text):
        vessel = m.group(1).strip()
        bms = int(m.group(2)) if m.group(2) else 0
        des = int(m.group(3)) if m.group(3) else 0
        deb = int(m.group(4)) if m.group(4) else 0
        rows.append((vessel, bms, des, deb))
    return rows


def find_cath_form_links(tree_html, isn):
    """Extract all 心導管室檢查後交班單(II) links for a given admission."""
    pattern = re.compile(
        r"<li[^>]*style='color:blue;'><span>\([^<]+</span>(.*?)"
        r"(?=<li[^>]*style='color:blue;'><span>\(|</ul></li></ul></li>|<div id=\"treelist\")",
        re.DOTALL,
    )
    for m in pattern.finditer(tree_html):
        body = m.group(1)
        if isn not in body:
            continue
        links = re.findall(r"<a href='([^']+)'[^>]*>([^<]+)</a>", body)
        return [(t.strip(), h) for h, t in links if "心導管室檢查後交班單" in t]
    return []


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: py survey_01002871.py <chart>")
    chart = sys.argv[1]
    start = "2020-01-01"
    stop = "2026-12-31"

    print(f"=== Surveying {chart} from {start} to {stop} ===")
    _, info, p2 = switch_chart(chart, start=start, stop=stop)
    print(f"patient: {info[:120]}")
    if not p2:
        sys.exit("no p2; access blocked or session bad")

    tree_html = fetch_text(f"{BASE}/list3.aspx?chartno={chart}&start={start}&stop={stop}&query=0&p2={p2}")
    admissions = list(parse_admissions(tree_html))
    print(f"\n{len(admissions)} admission(s) since 2020:\n")

    rows = []
    for adm in admissions:
        if "心臟" not in adm["dept"] and "Cardio" not in adm["dept"]:
            print(f"  {adm['isn']} {adm['start']}~{adm['end']} {adm['doctor']} {adm['dept']}  (skip — non-CV)")
            continue
        cath_links = find_cath_form_links(tree_html, adm["isn"])
        if not cath_links:
            print(f"  {adm['isn']} {adm['start']}~{adm['end']} {adm['doctor']} {adm['dept']}  — no cath form")
            continue
        for text, href in cath_links:
            full = expand_url(href)
            pdf_url, pdf_bytes = fetch_pdf_from_eform(full)
            if not pdf_bytes or pdf_bytes[:4] != b"%PDF":
                print(f"  {adm['isn']} {text} — PDF fetch failed")
                continue
            body = pdf_to_text(pdf_bytes)
            stents = parse_stents_from_pdf_text(body)
            total = sum(b + d + e for _, b, d, e in stents)
            rows.append({
                "isn": adm["isn"], "start": adm["start"], "end": adm["end"],
                "doctor": adm["doctor"], "form_text": text,
                "stents": stents, "total": total,
            })
            print(f"  {adm['isn']} {adm['start']}~{adm['end']} {adm['doctor']}  | {text}")
            for v, b, d, e in stents:
                print(f"      {v}: BMS={b} DES={d} DEB={e}")
            print(f"      TOTAL implants this session: {total}")
            time.sleep(0.3)

    print("\n=== Summary ===")
    rows.sort(key=lambda r: r["total"], reverse=True)
    for r in rows:
        print(f"  TOTAL={r['total']:2d}  {r['isn']}  {r['start']}~{r['end']}  {r['doctor']}  ({r['form_text']})")
    if rows:
        winner = rows[0]
        print(f"\nMAX STENT SESSION: {winner['isn']}  {winner['start']}~{winner['end']}  total={winner['total']}")


if __name__ == "__main__":
    main()
