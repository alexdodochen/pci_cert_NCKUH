# PCI 認證病歷小抄 — 第一組 (Stent > 5) — 欄位結構

For each case, fill out the YAML below. Use **Traditional Chinese** for narrative
fields. Leave a field as `null` if EMR does not contain that information; do **not**
guess. Cite the source section in `_evidence` (e.g. `AD`, `DC`, `心導管室檢查後交班單`,
`會診紀錄/2025/02/11`, `Order`).

```yaml
# ============================================================
# ① 病人識別 (Case Identifier)
# ============================================================
chart_no:        "12345678"           # 病歷號
name_code:       "王O明"              # 姓名 (代號) — keep first char + O + last char
pci_date:        "YYYY/MM/DD"
operator:        "主術者 / first / second"   # 從 cath form / 心導管室交班單 抓

# ============================================================
# ② Case 概要
# ============================================================
demographics_comorbidities: |
  e.g. 94 y/o female, HTN, parkinsonism, pulmonary embolism (PESI class IV intermediate-low risk)
presentation:    "STEMI / NSTEMI / UA / Stable angina / Silent ischemia"
lesion_summary: |
  LAD/LCX/RCA/LM 病灶位置、長度、Medina、calcification、CTO; 用 cath/讀圖+心導管報告判斷
syntax_score:    null                 # 若 EMR 有計算過則填數字, 否則 null
why_pci_not_cabg: |
  Heart team 結論 / patient preference / 手術風險 — 找 DC、cath conference 或 consult 紀錄

# ============================================================
# ③ Stent 策略 (本組重點)
# ============================================================
stents:                               # 依序列出 (從 cath 後交班單 + DC procedure note)
  - {site: "LAD", type: "DES",    brand_size: "?", count: 0}
  - {site: "RCA", type: "DES",    brand_size: "?", count: 0}
  - {site: "LCX", type: "DES",    brand_size: "?", count: 0}
total_stent_count_this_session: 0
prior_stent_count:               0    # 從 PL/AD past history 算之前打過幾根
total_stent_length_mm:           null # 若有
imaging_used:                    "IVUS / OCT / 無" # 若無, 一句說明理由
adjunctive_devices:              "Rotablation / IVL / OPN / cutting / 無"
why_more_than_5_stents: |
  e.g. Diffuse 3-vessel disease 不適合 CABG / long lesion 需 full coverage

# ============================================================
# ④ 結果與安全性
# ============================================================
final_timi_flow:                 "TIMI 3"
procedural_complication:         "無 / 描述"
contrast_volume_ml:              null
fluoroscopy_time_min:            null
door_to_device_min:              null # 若為急性 STEMI 才需要

# ============================================================
# ⑤ 篩選條件相關紀錄查核表 (Evidence Checklist)
# 對每一項回答 found(yes/no/null) + location(EMR section + 日期) + note
# ============================================================
evidence_checklist:
  pci_consent:
    found: true|false
    location: "同意書 / 自費同意書 / pubConsent PDF — 簽名日期"
    note:    "確認複雜病灶 / 多支架 風險欄位是否有勾選"
  heart_team_or_cath_conference:
    found: ?
    location: ?
    note:    ">5 stents 強烈建議事前討論"
  cv_surgery_consult:
    found: ?
    location: "會診紀錄 / 日期"
    note:    "高 SYNTAX 或 LM 病灶建議有"
  other_consults:                # 腎臟/感染/麻醉
    found: ?
    location: "列出單號/日期"
  family_meeting:
    found: ?
    location: "護理紀錄 / 社工紀錄"
  cds_alerts:
    found: ?
    note:    "CIN / 出血風險 / 過敏 / 抗凝藥 提醒"
  preop_imaging_or_function:
    found: ?
    location: "echo / CTA / SPECT — 報告日期"
  postop_followup:
    found: ?
    note:    "DAPT 處方 / 出院衛教 / OPD f/u"

# ============================================================
# ⑥ 報告口袋句
# ============================================================
opening_one_liner: |
  e.g. "94 歲女性 HTN/Parkinsonism, 因 NSTEMI + acute pulmonary edema 入院,
  cath 顯示 3VD, 因 high surgical risk 與家屬討論後選擇 PCI, 共置 4 支 DES
  於 RCA + LCX, ACT-guided heparin, final TIMI 3, 無併發症."

# ============================================================
# ⑦ 評委可能追問 / 應答準備
# ============================================================
likely_questions:
  - q: "為何選 PCI 不選 CABG?"
    a: "..."
  - q: "為何沒有用 IVUS / OCT?"
    a: "..."
  - q: "DAPT 期程如何規劃?"
    a: "..."

# ============================================================
# 來源/備註
# ============================================================
_evidence_summary: |
  哪些欄位來自 AD vs DC vs 心導管室交班單 vs 會診; 哪些是推論
_caveats: |
  - 此 session stent 數 vs 累積 stent 數 (>5 是哪一個?)
  - cath OP report 未取得 (separate SSO) — stent 廠牌/長度/contrast vol/fluoro time 可能 null
```
