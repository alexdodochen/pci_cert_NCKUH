"""Submit 線上申請 (online access request) for a chart that returns
"該病歷未在免申請即可調閱期間".

Default reason: A01 (醫療-醫療照護). Grants 3-day access.

Usage:
    py request_chart_access.py <chartno> [reason_code]

Reason codes:
    A01  醫療-醫療照護      A02  醫療-無排程檢查/治療
    B01  研究-研究            B02  研究-稽核
    C01  教學-病例討論        C02  教學-教學門診
    D01  行政-醫院評鑑        D02  行政-業務稽核或認證
"""
import re
import sys
import io
import urllib.request
import urllib.parse

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from config import BASE


def submit(chart, reason="A01"):
    url = f"{BASE}/exrequest.aspx?chartno={chart}"
    with urllib.request.urlopen(url, timeout=20) as r:
        raw = r.read().decode("utf-8", errors="replace")
    vs = re.search(r'name="__VIEWSTATE"[^>]*value="([^"]+)"', raw).group(1)
    vsg = re.search(r'name="__VIEWSTATEGENERATOR"[^>]*value="([^"]+)"', raw).group(1)
    ev = re.search(r'name="__EVENTVALIDATION"[^>]*value="([^"]+)"', raw).group(1)
    data = urllib.parse.urlencode({
        "__VIEWSTATE": vs, "__VIEWSTATEGENERATOR": vsg, "__EVENTVALIDATION": ev,
        "txtChartNo": chart, "DropDownList1": reason, "Button1": "申請",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        resp = r.read().decode("utf-8", errors="replace")
    msg_m = re.search(r'<span id="Messages"[^>]*>(.*?)</span>', resp, re.DOTALL)
    msg = re.sub(r"<[^>]+>", "", msg_m.group(1)).strip() if msg_m else "(no message)"
    return msg


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: py request_chart_access.py <chartno> [reason_code=A01]")
    chart = sys.argv[1]
    reason = sys.argv[2] if len(sys.argv) > 2 else "A01"
    print(f"Submitting access request for {chart} (reason={reason})...")
    msg = submit(chart, reason)
    print(f"  result: {msg}")


if __name__ == "__main__":
    main()
