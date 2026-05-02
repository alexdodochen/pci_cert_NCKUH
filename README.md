# pci_cert_NCKUH

Automation for filling out the Taiwan PCI 認證病歷小抄 (PCI certification cheatsheet) for cardiology cath cases at NCKUH (National Cheng Kung University Hospital).

Scrapes the in-network Web-EMR (`hisweb.hosp.ncku/Emrquery`), bundles per-admission notes + cath OP report + 心導管室交班單 PDFs, delegates structured field extraction to Gemini CLI, and renders a filled `.docx` per case.

## Pipeline

```
cases.csv ──► discover_admissions.py ──► _admission_map.json
                                            │
                                            ▼
                                       fetch_emr.py ──► _emr_raw/<chart>_<isn>_raw.txt
                                                          + _emr_pdfs/*.pdf
                                            │
                                            ▼
                                  Gemini CLI (Claude-Gemini-Dialogue)
                                            │
                                            ▼
                                   case_<chart>_filled.yaml
                                            │
                                            ▼
                                       render_docx.py ──► _filled_docx/<chart>_<姓O名>_filled.docx
```

Or one-shot: `py pci_cert.py` (prints the per-case delegate commands; you run each).

## Files

| File | Purpose |
|---|---|
| `config.py` | Reads `EMR_SESSION` env var + `cases.csv`; defines paths |
| `discover_admissions.py` | POSTs `top.aspx` to switch chart, fetches `list3.aspx`, picks I-sn matching PCI date |
| `request_chart_access.py` | Submits 線上申請 (`exrequest.aspx`) for charts outside the auto-access window |
| `fetch_emr.py` | Per matched admission: AD/DC/PL/diagnosis/order/consults/exam/eform PDFs |
| `render_docx.py` | python-docx fills the template's first-group tables; drops the second group |
| `pci_cert.py` | Orchestrator |
| `template_schema.md` | YAML field definitions handed to Gemini |
| `PCI_認證病歷小抄_template.docx` | The empty cheatsheet template |

## Prerequisites

- Python 3.10+ with `python-docx` and `PyYAML`
- `pdftotext` CLI (ships with [Git for Windows](https://git-scm.com/download/win) at `C:\Program Files\Git\mingw64\bin\pdftotext.exe`)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) authenticated
- [Claude-Gemini-Dialogue](https://github.com/alexdodochen/Claude-Gemini-Dialogue) cloned locally (default: `C:\Users\dr\Claude-Gemini-Dialogue`) — provides the security-hardened `delegate.sh` wrapper
- A current EMR session ID from your browser's URL (`(S(SESSION_ID))` portion); expires in hours

## Usage

```powershell
# 1. Set session
$env:EMR_SESSION = "<paste session id from browser>"

# 2. Edit cases.csv (PHI — gitignored)
#    chart,pci_date,group
#    12345678,2025/2/7,1

# 3. Run
py discover_admissions.py
# if any chart is access-blocked:
py request_chart_access.py 22172134 A01
py discover_admissions.py
py fetch_emr.py

# 4. Delegate to Gemini per case (run from Claude-Gemini-Dialogue dir):
cd /c/Users/dr/Claude-Gemini-Dialogue
GEMINI_CLI_TRUST_WORKSPACE=true bash scripts/delegate.sh -e \
  "Read inputs/template_schema.md and inputs/case_<chart>_raw.txt. Fill the YAML for chart <chart>; save to out/case_<chart>_filled.yaml. The cath OP report (心臟血管攝影檢查報告) is in the [檢驗報告] section. Be honest about unknowns — leave fields null. Final stdout line: 'DONE: out/case_<chart>_filled.yaml'."

# 5. Render
py render_docx.py
```

## Key EMR scraping facts (verified 2026-05-02)

- **Session is per-chart.** `list3.aspx` returns an empty tree unless you first POST `top.aspx` with `txtChartNo=<chart>` + `radVer3=on` + the form's three `__VIEWSTATE*` tokens. The POST response embeds a chart-specific `p2` filter (`Query('&p2=...')`) which `list3.aspx` requires.
- **Old charts need 線上申請.** When `divUserSpec` shows "該病歷未在免申請即可調閱期間", POST `exrequest.aspx?chartno=X` with `DropDownList1=A01&Button1=申請` (reason A01 = 醫療-醫療照護, grants 3-day access).
- **Cath OP report is in `viewer.aspx?type=exam`**, not in EMROutcome.aspx (which is behind a separate SSO). The 心臟血管攝影檢查報告 contains stent brand/length, IVUS use, lesion findings, contrast, fluoroscopy, etc.
- **eform_ncku is just a PDF iframe.** The HTML shell is empty; `<iframe src='.../imgURL/showDocument.aspx?fn=...pdf'>` points to the actual content. The `imgURL` endpoint requires no extra auth on the intranet.
- **EMR URL is intranet-only.** `hisweb.hosp.ncku` is not publicly accessible.

## License

MIT

## Related

- [euroscore_NCKUH](https://github.com/alexdodochen/euroscore_NCKUH) — same author, EuroSCORE II pipeline using a similar fetch pattern
- [Claude-Gemini-Dialogue](https://github.com/alexdodochen/Claude-Gemini-Dialogue) — the delegation wrapper used in step 4
