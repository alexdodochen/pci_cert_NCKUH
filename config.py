"""Shared config for the PCI cert workflow.

Set EMR_SESSION env var before running any script. Get the session ID from
the (S(SESSION_ID)) portion of any EMR URL in your authenticated browser:

    PowerShell:  $env:EMR_SESSION = "<id>"
    bash:        export EMR_SESSION=<id>

Cases are read from cases.csv (chart,pci_date,group).
"""
import csv
import os
from pathlib import Path

ROOT = Path(__file__).parent
SESSION = os.environ.get("EMR_SESSION")
if not SESSION:
    raise SystemExit(
        "EMR_SESSION env var not set.\n"
        "Get a fresh session ID from the (S(...)) part of the EMR URL in your browser, then:\n"
        "  PowerShell:  $env:EMR_SESSION = \"<id>\"\n"
        "  bash:        export EMR_SESSION=<id>"
    )

BASE = f"http://hisweb.hosp.ncku/Emrquery/(S({SESSION}))/tree"
PDF_BASE = "http://hisweb.hosp.ncku/imgURL/showDocument.aspx"

CASES_CSV = ROOT / "cases.csv"
ADMISSION_MAP = ROOT / "_admission_map.json"
EMR_RAW_DIR = ROOT / "_emr_raw"
EMR_PDF_DIR = ROOT / "_emr_pdfs"
TREE_RAW_DIR = ROOT / "_tree_raw"
FILLED_DOCX_DIR = ROOT / "_filled_docx"
TEMPLATE_DOCX = ROOT / "PCI_認證病歷小抄_template.docx"
TEMPLATE_SCHEMA = ROOT / "template_schema.md"
GEMINI_WORKSPACE = Path(r"C:\Users\dr\Claude-Gemini-Dialogue")


def load_cases():
    """Read cases.csv → list of {chart, pci_date, group}."""
    if not CASES_CSV.exists():
        raise SystemExit(f"missing {CASES_CSV} — create it with header `chart,pci_date,group`")
    with CASES_CSV.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        chart = (r.get("chart") or "").strip()
        if not chart:
            continue
        out.append({
            "chart": chart,
            "pci_date": (r.get("pci_date") or "").strip(),
            "group": (r.get("group") or "1").strip(),
        })
    return out
