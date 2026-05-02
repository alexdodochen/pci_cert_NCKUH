"""One-shot orchestrator for the PCI cert cheatsheet workflow.

Runs in order:
    1. discover_admissions.py  → _admission_map.json
    2. (per blocked chart) request_chart_access.py
    3. fetch_emr.py            → _emr_raw/<chart>_<isn>_raw.txt
    4. delegate to Gemini      → out/case_<chart>_filled.yaml
    5. render_docx.py          → _filled_docx/<chart>_<name>_filled.docx

Run with EMR_SESSION env var set (see config.py).

Step 4 (Gemini delegation) requires:
    - Claude-Gemini-Dialogue cloned at C:\\Users\\dr\\Claude-Gemini-Dialogue
    - GEMINI_CLI_TRUST_WORKSPACE=true
    - The workflow assumes you (Claude) call delegate.sh per case from the shell.
      The orchestrator only PRINTS the delegate commands — execute them yourself
      so you can audit each Gemini call.
"""
import json
import shutil
import subprocess
import sys
import io
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from config import (
    ADMISSION_MAP, EMR_RAW_DIR, FILLED_DOCX_DIR, GEMINI_WORKSPACE,
    TEMPLATE_SCHEMA, load_cases, ROOT,
)

TEMPLATE_SCHEMA_G2 = ROOT / "template_schema_group2.md"


def step(label):
    print(f"\n{'=' * 70}\n  {label}\n{'=' * 70}")


def main():
    cases = load_cases()
    if not cases:
        sys.exit("cases.csv is empty")

    step("Step 1 — discover admissions")
    subprocess.check_call([sys.executable, "discover_admissions.py"])

    step("Step 2 — handle access-blocked charts")
    amap = json.loads(ADMISSION_MAP.read_text(encoding="utf-8"))
    blocked = [c for c, info in amap.items() if info.get("access_blocked")]
    if blocked:
        print(f"  blocked charts: {blocked}")
        ans = input("  Submit 線上申請 (reason A01 醫療照護) for these? [y/N] ").strip().lower()
        if ans == "y":
            for c in blocked:
                subprocess.check_call([sys.executable, "request_chart_access.py", c, "A01"])
            print("  Re-discovering after access requests...")
            subprocess.check_call([sys.executable, "discover_admissions.py"])
        else:
            print(f"  skipped — these charts will be missing from final output")

    step("Step 3 — fetch EMR raw bundles")
    subprocess.check_call([sys.executable, "fetch_emr.py"])

    step("Step 4 — delegate per-case template fill to Gemini")
    inputs_dir = GEMINI_WORKSPACE / "inputs"
    inputs_dir.mkdir(exist_ok=True)
    shutil.copy(TEMPLATE_SCHEMA, inputs_dir / "template_schema.md")
    if TEMPLATE_SCHEMA_G2.exists():
        shutil.copy(TEMPLATE_SCHEMA_G2, inputs_dir / "template_schema_group2.md")
    amap = json.loads(ADMISSION_MAP.read_text(encoding="utf-8"))
    cmds = []
    for case in cases:
        chart = case["chart"]
        group = (case.get("group") or "1").strip()
        info = amap.get(chart) or {}
        if not info.get("matched"):
            print(f"  {chart}: skip (no admission match)")
            continue
        isn = info["matched"]["isn"]
        raw_src = EMR_RAW_DIR / f"{chart}_{isn}_raw.txt"
        if not raw_src.exists():
            print(f"  {chart}: skip ({raw_src.name} missing)")
            continue
        raw_dst = inputs_dir / f"case_{chart}_raw.txt"
        shutil.copy(raw_src, raw_dst)

        if group == "2":
            schema_file = "inputs/template_schema_group2.md"
            extra = (
                "This is a Group-2 case (Cover Stent + Elective PCI with Complication). "
                "★ Timeline timestamps (HH:MM) are critical — pull them from "
                "[護理紀錄] / [病程紀錄] / [心導管室檢查後交班單(II)]. "
                "If a timestamp is missing in EMR, set time to null and src to "
                "'未在 EMR 找到', then list it in _caveats. "
            )
        else:
            schema_file = "inputs/template_schema.md"
            extra = (
                "The cath OP report (心臟血管攝影檢查報告) is in the [檢驗報告] section. "
            )

        prompt = (
            f"Read {schema_file} and inputs/case_{chart}_raw.txt. "
            f"Fill the YAML for chart {chart} (PCI {info['pci_date']}, group {group}); "
            f"save to out/case_{chart}_filled.yaml. {extra}"
            f"Be honest about unknowns — leave fields null rather than invent. "
            f"Final stdout line must be 'DONE: out/case_{chart}_filled.yaml'."
        )
        cmd = (
            f'cd /c/Users/dr/Claude-Gemini-Dialogue && '
            f'GEMINI_CLI_TRUST_WORKSPACE=true bash scripts/delegate.sh -e '
            f'"{prompt}"'
        )
        cmds.append((chart, cmd))

    print("\n  Run these delegate commands (audit each Gemini run):\n")
    for chart, cmd in cmds:
        print(f"  # ---- chart {chart} ----")
        print(f"  {cmd}\n")

    print(f"  After all YAMLs are produced under {GEMINI_WORKSPACE / 'out'}, run:")
    print(f"    py render_docx.py")


if __name__ == "__main__":
    main()
