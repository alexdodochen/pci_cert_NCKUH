# PCI 認證病歷小抄 — 第一組 (Stent > 5) — YAML schema

**核心原則**：每一個寫進報告的事實都要附 `_src` 標註它從 **EMR 哪個按鈕 + 哪個日期** 找到，因為使用者必須在認證委員前直接點開 EMR 顯示。

`_src` 用 EMR 樹狀目錄裡的**按鈕原文**（中英都按它顯示的字面），加上文件日期：
- `"Admission Note(*) — 2025/01/26"`
- `"Discharge Note(*) — 2025/02/18"`
- `"問題表列 — 2025/02/18"`
- `"Diagnosis — 2025/01/26"`
- `"檢驗報告 / 心臟血管攝影檢查報告 — 2025/02/07"`  ← 心導管報告住這
- `"Order(醫囑清單) — 2025/01/26 起"`
- `"會診紀錄 / 復健科 陳廷彥 — 2025/02/11"`
- `"抗生素照會 — 2025/02/06"`
- `"心導管室檢查後交班單(II) — 2025/02/07"`  (eform-PDF)
- `"心導管室檢查前交班單(I) — 2025/02/07"`
- `"同意書 — 2025/01/26"` 或 `"住院同意書 — 2025/01/26"`
- `"出院帶藥 — 2025/02/18"`
- `"TPR — 入院期間"` (連續資料時)

若同一事實來自多個位置（最理想），用 `+` 連接：`"Admission Note(*) — 2025/01/26 + 檢驗報告 / 心臟血管攝影檢查報告 — 2025/02/07"`。

**禁止**：發明 EMR 按鈕名稱。若無法定位 → `_src: "未在 EMR 找到"`，並把對應 value 設 null。

---

