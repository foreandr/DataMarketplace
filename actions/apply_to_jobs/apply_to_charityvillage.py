"""
actions/apply_to_jobs/apply_to_charityvillage.py

Open a CharityVillage job listing in a browser and apply to it.
Internal application logic is handled by the caller.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from hyperSel import instance
from selenium.webdriver.common.by import By

from files.application_data import RESUME, COVER_LETTERS
from keywords import SOFTWARE_KEYWORDS
from net_guard import ensure_page_loaded


FIRST_NAME = "Andre"
LAST_NAME = "Foreman"
EMAIL = "foreandr@gmail.com"
PHONE = "5196363173"


def apply(job: dict[str, Any]) -> None:
    url = job.get("url")
    if not url:
        raise ValueError(f"charityvillage job missing url: {job}")

    browser = instance.Browser(
        driver_choice='selenium',
        headless=False,
        zoom_level=100,
    )
    browser.init_browser()
    browser.go_to_site(url)
    if not ensure_page_loaded(browser):
        raise ValueError("network hangup")
    # input(f"[charityvillage] Paused — press Enter to continue...")

    def step(label: str, fn) -> None:
        try:
            print(f"[charityvillage] step -> {label}")
            fn()
            print(f"[charityvillage] ok   -> {label}")
        except Exception as e:
            input(f"[charityvillage] failed at step '{label}': {e}\nPress Enter to continue...")
            raise

    def switch_to_newest_tab() -> None:
        handles = browser.get_all_tab_handles()
        if not handles:
            raise ValueError("no browser tabs found")
        browser.switch_to_tab(handles[-1])

    def is_software_title(title: str) -> bool:
        title_lower = (title or "").lower()
        if any(kw.lower() in title_lower for kw in SOFTWARE_KEYWORDS):
            return True
        signals = (
            "software",
            "developer",
            "engineer",
            "full stack",
            "frontend",
            "backend",
            "devops",
            "data",
            "machine learning",
            "ml",
            "ai",
        )
        return any(sig in title_lower for sig in signals)

    def try_upload_all_file_inputs(files_payload: str) -> None:
        # Brute-force: try every file input we can find until one accepts files.
        driver = browser.WEBDRIVER
        if driver is None:
            raise ValueError("webdriver not initialized")

        inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        # Fallback: include any input with "attach" or "upload" in attributes.
        inputs += driver.find_elements(By.CSS_SELECTOR, "input[id*='attach'], input[name*='attach'], input[id*='upload'], input[name*='upload']")

        seen = set()
        candidates = []
        for el in inputs:
            try:
                key = el.get_attribute("outerHTML")
            except Exception:
                key = None
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            candidates.append(el)

        last_err = None
        for idx, el in enumerate(candidates):
            try:
                browser.scroll_to_item_in_view(el)
                time.sleep(0.2)
                el.send_keys(files_payload)
                print(f"[charityvillage] upload succeeded on input #{idx + 1}")
                return
            except Exception as e:
                print(f"[charityvillage] upload failed on input #{idx + 1}: {e}")
                last_err = e

        raise ValueError(f"no file input accepted upload ({last_err})")

    success = False
    try:
        step("click apply button", lambda: browser.click_element(
            by_type="xpath",
            value="/html/body/div[3]/div/main/div[3]/div[1]/div/div/div/div[2]/div[2]/div[3]/div/a/button",
        ))
        step("wait after apply click", lambda: time.sleep(2.5))
        step("switch to new tab", switch_to_newest_tab)

        step("enter first name", lambda: browser.clear_and_enter_text(
            by_type="xpath",
            value="/html/body/div[3]/div/main/div[4]/div[4]/div[1]/div/div[1]/div/div/div/div[1]/div/input",
            content_to_enter=FIRST_NAME,
        ))
        step("enter last name", lambda: browser.clear_and_enter_text(
            by_type="xpath",
            value="/html/body/div[3]/div/main/div[4]/div[4]/div[1]/div/div[1]/div/div/div/div[3]/div/input",
            content_to_enter=LAST_NAME,
        ))
        step("enter email", lambda: browser.clear_and_enter_text(
            by_type="xpath",
            value="/html/body/div[3]/div/main/div[4]/div[4]/div[1]/div/div[1]/div/div/div/div[5]/div/input",
            content_to_enter=EMAIL,
        ))
        step("enter phone", lambda: browser.clear_and_enter_text(
            by_type="xpath",
            value="/html/body/div[3]/div/main/div[4]/div[4]/div[1]/div/div[1]/div/div/div/div[7]/div/input",
            content_to_enter=PHONE,
        ))

        step("click confirm", lambda: browser.click_element(
            by_type="xpath",
            value="/html/body/div[3]/div/main/div[4]/div[4]/div[1]/div/div[1]/div/div/div/div[9]/div[2]/div[1]",
        ))
        step("wait after confirm", lambda: time.sleep(1.2))

        def click_next_by_text() -> None:
            driver = browser.WEBDRIVER
            if driver is None:
                raise ValueError("webdriver not initialized")
            next_btn = driver.find_elements(
                By.XPATH,
                "//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'next') or contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'next')]",
            )
            if not next_btn:
                raise ValueError("no 'next' button found by text")
            browser.scroll_to_item_in_view(next_btn[0])
            time.sleep(0.2)
            next_btn[0].click()

        try:
            step("click next button (by text)", click_next_by_text)
        except Exception:
            input("[charityvillage] couldn't find/click Next by text — press Enter to continue...")
        step("wait after next", lambda: time.sleep(1.6))

        title = job.get("title", "")
        cover_letter_type = "swe" if is_software_title(title) else "general"
        resume_path = str(Path(RESUME))
        cover_path = str(Path(COVER_LETTERS[cover_letter_type]))
        files_payload = f"{resume_path}\n{cover_path}"
        step("upload resume + cover letter", lambda: try_upload_all_file_inputs(files_payload))
        step("wait after upload", lambda: time.sleep(1.2))

        def click_submit_by_bruteforce() -> None:
            driver = browser.WEBDRIVER
            if driver is None:
                raise ValueError("webdriver not initialized")

            buttons = driver.find_elements(By.TAG_NAME, "button")
            buttons += driver.find_elements(By.CSS_SELECTOR, "input[type='submit'], input[type='button']")
            if not buttons:
                raise ValueError("no buttons found on page")

            # Reverse order: bottom to top
            for idx, el in enumerate(reversed(buttons), 1):
                try:
                    label = (el.text or el.get_attribute("value") or "").strip()
                except Exception:
                    label = ""
                print(f"[charityvillage] trying button #{idx} -> '{label}'")
                try:
                    browser.scroll_to_item_in_view(el)
                    time.sleep(0.2)
                    try:
                        el.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", el)
                    print(f"[charityvillage] clicked button #{idx}")
                    return
                except Exception as e:
                    print(f"[charityvillage] button #{idx} failed: {e}")
                    continue

            raise ValueError("no button was clickable")

        try:
            step("click final submit (bruteforce)", click_submit_by_bruteforce)
        except Exception:
            input("[charityvillage] couldn't find/click final submit — press Enter to continue...")
        step("wait after submit", lambda: time.sleep(1.8))
        success = True
    finally:
        if success:
            try:
                browser.close_browser()
            except Exception as e:
                print(f"[charityvillage] close_browser failed: {e}")
        else:
            print("[charityvillage] leaving browser open due to failure")

