# PCI 認證病歷小抄 — 第二組 (Cover Stent + Elective PCI with Complication) — YAML schema

**核心原則**：每一個寫進報告的事實都要附 `_src` 標註它從 **EMR 哪個按鈕 + 哪個日期** 找到，因為使用者必須在認證委員前直接點開 EMR 顯示。

第二組的重點與第一組不同：
1. **時間軸完整性**：併發症發生 → bailout 決策 → cover stent 部署 → CV surgery 通知 → 家屬告知 → ICU/CCU 收治。每個時間點都要有 EMR 紀錄做佐證。
2. **危機處置鏈**：是否啟動 stand-by surgery、是否做 pericardiocentesis、是否需要 ECMO/IABP。
3. **病人/家屬告知**：當下口頭告知 + 事後補簽 cover-stent 同意書 + 家庭會議 + (院內) 不良事件通報 / M&M 討論。

`_src` 用 EMR 樹狀目錄裡的**按鈕原文**（中英都按它顯示的字面），加上文件日期：
- `"Admission Note(*) — 2025/01/26"`
- `"Discharge Note(*) — 2025/02/18"`  ← hospital course 通常在這裡描述併發症
- `"問題表列 — 2025/02/18"`
- `"Diagnosis — 2025/01/26"`
- `"檢驗報告 / 心臟血管攝影檢查報告 — 2025/02/07"`  ← 心導管報告住這
- `"Order(醫囑清單) — 2025/01/26 起"`
- `"會診紀錄 / 心臟外科 林士傑 — 2025/02/07"`  ← CV surgery stand-by 紀錄
- `"會診紀錄 / 麻醉科 — 2025/02/07"`  ← anesthesia consult
- `"心導管室檢查後交班單(II) — 2025/02/07"`  (eform-PDF) ← 併發症處置摘要
- `"心導管室檢查前交班單(I) — 2025/02/07"`
- `"同意書 — 2025/01/26"` 或 `"住院同意書 — 2025/01/26"`
- `"自費同意書 — 2025/02/07"`  ← cover stent 自費同意書
- `"出院帶藥 — 2025/02/18"`
- `"護理紀錄 / 重症加護 — 2025/02/07 HH:MM"`  ← 時間戳鏈最重要
- `"病程紀錄 — 2025/02/07 HH:MM"`  ← 家屬告知的 progress note
- `"心臟功能評估報告 — 2025/02/10"`  ← post-event echo
- `"出院準備服務表單 — 2025/02/15"`

若同一事實來自多個位置（最理想），用 `+` 連接：`"心導管室檢查後交班單(II) — 2025/02/07 + 護理紀錄 — 2025/02/07 14:35"`。

**禁止**：發明 EMR 按鈕名稱。若無法定位 → `_src: "未在 EMR 找到"`，並把對應 value 設 null。

---

