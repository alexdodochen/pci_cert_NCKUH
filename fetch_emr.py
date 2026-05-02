"""Fetch all relevant EMR documents for the charts mapped in _admission_map.json.

For each chart's matched admission, fetches: AD, DC, PL, diagnosis, order, every
individual consult (by titleid), aconsult, and eform_ncku cath-room forms — the
eform shells embed iframe PDFs at imgURL/showDocument.aspx, which we download
and pdftotext-convert.

Output: _emr_raw/<chart>_<isn>_raw.txt + _emr_pdfs/<chart>_<isn>_<pdf-name>.pdf

Usage:
    $env:EMR_SESSION = "<session-id>"
    py fetch_emr.py
"""
import json
import re
import sys
import io
import time
import urllib.request
import urllib.parse
from html.parser import HTMLParser

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from config import BASE, ADMISSION_MAP, EMR_RAW_DIR, EMR_PDF_DIR

EMR_RAW_DIR.mkdir(exist_ok=True)
EMR_PDF_DIR.mkdir(exist_ok=True)
RAW_DIR = EMR_RAW_DIR
PDF_DIR = EMR_PDF_DIR


# ---------- HTTP helpers ----------

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "PCI-cert-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_text(url, timeout=25):
    return fetch(url, timeout).decode("utf-8", errors="replace")


def post_top(chartno, start="2020-01-01", stop="2026-12-31"):
    """Switch session to chartno; return (post_html, p2_filter)."""
    raw = fetch_text(f"{BASE}/top.aspx")
    vs = re.search(r'name="__VIEWSTATE"[^>]*value="([^"]+)"', raw).group(1)
    vsg = re.search(r'name="__VIEWSTATEGENERATOR"[^>]*value="([^"]+)"', raw).group(1)
    ev = re.search(r'name="__EVENTVALIDATION"[^>]*value="([^"]+)"', raw).group(1)
    fields = {
        "__VIEWSTATE": vs, "__VIEWSTATEGENERATOR": vsg, "__EVENTVALIDATION": ev,
        "txtChartNo": chartno, "StartDate": start, "StopDate": stop,
        "BTQuery": "查詢", "radVer3": "on",
    }
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(f"{BASE}/top.aspx", data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=20) as r:
        html = r.read().decode("utf-8", errors="replace")
    qm = re.search(r"Query\('&p2=([^']+)'\)", html)
    return html, (qm.group(1) if qm else None)


# ---------- HTML to text ----------

