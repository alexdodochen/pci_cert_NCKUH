"""Render a filled PCI cert cheatsheet docx from the template + a filled YAML.

Approach:
- Open the template docx with python-docx
- Walk the tables; each is a 2-column row: [label | value/example]
- For each label we recognize, write the value into the right cell, replacing any
  example placeholder text (anything matching `(例:...)` or empty).
- For the Evidence Checklist table, replace ☐ with ☑ where `found: true`, keep ☐
  for false/null, and append the location/note into the rightmost cell.
- Save as `out_docx/<chart>_<name_code>_filled.docx`.
"""
import sys
import io
import re
import yaml
from pathlib import Path
from copy import deepcopy

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from docx import Document  # type: ignore
from docx.oxml.ns import qn

from config import (
    TEMPLATE_DOCX as TEMPLATE, FILLED_DOCX_DIR as OUT_DIR,
    GEMINI_WORKSPACE, load_cases,
)

OUT_DIR.mkdir(exist_ok=True)


def cell_text(cell):
    return "".join(p.text for p in cell.paragraphs)


def set_cell_text(cell, text):
    """Replace a cell's full text with `text`, preserving the first paragraph's
    style. Multi-line text becomes multiple paragraphs."""
    # Remove all but first paragraph
    p0 = cell.paragraphs[0]
    for p in list(cell.paragraphs[1:]):
        p._element.getparent().remove(p._element)
    # Clear runs in p0
    for r in list(p0.runs):
        r._element.getparent().remove(r._element)
    lines = (text or "").split("\n")
    p0.add_run(lines[0])
    for line in lines[1:]:
        new_p = cell.add_paragraph()
        new_p.add_run(line)


def label_match(label, target):
    """Match if `target` keyword appears in cleaned label text."""
    return target in label


# ---------- Section ① — ⑥ scalar fillers ----------

# Map (label keyword) -> function(yaml) -> str
def scalar_fillers(y):
    """Return list of (label_keyword, value) tuples for the 2-col scalar tables."""
    stents = y.get("stents") or []
    stent_lines = []
    for s in stents:
        site = s.get("site", "?")
        typ = s.get("type", "?")
        bs = s.get("brand_size") or ""
        cnt = s.get("count", "?")
        stent_lines.append(f"{site}: {typ} × {cnt}" + (f"  [{bs}]" if bs else ""))
    stent_block = "\n".join(stent_lines) if stent_lines else "—"

    total_count = y.get("total_stent_count_this_session")
    prior_count = y.get("prior_stent_count")
    total_str = f"本次 {total_count} 支"
    if prior_count:
        total_str += f"  (含 prior {prior_count} 支 → 累積 {(total_count or 0)+prior_count})"

    timi = y.get("final_timi_flow") or "—"
    contrast = y.get("contrast_volume_ml")
    contrast_str = f"{contrast} mL" if contrast is not None else "—"
    fluoro = y.get("fluoroscopy_time_min")
    fluoro_str = f"{fluoro} min" if fluoro is not None else "—"
    door_to_dev = y.get("door_to_device_min")
    door_str = f"{door_to_dev} min" if door_to_dev is not None else "—"

    syntax = y.get("syntax_score")
    syntax_str = str(syntax) if syntax not in (None, "null") else "—"

    fillers = [
        ("病歷號 Chart No.", y.get("chart_no", "")),
        ("姓名", y.get("name_code", "")),
        ("PCI 日期", y.get("pci_date", "")),
        ("Operator", y.get("operator", "")),
        ("Demographics", y.get("demographics_comorbidities", "")),
        ("Presentation", y.get("presentation", "")),
        ("病灶位置", y.get("lesion_summary", "")),
        ("SYNTAX score", syntax_str),
        ("為何選 PCI", y.get("why_pci_not_cabg", "")),
        ("Stent 數量", stent_block + "\n\n" + total_str),
        ("Total stent length", f"{y.get('total_stent_length_mm')} mm" if y.get("total_stent_length_mm") is not None else "—"),
        ("使用的 imaging", y.get("imaging_used", "")),
        ("Adjunctive devices", y.get("adjunctive_devices", "")),
        ("為何需要 >5 支", y.get("why_more_than_5_stents", "")),
        ("Final TIMI flow", timi),
        ("Procedural complication", y.get("procedural_complication", "")),
        ("Contrast volume", contrast_str),
        ("Fluoroscopy time", fluoro_str),
        ("Door-to-device", door_str),
        ("被點到時這樣開場", y.get("opening_one_liner", "")),
    ]
    return fillers


