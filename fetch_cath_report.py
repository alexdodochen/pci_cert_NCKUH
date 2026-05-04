"""Fetch cath OP report (心臟血管攝影檢查報告) for each chart in cases.csv,
using Selenium because the lab popup uses a dynamic TreeView that requests
cannot reach.

Navigation pattern adapted from D:\\學術\\hospital_automation_postdilate.py.

Auth: user logs in manually in the opened Chrome window (no creds stored).
Then press Enter in terminal to let the script take over.

Output: _emr_raw/<chart>_cath_op_report.txt + _emr_raw/<chart>_cath_op_report.html
"""
import os
import re
import sys
import time

# config.py requires EMR_SESSION; Selenium handles auth via cookies, so dummy it
os.environ.setdefault("EMR_SESSION", "selenium-managed")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from config import EMR_RAW_DIR, load_cases

# Login URL: session in URL is a placeholder; ASP.NET creates a fresh session on login.
LOGIN_URL = "http://hisweb.hosp.ncku/Emrquery/(S(00000000000000000000000000))/tree/tlogin.aspx"

# Reports we want and how to date-match
CATH_KEYWORDS_REPORT_NAME = ["心臟血管攝影檢查報告", "心臟血管造影檢查報告", "Cardiac Cath", "Coronary"]
CATH_KEYWORDS_TEXT = ["coronary", "stenosis", "TIMI", "POBA", "stent", "PCI", "心臟血管攝影"]


def login(driver):
    """Open login page and wait for the user to authenticate manually."""
    print("[login] 開啟登入頁...")
    driver.get(LOGIN_URL)
    print("[login] 請在 Chrome 視窗手動輸入帳密 + 認證碼並點 Login，登入成功後在這按 Enter")
    input()
    # Wait until leftFrame appears (= login successful)
    WebDriverWait(driver, 60).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "leftFrame")))
    driver.switch_to.default_content()
    print("[login] 偵測到 leftFrame，登入成功")


def query_chart(driver, chart):
    driver.switch_to.default_content()
    WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "topFrame")))
    inp = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "txtChartNo")))
    inp.clear()
    inp.send_keys(chart)
    driver.find_element(By.ID, "BTQuery").click()
    driver.switch_to.default_content()
    time.sleep(1)


def request_access_if_needed(driver):
    try:
        driver.switch_to.default_content()
        WebDriverWait(driver, 3).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "topFrame")))
        apply_btn = driver.find_element(By.XPATH, "//a[contains(text(), '線上申請')]")
        print("[access] 病歷需線上申請，submit B01...")
        apply_btn.click()
        driver.switch_to.default_content()
        WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "mainFrame")))
        Select(WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "DropDownList1")))).select_by_value("B01")
        driver.find_element(By.ID, "Button1").click()
        time.sleep(2)
        # re-query to refresh
        driver.switch_to.default_content()
        WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "topFrame")))
        driver.find_element(By.ID, "BTQuery").click()
        time.sleep(1)
    except Exception:
        return  # no apply needed


def open_lab_popup(driver):
    """Click 檢驗檢查 → 檢驗報告 in leftFrame to open EMROutcome popup."""
    main = driver.current_window_handle
    driver.switch_to.default_content()
    WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "leftFrame")))
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '檢驗檢查')]"))).click()
    report_link = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '檢驗報告')]")))
    report_link.click()
    WebDriverWait(driver, 20).until(EC.number_of_windows_to_be(2))
    popup = [w for w in driver.window_handles if w != main][0]
    driver.switch_to.window(popup)
    return main, popup


def date_to_yyyymmdd(pci_date_str):
    y, m, d = pci_date_str.split("/")
    return f"{y}{int(m):02d}{int(d):02d}"


def date_to_iso(pci_date_str):
    y, m, d = pci_date_str.split("/")
    return f"{y}-{int(m):02d}-{int(d):02d}"


