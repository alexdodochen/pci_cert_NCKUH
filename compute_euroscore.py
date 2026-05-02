"""Compute EuroSCORE II for each filled case YAML and write the score back.

Inputs:  C:\\Users\\dr\\Claude-Gemini-Dialogue\\out\\case_*_filled.yaml
Outputs: same files, mutated to add:
    euroscore_ii:
      computed:
        score_pct: <float>            # 0-100
        risk_band: "low|intermediate|high|very_high"
        cc_ml_min: <float|null>       # Cockcroft-Gault used for renal categorization
        derived_renal: <str>          # what we computed for `renal` (overrides input if input was missing)
        contributors: [...]           # top contributors with their points (in log-odds)

Uses the Nashef 2012 calculator from C:\\Users\\dr\\euroscore_NCKUH\\euroscore_ii.py.
"""
import sys
import io
import yaml
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Import the calculator from the cloned repo
sys.path.insert(0, r"C:\Users\dr\euroscore_NCKUH")
from euroscore_ii import calc, cockcroft_gault, renal_category, BETA, age_x  # type: ignore

GEMINI_OUT = Path(r"C:\Users\dr\Claude-Gemini-Dialogue\out")


def risk_band(score_pct):
    if score_pct < 2:
        return "low"
    if score_pct < 5:
        return "intermediate"
    if score_pct < 10:
        return "high"
    return "very_high"


def main_contributors(inputs):
    """Return top contributing factors (label, beta_points)."""
    pts = []
    pts.append(("age", BETA["age"] * age_x(inputs.get("age"))))
    if inputs.get("female"):
        pts.append(("female", BETA["female"]))
    nyha = (inputs.get("nyha") or "").upper()
    if nyha == "II":
        pts.append(("NYHA II", BETA["nyha_ii"]))
    elif nyha == "III":
        pts.append(("NYHA III", BETA["nyha_iii"]))
    elif nyha == "IV":
        pts.append(("NYHA IV", BETA["nyha_iv"]))
    flag_map = {
        "ccs4": "CCS class 4 angina",
        "iddm": "IDDM",
        "extracardiac_arteriopathy": "extracardiac arteriopathy",
        "chronic_pulmonary_disease": "chronic pulmonary disease",
        "poor_mobility": "poor mobility",
        "previous_cardiac_surgery": "previous cardiac surgery",
        "active_endocarditis": "active endocarditis",
        "critical_preop": "critical preop state",
        "recent_mi": "recent MI",
        "thoracic_aorta": "thoracic aorta",
    }
    for k, label in flag_map.items():
        if inputs.get(k):
            pts.append((label, BETA[k]))
    renal = inputs.get("renal") or "normal"
    if renal == "dialysis":
        pts.append(("dialysis", BETA["dialysis"]))
    elif renal == "cc_le_50":
        pts.append(("CC ≤ 50", BETA["cc_le_50"]))
    elif renal == "cc_50_85":
        pts.append(("CC 50-85", BETA["cc_50_85"]))
    lv = inputs.get("lv_function") or "good"
    if lv == "moderate":
        pts.append(("LV moderate (EF 31-50)", BETA["lv_moderate"]))
    elif lv == "poor":
        pts.append(("LV poor (EF 21-30)", BETA["lv_poor"]))
    elif lv == "very_poor":
        pts.append(("LV very poor (EF ≤20)", BETA["lv_very_poor"]))
    pa = inputs.get("pa_systolic") or "none"
    if pa == "31_55":
        pts.append(("PASP 31-55", BETA["pa_31_55"]))
    elif pa == "ge_55":
        pts.append(("PASP ≥ 55", BETA["pa_ge_55"]))
    urg = inputs.get("urgency") or "elective"
    if urg == "urgent":
        pts.append(("urgent", BETA["urgent"]))
    elif urg == "emergency":
        pts.append(("emergency", BETA["emergency"]))
    elif urg == "salvage":
        pts.append(("salvage", BETA["salvage"]))
    w = inputs.get("weight_of_procedure") or "isolated_cabg"
    if w == "single_non_cabg":
        pts.append(("single non-CABG", BETA["single_non_cabg"]))
    elif w == "two":
        pts.append(("2 procedures", BETA["two"]))
    elif w == "three_plus":
        pts.append(("3+ procedures", BETA["three_plus"]))
    pts.sort(key=lambda x: -x[1])
    return [{"factor": label, "beta": round(b, 4)} for label, b in pts if b > 0]


def process(yaml_path):
    raw = yaml_path.read_text(encoding="utf-8")
    y = yaml.safe_load(raw)
    es = y.get("euroscore_ii") or {}
    inp = es.get("inputs") or {}

    # Cockcroft-Gault if Cr provided and renal not explicit
    cc = cockcroft_gault(
        inp.get("age"), inp.get("weight_kg"), inp.get("cr_mg_dl"), inp.get("female")
    )
    derived_renal = inp.get("renal") or renal_category(cc)
    if not inp.get("renal"):
        inp["renal"] = derived_renal

    score = calc(inp)
    score_pct = round(score * 100, 2)

    es["computed"] = {
        "score_pct": score_pct,
        "risk_band": risk_band(score_pct),
        "cc_ml_min": round(cc, 1) if cc is not None else None,
        "derived_renal": derived_renal,
        "contributors": main_contributors(inp),
    }
    y["euroscore_ii"] = es

    yaml_path.write_text(
        yaml.dump(y, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
    return score_pct, risk_band(score_pct), cc


def main():
    for p in sorted(GEMINI_OUT.glob("case_*_filled.yaml")):
        score_pct, band, cc = process(p)
        cc_str = f"CC={cc:.1f}" if cc is not None else "CC=N/A"
        print(f"  {p.stem:30}  EuroSCORE II = {score_pct:5.2f}%  ({band:<13})  {cc_str}")


if __name__ == "__main__":
    main()