# ---------- Evidence Checklist (section ⑤) ----------

CHECKLIST_LABELS = [
    ("PCI 知情同意書", "pci_consent"),
    ("Heart Team", "heart_team_or_cath_conference"),
    ("CV Surgery 照會", "cv_surgery_consult"),
    ("其他相關照會", "other_consults"),
    ("家庭會議", "family_meeting"),
    ("CDS 警示", "cds_alerts"),
    ("術前 echo", "preop_imaging_or_function"),
    ("術後追蹤", "postop_followup"),
]


def fill_checklist(table, checklist):
    """The checklist table has rows: [☐, 項目, 病歷位置/備註]. Fill rows by matching label."""
    if not checklist:
        return
    for row in table.rows:
        if len(row.cells) < 3:
            continue
        item_text = cell_text(row.cells[1])
        for label_key, yaml_key in CHECKLIST_LABELS:
            if label_key in item_text:
                entry = checklist.get(yaml_key) or {}
                found = entry.get("found")
                checkbox = "☑" if found is True else ("☒" if found is False else "☐")
                set_cell_text(row.cells[0], checkbox)
                loc = entry.get("location") or ""
                note = entry.get("note") or ""
                merged = []
                if loc:
                    merged.append(f"位置/日期: {loc}")
                if note:
                    merged.append(f"備註: {note}")
                if merged:
                    set_cell_text(row.cells[2], "\n".join(merged))
                break


# ---------- Q&A (section ⑦) ----------

def fill_qa(doc, questions):
    """Find the Q1/Q2/Q3 rows and fill each. Q labels in template are 'Q1:' etc."""
    q_idx = 0
    for tbl in doc.tables:
        for row in tbl.rows:
            if len(row.cells) < 2:
                continue
            label = cell_text(row.cells[0]).strip()
            m = re.match(r"^Q(\d+):", label)
            if m:
                if q_idx < len(questions):
                    q = questions[q_idx]
                    set_cell_text(row.cells[0], f"Q{m.group(1)}: {q.get('q', '')}")
                    set_cell_text(row.cells[1], q.get("a", ""))
                q_idx += 1


# ---------- Main ----------

GROUP2_TITLE_RE = re.compile(r"PCI\s*認證病歷小抄\s*—\s*第二組")


def drop_group_two(doc):
    """The template has both 第一組 (Stent>5) and 第二組 (Cover stent) — delete
    everything from the Group-2 title table onward."""
    body = doc.element.body
    boundary = None
    for child in list(body):
        text = "".join(t.text or "" for t in child.iter(qn("w:t")))
        if GROUP2_TITLE_RE.search(text):
            boundary = child
            break
    if boundary is None:
        return
    seen = False
    for child in list(body):
        if child is boundary:
            seen = True
        if seen:
            if child.tag == qn("w:sectPr"):
                continue
            body.remove(child)


def fill_doc(template_path, yaml_data, output_path):
    doc = Document(str(template_path))

    drop_group_two(doc)

    fillers = scalar_fillers(yaml_data)
    used = set()

    for tbl in doc.tables:
        for row in tbl.rows:
            cells = row.cells
            if len(cells) < 2:
                continue
            label = cell_text(cells[0]).strip()
            if not label:
                continue
            for i, (kw, val) in enumerate(fillers):
                if i in used:
                    continue
                if kw in label:
                    set_cell_text(cells[1], str(val) if val is not None else "—")
                    used.add(i)
                    break

        first_row_cells = tbl.rows[0].cells if tbl.rows else []
        if len(first_row_cells) >= 3:
            first_text = cell_text(first_row_cells[1])
            if "項目" in first_text:
                fill_checklist(tbl, yaml_data.get("evidence_checklist") or {})

    fill_qa(doc, yaml_data.get("likely_questions") or [])

    doc.save(str(output_path))
    return output_path


def main():
    gemini_out = GEMINI_WORKSPACE / "out"
    for case in load_cases():
        chart = case["chart"]
        yaml_path = gemini_out / f"case_{chart}_filled.yaml"
        if not yaml_path.exists():
            print(f"  {chart}: skip ({yaml_path.name} not found)")
            continue
        y = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        name_code = (y.get("name_code") or chart).replace("/", "")
        out_path = OUT_DIR / f"{chart}_{name_code}_filled.docx"
        fill_doc(TEMPLATE, y, out_path)
        print(f"  rendered -> {out_path}")


if __name__ == "__main__":
    main()