```yaml
# ============================================================
# ① 病人識別
# ============================================================
chart_no:        "12345678"
name_code:       "王O明"
pci_date:        "YYYY/MM/DD"
operator:        "主術者姓名"
operator_src:    "心導管室檢查後交班單(II) — YYYY/MM/DD"  # 或 "檢驗報告 / 心臟血管攝影檢查報告 — YYYY/MM/DD"

# ============================================================
# ② Case 概要
# ============================================================
demographics_comorbidities: |
  e.g. 94 y/o female, HTN, parkinsonism, prior PE (PESI IV intermediate-low)
demographics_comorbidities_src: "Admission Note(*) — YYYY/MM/DD"

presentation:    "STEMI / NSTEMI / UA / Stable angina / Silent ischemia"
presentation_src: "Admission Note(*) — YYYY/MM/DD + Diagnosis — YYYY/MM/DD"

lesion_summary: |
  LM/LAD/LCX/RCA 病灶位置、長度、Medina、calcification、CTO
lesion_summary_src: "檢驗報告 / 心臟血管攝影檢查報告 — YYYY/MM/DD"

syntax_score:    null
syntax_score_src: "檢驗報告 / 心臟血管攝影檢查報告 — YYYY/MM/DD"  # 或 "未在 EMR 找到"

why_pci_not_cabg: |
  Heart team 結論 / patient preference / 手術風險
why_pci_not_cabg_src: "Discharge Note(*) — YYYY/MM/DD"  # 或 會診紀錄 / 心臟外科 — YYYY/MM/DD

# ============================================================
# ③ Stent 策略
# ============================================================
stents:
  - {site: "LAD", type: "DES", brand_size: "Onyx 3.0/30", count: 1}
  - {site: "RCA", type: "DES", brand_size: "...",         count: 2}
stents_src: "檢驗報告 / 心臟血管攝影檢查報告 — YYYY/MM/DD + 心導管室檢查後交班單(II) — YYYY/MM/DD"

total_stent_count_this_session: 0
prior_stent_count: 0
prior_stent_src: "Admission Note(*) past hx — YYYY/MM/DD"

total_stent_length_mm: null

imaging_used: "IVUS / OCT / 無"
imaging_used_src: "檢驗報告 / 心臟血管攝影檢查報告 — YYYY/MM/DD"

adjunctive_devices: "Rotablation / IVL / OPN / cutting / scoring / 無"
adjunctive_devices_src: "檢驗報告 / 心臟血管攝影檢查報告 — YYYY/MM/DD"

why_more_than_5_stents: |
  e.g. Diffuse 3-vessel disease + bifurcation, full coverage 必要

# ============================================================
# ④ 結果與安全性
# ============================================================
final_timi_flow: "TIMI 3"
final_timi_flow_src: "檢驗報告 / 心臟血管攝影檢查報告 — YYYY/MM/DD"

procedural_complication: "無 / 描述"
procedural_complication_src: "檢驗報告 / 心臟血管攝影檢查報告 — YYYY/MM/DD + 心導管室檢查後交班單(II) — YYYY/MM/DD"

contrast_volume_ml: null
contrast_volume_src: "檢驗報告 / 心臟血管攝影檢查報告 — YYYY/MM/DD"

fluoroscopy_time_min: null
fluoroscopy_time_src: "檢驗報告 / 心臟血管攝影檢查報告 — YYYY/MM/DD"

door_to_device_min: null
door_to_device_src: null

# ============================================================
# ⑤ Evidence Checklist
# location 已是 _src 等價;按 EMR 按鈕原文 + 日期
# ============================================================
evidence_checklist:
  pci_consent:
    found: true|false|null
    location: "同意書 — YYYY/MM/DD (頁碼/簽名日期)"
    note: "確認複雜病灶/多支架風險欄位有勾選"
  heart_team_or_cath_conference:
    found: ?
    location: "Cath conference 紀錄 / 會議日期"
    note: ">5 stents 強烈建議事前討論"
  cv_surgery_consult:
    found: ?
    location: "會診紀錄 / 心臟外科 — YYYY/MM/DD"
    note: "高 SYNTAX 或 LM 病灶建議有"
  other_consults:
    found: ?
    location: "列出單號/科別/日期"
    note: null
  family_meeting:
    found: ?
    location: "Discharge Note(*) 段落 / 護理紀錄(New) — YYYY/MM/DD"
    note: null
  cds_alerts:
    found: ?
    location: "Order(醫囑清單) — 起日"
    note: "CIN / 出血風險 / 過敏 / 抗凝藥提醒"
  preop_imaging_or_function:
    found: ?
    location: "檢驗報告 / 心臟超音波 — YYYY/MM/DD"
    note: "LVEF / chamber size 摘要"
  postop_followup:
    found: ?
    location: "出院帶藥 — YYYY/MM/DD + 門診預約"
    note: "DAPT 處方 / OPD f/u"

# ============================================================
# ⑥ 報告口袋句
# ============================================================
opening_one_liner: |
  e.g. "94 歲女性 HTN/Parkinsonism, 因 NSTEMI + 急性肺水腫入院..."

# ============================================================
# ⑦ 評委可能追問
# ============================================================
likely_questions:
  - q: "為何選 PCI 不選 CABG?"
    a: "..."
  - q: "為何沒用 IVUS/OCT?"
    a: "..."
  - q: "DAPT 期程?"
    a: "..."

# ============================================================
# ⑧ EuroSCORE II — 用於佐證「為何選 PCI 不選 CABG」
# **不要計算分數！** 只填 inputs 與 rationale。分數由 Python 計算回填。
# ============================================================
euroscore_ii:
  inputs:
    age: <int>                              # 入院日的年齡
    female: <bool>
    weight_kg: <float|null>
    cr_mg_dl: <float|null>                  # 入院期間最近一筆 CREA
    egfr: <float|null>
    nyha: "I"|"II"|"III"|"IV"               # 無資訊預設 "I"
    ccs4: <bool>                            # 只有 "rest angina with no functional capacity" 才 true
    iddm: <bool>                            # Order list 有 insulin/glargine/aspart/... 才 true
    extracardiac_arteriopathy: <bool>       # PAOD/carotid stenosis>50%/claudication/aortic intervention
    chronic_pulmonary_disease: <bool>       # COPD/asthma on chronic bronchodilator/steroid
    poor_mobility: <bool>                   # AD 寫 partially dependent/dependent 才 true
    previous_cardiac_surgery: <bool>        # 開心 CABG/valve/congenital;PCI/cath 不算
    active_endocarditis: <bool>             # 仍在抗生素治療中的 IE
    critical_preop: <bool>                  # IABP/ECMO/shock/acute resp failure/decomp HF/VT-VF/preop inotrope/oliguria
    lv_function: "good"|"moderate"|"poor"|"very_poor"  # LVEF >50 / 31-50 / 21-30 / ≤20
    recent_mi: <bool>                       # 入院前 90 天內 MI
    pa_systolic: "none"|"31_55"|"ge_55"     # PASP from echo
    renal: "normal"|"cc_50_85"|"cc_le_50"|"dialysis"  # 由 Cockcroft-Gault 算
    urgency: "elective"|"urgent"|"emergency"|"salvage"
    weight_of_procedure: "isolated_cabg"|"single_non_cabg"|"two"|"three_plus"  # PCI cert 一律當 isolated_cabg
    thoracic_aorta: false
  rationale:
    nyha: "AD physical: ... → ?"
    ccs4: "AD/DC: ... → ?"
    iddm: "Order list: ... → ?"
    extracardiac_arteriopathy: "PL/Dx: ... → ?"
    chronic_pulmonary_disease: "Dx: ... → ?"
    poor_mobility: "AD social hx: ... → ?"
    previous_cardiac_surgery: "AD past hx: ... → ?"
    active_endocarditis: "Order/Dx: ... → ?"
    critical_preop: "DC hospital course: ... → ?"
    lv_function: "Echo (160025K01588) 2025/02/03 LVEF 67.7% → good"
    recent_mi: "AD: NSTEMI 2025/01/26 → Y"
    pa_systolic: "Echo: ... → ?"
    renal: "Cr 1.2 mg/dL 2025/01/27, age 94, weight 50.4kg → CC ≈ 23 → cc_le_50"

# ============================================================
# 來源/備註
# ============================================================
_caveats: |
  - 本次 stent 數 vs 累積 stent 數
  - 哪些 _src 標 "未在 EMR 找到"
```

**Final note**: be paranoid about provenance. If a fact's `_src` cannot point at a real EMR button + concrete date, set the value to null and `_src` to `"未在 EMR 找到"`. Do not invent doctype names; use **exactly** the strings shown above as they appear in the EMR tree.