```yaml
# ============================================================
# ① 病人識別
# ============================================================
chart_no:        "12345678"
name_code:       "陳O美"
pci_date:        "YYYY/MM/DD"
operator:        "主術者姓名"
operator_src:    "心導管室檢查後交班單(II) — YYYY/MM/DD"

group2_subtype:  "cover_stent" | "elective_with_complication"
group2_subtype_src: "檢驗報告 / 心臟血管攝影檢查報告 — YYYY/MM/DD"

# ============================================================
# ② Case 概要
# ============================================================
demographics_comorbidities: |
  e.g. 67 y/o male, HTN, DM, CKD stage 3, prior CABG 2018
demographics_comorbidities_src: "Admission Note(*) — YYYY/MM/DD"

presentation:    "Elective / Stable angina / Recent NSTEMI 已穩定 / Chronic stable + + ischemia by stress"
presentation_src: "Admission Note(*) — YYYY/MM/DD + Diagnosis — YYYY/MM/DD"

original_pci_plan: |
  原計畫:LAD ostial 80% lesion + diffuse mid-LAD disease;預計 2 顆 DES, IVUS-guided
original_pci_plan_src: "心導管室檢查前交班單(I) — YYYY/MM/DD + 同意書 — YYYY/MM/DD"

# ============================================================
# ③ 併發症類型 (本組重點)
# ============================================================
complication_category: "Perforation Ellis I" | "Perforation Ellis II" | "Perforation Ellis III"
                       | "Slow-no reflow" | "Coronary dissection" | "Stent loss / embolism"
                       | "Tamponade" | "Side branch occlusion" | "Wire fracture" | "Other"
complication_category_src: "檢驗報告 / 心臟血管攝影檢查報告 — YYYY/MM/DD + 心導管室檢查後交班單(II) — YYYY/MM/DD"

complication_mechanism: |
  一句話描述:e.g. Wire perforation in distal LAD during CTO PCI / Slow flow after rotablation /
  Type B dissection at proximal LAD after stent deployment
complication_mechanism_src: "檢驗報告 / 心臟血管攝影檢查報告 — YYYY/MM/DD"

cover_stent_used:
  used: true|false|null
  brand_size: "BeGraft 3.0/19" | "Graftmaster 3.5/16" | null
  position: "Distal LAD" | null
cover_stent_src: "心導管室檢查後交班單(II) — YYYY/MM/DD + 自費同意書 — YYYY/MM/DD"

pericardiocentesis:
  performed: true|false|null
  drained_ml: <int|null>
  time: "YYYY/MM/DD HH:MM"   # null if not performed or no timestamp found
pericardiocentesis_src: "心導管室檢查後交班單(II) — YYYY/MM/DD + 護理紀錄 — YYYY/MM/DD HH:MM"

cv_surgery_standby:
  activated: true|false|null
  notify_time: "YYYY/MM/DD HH:MM"
  arrival_time: "YYYY/MM/DD HH:MM"
cv_surgery_standby_src: "會診紀錄 / 心臟外科 — YYYY/MM/DD HH:MM"

mcs_devices:
  ecmo: true|false|null
  iabp: true|false|null
  device_start_time: "YYYY/MM/DD HH:MM"
mcs_devices_src: "Order(醫囑清單) — YYYY/MM/DD + 護理紀錄 — YYYY/MM/DD HH:MM"

# ============================================================
# ④ 事件時間軸 ★ 第二組最重要 ★
# 每一列都要有 time + 紀錄位置(_src),時間找不到就 null;EMR 沒紀錄就標 "未在 EMR 找到"。
# ============================================================
timeline:
  complication_onset:
    time: "YYYY/MM/DD HH:MM"
    note: "e.g. distal LAD perforation 出現 contrast extravasation"
    src:  "心導管室檢查後交班單(II) — YYYY/MM/DD + 檢驗報告 / 心臟血管攝影檢查報告 — YYYY/MM/DD"
  bailout_decision:
    time: "YYYY/MM/DD HH:MM"
    note: "e.g. Decided to deploy cover stent over balloon tamponade"
    src:  "心導管室檢查後交班單(II) — YYYY/MM/DD"
  cover_stent_deployment:
    time: "YYYY/MM/DD HH:MM"
    note: "e.g. BeGraft 3.0/19 deployed at distal LAD, 14 atm × 30 sec"
    src:  "檢驗報告 / 心臟血管攝影檢查報告 — YYYY/MM/DD"
  cv_surgery_notify:
    time: "YYYY/MM/DD HH:MM"
    note: "Stand-by called / arrived / not needed"
    src:  "會診紀錄 / 心臟外科 — YYYY/MM/DD HH:MM"
  family_notification:
    time: "YYYY/MM/DD HH:MM"
    note: "★ 必須對得上 complication_onset 的時間 ★ 一句話寫告知內容"
    src:  "病程紀錄 — YYYY/MM/DD HH:MM + 護理紀錄 — YYYY/MM/DD HH:MM"
  icu_ccu_transfer:
    time: "YYYY/MM/DD HH:MM"
    note: "送 CCU / ICU / 一般病房;附理由"
    src:  "Order(醫囑清單) 轉床 — YYYY/MM/DD HH:MM + 護理紀錄 — YYYY/MM/DD HH:MM"
  followup_management:
    time: "YYYY/MM/DD"
    note: "後續處置:echo follow-up / Hb trend / DAPT 開立 / 出院"
    src:  "心臟功能評估報告 — YYYY/MM/DD + Discharge Note(*) — YYYY/MM/DD"

# ============================================================
# ⑤ Evidence Checklist
# location 已是 _src 等價;按 EMR 按鈕原文 + 日期
# ============================================================
evidence_checklist:
  original_pci_consent:
    found: true|false|null
    location: "同意書 — YYYY/MM/DD (頁碼/簽名日期)"
    note: "確認含『併發症風險』欄位有勾選"
  cover_stent_or_bailout_consent:
    found: ?
    location: "自費同意書 — YYYY/MM/DD 或 病程紀錄 (口頭同意註記) — YYYY/MM/DD HH:MM"
    note: "緊急狀況下口頭同意之紀錄,事後補簽日期"
  family_notification_record:
    found: ?
    location: "病程紀錄 — YYYY/MM/DD HH:MM + 護理紀錄 — YYYY/MM/DD HH:MM"
    note: "★ 時間戳要對得上 complication_onset ★"
  cv_surgery_realtime_consult:
    found: ?
    location: "會診紀錄 / 心臟外科 — YYYY/MM/DD HH:MM"
    note: "照會單號 / 通知時間 / 到場時間"
  anesthesia_icu_ccu_consult:
    found: ?
    location: "會診紀錄 / 麻醉科 — YYYY/MM/DD + 護理紀錄 / 重症加護 — YYYY/MM/DD"
    note: "照會單號 / 接收時間"
  family_meeting_followup:
    found: ?
    location: "病程紀錄 / 家庭會議 — YYYY/MM/DD 或 社工紀錄 — YYYY/MM/DD"
    note: "建議 24-48h 內舉行"
  cath_conference_or_mm:
    found: ?
    location: "院內 case discussion / 不良事件討論會 — YYYY/MM/DD"
    note: "若 EMR 沒有外部紀錄,標 '未在 EMR 找到' 並提醒使用者人工提供"
  hospital_incident_report:
    found: ?
    location: "通報系統編號 (若有) — YYYY/MM/DD"
    note: "依院內 SOP;EMR 通常找不到,提醒使用者人工確認"
  cds_alerts:
    found: ?
    location: "Order(醫囑清單) — YYYY/MM/DD 起"
    note: "出血風險 / 抗凝藥 / 過敏 / CIN"
  postop_followup:
    found: ?
    location: "心臟功能評估報告 — YYYY/MM/DD + Discharge Note(*) — YYYY/MM/DD"
    note: "Echo (effusion?) / Hb trend / Cr trend / OPD f/u"

# ============================================================
# ⑥ Outcome & 後續處置
# ============================================================
length_of_stay_days: <int|null>
length_of_stay_src: "Admission Note(*) — YYYY/MM/DD + Discharge Note(*) — YYYY/MM/DD"

discharge_status: "alive_stable" | "needs_rehab" | "transfer_out" | "expired"
discharge_status_src: "Discharge Note(*) — YYYY/MM/DD"

final_lvef: <float|null>          # post-event 若有 follow echo
final_lvef_src: "心臟功能評估報告 — YYYY/MM/DD"

dapt_plan:
  drugs: "Aspirin 100 mg + Ticagrelor 90 mg BID" | null
  duration: "≥12 個月" | null
dapt_plan_src: "出院帶藥 — YYYY/MM/DD"

mm_takeaway: |
  一句話的 M&M 學習點:e.g. Hydrophilic wire 在 CTO 末端 distal vessel 易致 perforation,
  下次 routine fluoro 確認 distal wire position
mm_takeaway_src: "Discharge Note(*) — YYYY/MM/DD 或 心導管室檢查後交班單(II) — YYYY/MM/DD"

# ============================================================
# ⑦ 報告口袋句
# ============================================================
opening_one_liner: |
  e.g. "67 歲男性 HTN/DM/prior CABG, elective PCI 中發生 distal LAD perforation Ellis II,
  立即 cover stent 部署成功,送 CCU 觀察, day 5 順利出院"

# ============================================================
# ⑧ 評委可能追問
# ============================================================
likely_questions:
  - q: "為何選擇 cover stent 而非 prolonged balloon inflation?"
    a: "..."
  - q: "CV surgery 是否該更早 stand-by?"
    a: "..."
  - q: "家屬告知時間是否合理?(對應 complication onset)"
    a: "..."
  - q: "有無院內通報 / M&M 討論?"
    a: "..."

# ============================================================
# 來源/備註
# ============================================================
_caveats: |
  - 哪些 timeline timestamp 在 EMR 找不到,需人工補
  - 哪些 evidence_checklist 項目 EMR 沒有,需提醒委員會以紙本/院內系統補
  - 哪些 _src 標 "未在 EMR 找到"
```

**Final note**: be paranoid about provenance. If a fact's `_src` cannot point at a real EMR button + concrete date (and ideally HH:MM for timeline events), set the value to null and `_src` to `"未在 EMR 找到"`. Do not invent doctype names; use **exactly** the strings shown above as they appear in the EMR tree. The committee will click into EMR live during the cert defense — every claim must survive a click.
