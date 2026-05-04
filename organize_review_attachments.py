"""Copy & rename all extracted scanned forms / PDFs / cath report into a single
review-friendly folder with descriptive Chinese filenames.

Output: _review_attachments_<chart>/
"""
import io
import re
import shutil
import sys
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from config import EMR_PDF_DIR, EMR_RAW_DIR, ROOT, load_cases

# Map: file pattern in _emr_pdfs/ -> (display order prefix, descriptive name template)
CAMERA_NAMES = {
    "027": ("01", "住院轉床轉科異動表"),
    "031": ("02", "出院準備服務表單"),
    "032_p1": ("03a", "同意書_愛滋篩檢"),
    "032_p2": ("03b", "同意書_住院許可證"),
    "032_p3": ("03c", "同意書_安寧共照服務說明書"),
    "032_p4": ("03d", "同意書_安寧病房療護同意書"),
    "033": ("04", "DNR同意書"),
    "058": ("05", "家庭會議紀錄_第一份"),
    "059": ("06", "家庭會議紀錄_第二份"),
}

EFORM_NAMES = {
    "EMR-3-04-001": ("07", "心導管室病人安全把關"),
    "EMR-3-CR-002": ("08", "心導管室檢查前交班單"),
    "EMR-3-CR-001": ("09", "心導管室檢查後交班單"),
    "EMR-3-07-004": ("10", "安寧共照_收案申請書"),
    "EMR-3-07-005": ("11", "安寧共照_服務內容紀錄"),
    "EMR-3-07-006": ("12a", "安寧居家照護首頁"),
    "EMR-3-07-007": ("12b", "安寧居家_07"),
    "EMR-3-07-008": ("12c", "安寧居家_08"),
    "EMR-3-07-009": ("12d", "安寧居家_09"),
    "EMR-3-07-010": ("12e", "安寧居家_10"),
    "EMR-3-07-011": ("12f", "安寧居家_11"),
    "EMR-3-07-014": ("12g", "安寧居家_14"),
    "EMR-3-07-015": ("12h", "安寧居家_15"),
    "EMR-3-07-016": ("12i", "安寧居家_16"),
    "EMR-3-N0-091": ("13", "善終準備備忘錄"),
}


def organize(chart):
    out_dir = ROOT / f"_review_attachments_{chart}"
    out_dir.mkdir(exist_ok=True)
    print(f"=== Organizing review attachments for {chart} into {out_dir.name} ===")

    copied = 0

    # 1. Camera scans (JPGs)
    for jpg in sorted(EMR_PDF_DIR.glob(f"{chart}_camera_*.jpg")):
        m = re.match(rf"{chart}_camera_(\d+)_p(\d+)\.jpg", jpg.name)
        if not m:
            continue
        kind, page = m.group(1), int(m.group(2))
        # Try page-specific match first (e.g., 032_p1)
        key = f"{kind}_p{page}"
        if key in CAMERA_NAMES:
            prefix, label = CAMERA_NAMES[key]
            dst_name = f"{prefix}_{label}.jpg"
        elif kind in CAMERA_NAMES:
            prefix, label = CAMERA_NAMES[kind]
            dst_name = f"{prefix}_{label}_p{page}.jpg"
        else:
            dst_name = f"99_camera_{kind}_p{page}.jpg"
        dst = out_dir / dst_name
        shutil.copy2(jpg, dst)
        copied += 1

    # 2. Eform PDFs
    for pdf in sorted(EMR_PDF_DIR.glob(f"{chart}_g*_EMR-*.pdf")):
        m = re.search(r"_(EMR-\d-[A-Z0-9]+-\d+)_", pdf.name)
        if not m:
            continue
        tc = m.group(1)
        if tc in EFORM_NAMES:
            prefix, label = EFORM_NAMES[tc]
            dst_name = f"{prefix}_{label}.pdf"
        else:
            dst_name = f"98_{tc}.pdf"
        dst = out_dir / dst_name
        shutil.copy2(pdf, dst)
        copied += 1

    # 3. Cath OP report (text from exam viewer)
    cath_html = EMR_RAW_DIR / f"{chart}_exam_reports.txt"
    if cath_html.exists():
        # Extract just the cath report section
        text = cath_html.read_text(encoding="utf-8")
        cath_start = text.find("心臟血管攝影檢查報告")
        if cath_start > 0:
            # Find the section start (find preceding marker)
            section_start = text.rfind("===", 0, cath_start)
            if section_start < 0:
                section_start = max(0, cath_start - 200)
            cath_end = text.find("=== ", cath_start + 50)
            if cath_end < 0:
                cath_end = len(text)
            cath_text = text[section_start:cath_end]
            dst = out_dir / "00_cath_OP_report.txt"
            dst.write_text(cath_text.strip(), encoding="utf-8")
            copied += 1

    # 4. Case summary markdown
    summary = ROOT / f"_case_summary_{chart}.md"
    if summary.exists():
        dst = out_dir / f"00_case_summary.md"
        shutil.copy2(summary, dst)
        copied += 1

    # 5. Word review doc
    docx = ROOT / "_filled_docx" / f"{chart}_嚴O龍_review.docx"
    # 用 glob 不寫死姓名
    for d in (ROOT / "_filled_docx").glob(f"{chart}_*_review.docx"):
        dst = out_dir / f"00_review.docx"
        shutil.copy2(d, dst)
        copied += 1
        break

    print(f"   {copied} files copied")
    print(f"   -> {out_dir}")


def main():
    cases = load_cases()
    if not cases:
        raise SystemExit("cases.csv empty")
    for case in cases:
        organize(case["chart"])


if __name__ == "__main__":
    main()