class _TX(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip = True
        if tag in ("br", "p", "tr", "div", "li", "h1", "h2", "h3"):
            self.parts.append("\n")
        if tag == "td":
            self.parts.append(" | ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = False

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(html):
    p = _TX()
    p.feed(html)
    txt = "".join(p.parts)
    txt = re.sub(r"[ \t ]+", " ", txt)
    txt = re.sub(r"\n{2,}", "\n", txt)
    return txt.strip()


# ---------- PDF to text ----------

PDFTOTEXT_CANDIDATES = [
    r"C:\Program Files\Git\mingw64\bin\pdftotext.exe",
    r"C:\msys64\mingw64\bin\pdftotext.exe",
    "pdftotext",
]


def _find_pdftotext():
    import os
    for c in PDFTOTEXT_CANDIDATES:
        if os.path.isabs(c):
            if os.path.exists(c):
                return c
        else:
            return c  # let subprocess search PATH; if not found, FileNotFoundError
    return None


def pdf_to_text(data):
    """Extract PDF text using pdftotext CLI (poppler shipped with Git for Windows)."""
    import tempfile
    import subprocess
    import os
    exe = _find_pdftotext()
    if not exe:
        return f"[no pdftotext available; {len(data)} bytes]"
    tmp_pdf = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(data)
            tmp_pdf = f.name
        out = subprocess.run(
            [exe, "-layout", "-enc", "UTF-8", tmp_pdf, "-"],
            capture_output=True, timeout=30,
        )
        if out.returncode == 0:
            return out.stdout.decode("utf-8", errors="replace")
        return f"[pdftotext rc={out.returncode}: {out.stderr.decode('utf-8', errors='replace')[:200]}]"
    except Exception as e:
        return f"[PDF extract error: {e}; {len(data)} bytes]"
    finally:
        if tmp_pdf and os.path.exists(tmp_pdf):
            try:
                os.unlink(tmp_pdf)
            except Exception:
                pass


# ---------- Tree parsing for one admission ----------

def get_tree_html(chartno, p2, start, stop):
    url = f"{BASE}/list3.aspx?chartno={chartno}&start={start}&stop={stop}&query=0&p2={p2}"
    return fetch_text(url)


def admission_links(tree_html, isn):
    """Return [(text, href)] for the block matching isn."""
    pattern = re.compile(
        r"<li[^>]*style='color:blue;'><span>(\([^<]+)</span>(.*?)"
        r"(?=<li[^>]*style='color:blue;'><span>\(|</ul></li></ul></li>|<div id=\"treelist\")",
        re.DOTALL,
    )
    for m in pattern.finditer(tree_html):
        body = m.group(2)
        if isn in body:
            links = re.findall(r"<a href='([^']+)'[^>]*>([^<]+)</a>", body)
            header = m.group(1).replace("&nbsp;", " ").strip()
            return header, [(t.strip(), h) for h, t in links]
    return None, []


# ---------- Fetch logic per admission ----------

INTEREST_PATTERNS = [
    # (label, regex on link text — case-sensitive)
    ("AD", re.compile(r"^Admission Note")),
    ("PL", re.compile(r"^問題表列")),
    ("DC", re.compile(r"^Discharge Note")),
    ("Diagnosis", re.compile(r"^Diagnosis$")),
    ("Order", re.compile(r"^Order")),
    ("出院帶藥", re.compile(r"^出院帶藥")),
    ("檢驗報告", re.compile(r"^檢驗報告")),
    ("會診紀錄", re.compile(r"^會診紀錄$")),
    ("會診", re.compile(r"^\s*\d{4}/\d{2}/\d{2}.*")),  # individual consult by date
    ("抗生素照會", re.compile(r"^抗生素照會$")),
    ("同意書", re.compile(r"^同意書$")),
    ("自費同意書", re.compile(r"^自費同意書$")),
    ("出院準備", re.compile(r"^出院準備服務表單$")),
    ("出院照護", re.compile(r"^出院照護計畫$")),
    ("DRG", re.compile(r"^DRG編審$")),
    ("eform", re.compile(r"^心導管室")),  # cath room handover forms
    ("eform", re.compile(r"^心臟功能")),  # echo / functional
    ("eform", re.compile(r"^物理治療")),  # PT records
    ("eform", re.compile(r"^住院同意書")),  # admission consent
]


def classify(text):
    for label, pat in INTEREST_PATTERNS:
        if pat.search(text):
            return label
    return None


def fetch_pdf_from_eform(eform_url):
    """Given an eform_ncku viewer URL, fetch it and extract iframe PDF URL,
    then download and return (pdf_url, pdf_bytes)."""
    try:
        html = fetch_text(eform_url)
    except Exception as e:
        return None, f"FETCH ERROR: {e}".encode()
    m = re.search(r"<iframe[^>]+src='([^']+\.pdf[^']*)'", html)
    if not m:
        m = re.search(r'src=["\']([^"\']*showDocument\.aspx\?fn=[^"\']+)["\']', html)
    if not m:
        return None, b""
    pdf_url = m.group(1)
    if pdf_url.startswith("http"):
        full = pdf_url
    else:
        full = "http://hisweb.hosp.ncku" + ("" if pdf_url.startswith("/") else "/") + pdf_url
    try:
        return full, fetch(full, timeout=30)
    except Exception as e:
        return full, f"PDF FETCH ERROR: {e}".encode()


def expand_url(href):
    """Resolve relative tree-page hrefs to absolute URLs."""
    if href.startswith("http"):
        return href
    return f"{BASE}/{href}"


def fetch_admission_bundle(chart, isn, links, header):
    sections = []
    sections.append(f"############ ADMISSION {isn} — {header} ############\n")

    pdf_jobs = []  # (label, full_eform_url, link_text)

    for text, href in links:
        label = classify(text)
        if label is None:
            continue
        full_url = expand_url(href)

        if label == "eform":
            pdf_jobs.append((text, full_url))
            continue

        try:
            html = fetch_text(full_url)
        except Exception as e:
            sections.append(f"\n=== [{label}] {text} ===\nFETCH ERROR: {e}")
            continue
        body = html_to_text(html)
        sections.append(f"\n=== [{label}] {text} ===\nURL: {full_url}\n{body}")
        time.sleep(0.25)

    # Now do PDFs
    for text, eform_url in pdf_jobs:
        pdf_url, pdf_bytes = fetch_pdf_from_eform(eform_url)
        if not pdf_url:
            sections.append(f"\n=== [eform/no-pdf] {text} ===\nNo iframe PDF in eform shell.")
            continue
        # Save raw PDF for archive
        fn = pdf_url.rsplit("fn=", 1)[-1].split("&", 1)[0]
        pdf_path = PDF_DIR / f"{chart}_{isn}_{fn}"
        try:
            pdf_path.write_bytes(pdf_bytes)
        except Exception:
            pass
        text_body = pdf_to_text(pdf_bytes) if pdf_bytes and pdf_bytes[:4] == b"%PDF" else f"[non-PDF or empty: {len(pdf_bytes)} bytes]"
        sections.append(f"\n=== [eform-PDF] {text} ===\nPDF: {pdf_url}\nSAVED: {pdf_path.name}\n{text_body}")
        time.sleep(0.25)

    return "\n".join(sections)


# ---------- Main ----------

def main():
    amap = json.loads(ADMISSION_MAP.read_text(encoding="utf-8"))

    for chart, info in amap.items():
        match = info.get("matched")
        if not match:
            print(f"\n=== {chart}: SKIP — {info.get('access_blocked') or info.get('error') or 'no match'}")
            continue
        isn = match["isn"]
        pci_date = info["pci_date"]
        print(f"\n=== {chart} (PCI {pci_date}) — {isn} ===")

        # 1. Switch session to this chart
        _, p2 = post_top(chart, start="2020-01-01", stop="2026-12-31")
        if not p2:
            print("    no p2 from switch — skip")
            continue
        print(f"    p2 = {p2[:30]}...")
        time.sleep(0.3)

        # 2. Refetch tree (already in admission_map but fresher is safer)
        # Use a wide window so the matched admission is in there.
        from datetime import date, timedelta
        y, m, d = pci_date.split("/")
        pci = date(int(y), int(m), int(d))
        tree_html = get_tree_html(chart, p2,
                                   (pci - timedelta(days=180)).isoformat(),
                                   (pci + timedelta(days=180)).isoformat())
        header, links = admission_links(tree_html, isn)
        if not links:
            print(f"    no links found for {isn}")
            continue
        print(f"    header: {header}")
        print(f"    {len(links)} links in admission")

        # 3. Fetch bundle
        bundle = fetch_admission_bundle(chart, isn, links, header)
        out = RAW_DIR / f"{chart}_{isn}_raw.txt"
        out.write_text(bundle, encoding="utf-8")
        print(f"    -> {out} ({len(bundle):,} chars)")


if __name__ == "__main__":
    main()
