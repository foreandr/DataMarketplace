"""
actions/apply_to_jobs/apply_to_workbc.py

Open a WorkBC job listing in a browser and apply to it.
Internal application logic is handled by the caller.
"""
from __future__ import annotations

from typing import Any
import time
from hyperSel import instance
from net_guard import ensure_page_loaded

def apply(job: dict[str, Any]) -> None:
    print("ARE WE GETTING HERE")
    url = job.get("url")
    if not url:
        raise ValueError(f"workbc job missing url: {job}")

    browser = instance.Browser(
        driver_choice='selenium',
        headless=False,
        zoom_level=100,
    )
    browser.init_browser()
    browser.go_to_site(url)
    
    if not ensure_page_loaded(browser):
        browser.close_browser()
        raise ValueError("network hangup")
    
    try:
        # Get all button elements currently on the page
        buttons = browser.driver.find_elements("tag name", "button")
        print(f"Found {len(buttons)} buttons. Starting reverse click loop...")

        # Loop through buttons from last to first
        for i in range(len(buttons) - 1, -1, -1):
            btn = buttons[i]
            btn_text = btn.text.replace('\n', ' ').strip() or "NO TEXT"
            btn_class = btn.get_attribute("class")
            
            print(f"[{i}] Attempting click on: '{btn_text}' (Class: {btn_class})")
            
            try:
                # Scroll into view to ensure it is clickable
                browser.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                time.sleep(0.5) 
                btn.click()
                print(f"  --> Success")
            except Exception as e:
                print(f"  --> Failed: {str(e).splitlines()[0]}")
            
            time.sleep(1)

    except Exception as e:
        print(f"Error during button discovery: {e}")
    
    input(f"[workbc] Paused — press Enter to continue...")

    browser.close_browser()