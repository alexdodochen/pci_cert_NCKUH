"""For each case in cases.csv, switch the EMR session to that chart, fetch the
admission tree, and pick the I-sn whose date range contains the PCI date.

Output: _admission_map.json (chart → matched admission + all admissions in window)

Usage:
    $env:EMR_SESSION = "<session-id>"
    py discover_admissions.py
"""
import json
import re
import sys
import io
import datetime as dt
import urllib.request
import urllib.parse
import time

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from config import BASE, ADMISSION_MAP, TREE_RAW_DIR, load_cases


def fetch(url, timeout=25):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def switch_chart(chartno, start="2020-01-01", stop="2026-12-31"):
    """POST top.aspx → returns (post_html, patient_info, chart_specific_p2)."""
    raw = fetch(f"{BASE}/top.aspx")
    vs = re.search(r'name="__VIEWSTATE"[^>]*value="([^"]+)"', raw).group(1)
    vsg = re.search(r'name="__VIEWSTATEGENERATOR"[^>]*value="([^"]+)"', raw).group(1)
    ev = re.search(r'name="__EVENTVALIDATION"[^>]*value="([^"]+)"', raw).group(1)
    data = urllib.parse.urlencode({
        "__VIEWSTATE": vs, "__VIEWSTATEGENERATOR": vsg, "__EVENTVALIDATION": ev,
        "txtChartNo": chartno, "StartDate": start, "StopDate": stop,
        "BTQuery": "查詢", "radVer3": "on",
    }).encode("utf-8")
    req = urllib.request.Request(f"{BASE}/top.aspx", data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        html = r.read().decode("utf-8", errors="replace")
    rm = re.search(r'<span id="divUserSpec">(.*?)</span>', html, re.DOTALL)
    info = re.sub(r"<[^>]+>", "", rm.group(1)).strip() if rm else ""
    qm = re.search(r"Query\('&p2=([^']+)'\)", html)
    return html, info, (qm.group(1) if qm else None)


def parse_admissions(html):
    pattern = re.compile(
        r"<li[^>]*style='color:blue;'><span>\(住院\)([^<]+)</span>(.*?)"
        r"(?=<li[^>]*style='color:blue;'><span>\(|</ul></li></ul></li>|<div id=\"treelist\")",
        re.DOTALL,
    )
    for m in pattern.finditer(html):
        header = m.group(1).replace("&nbsp;", " ")
        body = m.group(2)
        hm = re.match(
            r"\s*(\d{4}/\d{2}/\d{2})\s*-\s*(\d{4}/\d{2}/\d{2})\s+(\S+)\s+(\S+)",
            header,
        )
        if not hm:
            continue
        s, e, doctor, dept = hm.groups()
        sn_m = re.search(r"medicalsn=(I\d+)", body)
        if not sn_m:
            continue
        links = re.findall(r"<a href='([^']+)'[^>]*>([^<]+)</a>", body)
        yield {
            "start": s, "end": e, "doctor": doctor, "dept": dept,
            "isn": sn_m.group(1), "header": header.strip(),
            "links": [{"text": t.strip(), "href": h} for h, t in links],
        }


def parse_date(s):
    y, m, d = s.split("/")
    return dt.date(int(y), int(m), int(d))


def in_range(date_str, start, end):
    return parse_date(start) <= parse_date(date_str) <= parse_date(end)


def main():
    out = {}
    TREE_RAW_DIR.mkdir(exist_ok=True)
    for case in load_cases():
        chart, pci_date = case["chart"], case["pci_date"]
        d = parse_date(pci_date)
        start = (d - dt.timedelta(days=180)).isoformat()
        stop = (d + dt.timedelta(days=180)).isoformat()
        print(f"\n=== {chart} (PCI {pci_date}) ===")

        try:
            _, patient_info, p2 = switch_chart(chart, start, stop)
        except Exception as e:
            print(f"    SWITCH ERROR: {e}")
            out[chart] = {"pci_date": pci_date, "error": f"switch: {e}"}
            continue
        print(f"    patient: {patient_info[:120]}")
        if "免申請" in patient_info or "線上申請" in patient_info:
            print(f"    ACCESS BLOCKED — run request_chart_access.py {chart}")
            out[chart] = {"pci_date": pci_date, "access_blocked": patient_info}
            continue
        if not p2:
            out[chart] = {"pci_date": pci_date, "error": "no p2 in switch response"}
            continue

        try:
            html = fetch(f"{BASE}/list3.aspx?chartno={chart}&start={start}&stop={stop}&query=0&p2={p2}")
        except Exception as e:
            print(f"    LIST3 ERROR: {e}")
            out[chart] = {"pci_date": pci_date, "error": str(e)}
            continue
        time.sleep(0.5)

        (TREE_RAW_DIR / f"list3_{chart}_{pci_date.replace('/', '')}.html").write_text(
            html, encoding="utf-8")
        admissions = list(parse_admissions(html))
        print(f"    {len(admissions)} admission(s)")
        for a in admissions:
            mark = "  <-- MATCH" if in_range(pci_date, a["start"], a["end"]) else ""
            print(f"      {a['isn']}  {a['start']}~{a['end']}  {a['doctor']} {a['dept']}{mark}")

        match = next((a for a in admissions if in_range(pci_date, a["start"], a["end"])), None)
        out[chart] = {"pci_date": pci_date, "matched": match, "all_admissions": admissions}

    ADMISSION_MAP.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {ADMISSION_MAP}")


if __name__ == "__main__":
    main()
