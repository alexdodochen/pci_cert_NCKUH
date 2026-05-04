"""Fetch all viewer.aspx?type=exam pages for each chart in cases.csv.

This is the FAST path for the cath OP report (心臟血管攝影檢查報告) — it lives
inline in the type=exam viewer (which renders the day's full lab + exam
report), reachable by Python requests with a valid EMR_SESSION.

Repo README earlier called it correctly: "Cath OP report is in
viewer.aspx?type=exam, not in EMROutcome.aspx (which is behind a separate SSO)."

EMROutcome.aspx is on a different host (HISService) with separate SSO — Python
requests gets back the SSO login page, so don't waste time there.
"""
import io
import re
import sys
import time
from datetime import date, timedelta

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from config import BASE, EMR_RAW_DIR, load_cases
from fetch_emr import post_top, fetch_text, html_to_text, get_tree_html


def fetch_one_chart(chart, pci_date):
    y, m, d = pci_date.split("/")
    pci = date(int(y), int(m), int(d))
    start = (pci - timedelta(days=180)).isoformat()
    stop = (pci + timedelta(days=180)).isoformat()

    print(f"=== Fetching type=exam reports for {chart} ({start} ~ {stop}) ===")
    _, p2 = post_top(chart, start, stop)
    print(f"   p2 = {p2[:30]}...")
    time.sleep(0.3)

    tree_html = get_tree_html(chart, p2, start, stop)
    exam_links = re.findall(r"<a href='([^']+type=exam[^']*)'[^>]*>([^<]+)</a>", tree_html)

    seen = set()
    unique = []
    for h, t in exam_links:
        if h in seen:
            continue
        seen.add(h)
        unique.append((h, t.strip()))
    print(f"   {len(unique)} unique type=exam link(s)")

    sections = [f"############ EXAM REPORTS for {chart} ############\n"]
    for href, text in unique:
        full_url = f"{BASE}/{href}"
        sn_m = re.search(r"medicalsn=([^&]+)", href)
        sn = sn_m.group(1) if sn_m else "unknown"
        print(f"   [{sn}] -> {href[:80]}")
        try:
            html = fetch_text(full_url)
        except Exception as e:
            print(f"     ERR: {e}")
            sections.append(f"\n=== [{sn}] ===\nURL: {full_url}\nERR: {e}")
            continue

        out_html = EMR_RAW_DIR / f"{chart}_exam_{sn}.html"
        out_html.write_text(html, encoding="utf-8")

        body = html_to_text(html)
        cath_hit = ("心臟血管攝影" in body or "Coronary" in body or "PCI" in body or "TIMI" in body)
        marker = " ★ cath" if cath_hit else ""
        print(f"     -> {out_html.name} ({len(body):,} chars){marker}")

        sections.append(f"\n\n=== [{sn}]{marker} ===\nURL: {full_url}\n{body}")
        time.sleep(0.3)

    out = EMR_RAW_DIR / f"{chart}_exam_reports.txt"
    out.write_text("\n".join(sections), encoding="utf-8")
    print(f"\n-> {out} ({sum(len(s) for s in sections):,} chars)")


def main():
    for case in load_cases():
        fetch_one_chart(case["chart"], case["pci_date"])


if __name__ == "__main__":
    main()