def find_cath_report(driver, chart, pci_date_str):
    """Inside the popup, set date window, click 心臟內科檢查報告, scan rows."""
    target_iso = date_to_iso(pci_date_str)
    target_yyyymmdd = date_to_yyyymmdd(pci_date_str)
    # 1-month window around PCI date
    y, m, d = pci_date_str.split("/")
    start_yyyy = f"{int(y)}{int(m):02d}01"
    end_yyyy = f"{int(y)}{(int(m) % 12) + 1:02d}28" if int(m) < 12 else f"{int(y) + 1}0128"

    # Set date range
    try:
        sd = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "txtBeginDay")))
        sd.clear(); sd.send_keys(start_yyyy)
        ed = driver.find_element(By.ID, "txtEndDay")
        ed.clear(); ed.send_keys(end_yyyy)
        driver.find_element(By.ID, "btnQuery").click()
        print(f"[range] {start_yyyy} ~ {end_yyyy} -> 查詢")
        time.sleep(1.5)
    except Exception as e:
        print(f"[range] 日期欄位找不到（可能該頁無此控件）: {e}")

    # Try to click 心臟內科檢查報告 node
    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
            (By.XPATH, "//a[contains(text(), '心臟內科檢查報告')]")
        )).click()
        print("[tree] 點開 心臟內科檢查報告")
        time.sleep(1)
    except TimeoutException:
        print("[tree] 沒有 心臟內科檢查報告 子節點 — 可能直接是報告清單")

    # Read all report rows
    rows_xpath = "//div[contains(@class, 'cssReportHead')]"
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.XPATH, rows_xpath)))
    except TimeoutException:
        print("[scan] 沒有任何 cssReportHead 報告 row")
        return None, None

    rows = driver.find_elements(By.XPATH, rows_xpath)
    print(f"[scan] 找到 {len(rows)} 份報告，掃描中...")

    for i, row in enumerate(rows):
        try:
            row_text = row.text
            # Cheap pre-filter: name OR date in the header text
            name_hit = any(kw in row_text for kw in CATH_KEYWORDS_REPORT_NAME)
            date_hit = (target_iso in row_text) or (target_yyyymmdd in row_text)

            if not (name_hit or date_hit):
                continue

            print(f"  [#{i+1}] candidate (name_hit={name_hit}, date_hit={date_hit})")
            row.click()
            time.sleep(1.5)
            # After click, the row's text becomes the full report
            full_text = row.text

            looks_like_cath = (
                any(kw in full_text for kw in CATH_KEYWORDS_REPORT_NAME)
                or sum(1 for kw in CATH_KEYWORDS_TEXT if kw.lower() in full_text.lower()) >= 3
            )
            if looks_like_cath:
                print(f"  [#{i+1}] 命中 cath OP report ({len(full_text):,} chars)")
                # Also grab raw inner HTML for reference
                html = row.get_attribute("outerHTML") or ""
                return full_text, html
            print(f"  [#{i+1}] 點開後內容看起來不是 cath report，繼續...")
        except Exception as e:
            print(f"  [#{i+1}] error: {e}")
            continue
    return None, None


def main():
    cases = load_cases()
    if not cases:
        raise SystemExit("cases.csv 沒有 case")

    print("啟動 Chrome...")
    driver = webdriver.Chrome()
    driver.maximize_window()

    try:
        login(driver)
    except Exception as e:
        print(f"login error: {e}")
        driver.quit()
        return

    for case in cases:
        chart = case["chart"]
        pci_date = case["pci_date"]
        print(f"\n=== chart {chart} (PCI {pci_date}) ===")

        try:
            query_chart(driver, chart)
            request_access_if_needed(driver)
            main_win, popup = open_lab_popup(driver)

            text, html = find_cath_report(driver, chart, pci_date)
            if text:
                txt_path = EMR_RAW_DIR / f"{chart}_cath_op_report.txt"
                txt_path.write_text(text, encoding="utf-8")
                print(f"-> {txt_path}")
                if html:
                    html_path = EMR_RAW_DIR / f"{chart}_cath_op_report.html"
                    html_path.write_text(html, encoding="utf-8")
                    print(f"-> {html_path}")
            else:
                print(f"!! {chart}: 未找到符合的 cath OP report")

            driver.close()
            driver.switch_to.window(main_win)
            driver.switch_to.default_content()
        except Exception as e:
            print(f"處理 {chart} 時錯誤: {e}")
            try:
                driver.switch_to.default_content()
            except Exception:
                pass

    print("\n全部完成。Chrome 仍開啟方便檢查；按 Enter 關閉。")
    input()
    driver.quit()


if __name__ == "__main__":
    main()
