"""
actions/apply_to_jobs/apply_to_indeed.py

Fetch easy-apply Indeed jobs matching software keywords, then apply.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any
import time
import requests
from hyperSel import instance, parser, log
import random

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from some_keywords import SOFTWARE_KEYWORDS

INDEED_DB = ROOT / "src/_indeed_jobs/database.sqlite"


def get_indeed_easy_apply_jobs() -> list[dict[str, Any]]:
    if not INDEED_DB.exists():
        print(f"Indeed DB not found: {INDEED_DB}")
        return []

    kw_clauses = " OR ".join(["LOWER(title) LIKE ?" ] * len(SOFTWARE_KEYWORDS))
    params: list[Any] = [f"%{kw.lower()}%" for kw in SOFTWARE_KEYWORDS]

    sql = f"""
        SELECT * FROM items
        WHERE is_easy_apply = 1
          AND ({kw_clauses})
    """

    conn = sqlite3.connect(INDEED_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def main() -> None:
    jobs = get_indeed_easy_apply_jobs()
    random.shuffle(jobs)
    print(f"Found {len(jobs)} easy-apply Indeed jobs matching keywords.")
    browser = instance.Browser(
        driver_choice="selenium",
        headless=False,
        zoom_level=100,
    )
    browser.init_browser()
    browser.go_to_site("https://ca.indeed.com/")
    input("I AM NOW LOGGED IN ")
    
    for job in jobs:
        print(job)
        url = job.get("url")
        time.sleep(2)
        browser.go_to_site(url)
        soup = browser.return_current_soup()   
        print("len(str(soup))", len(str(soup)))
        if "We can’t find this page".lower() in str(soup).lower():
            print("Page not found, skipping.")
            continue  
        
        # APPLICATION PROCESS
        print("BEGINNIG APPLICATION PROCESS")
        
        log.checkpoint()
        apply_now_xpath = '''/html/body/div/div/div[2]/div[3]/div/div/div[1]/div[2]/div[5]/div[1]/div/div/div/div/span/div/button'''
        browser.click_element(by_type="xpath", value=apply_now_xpath)
        
        
        while True:
            time.sleep(2)
            # DIAGNOSE AT EACH NEW PAGE WHAT THEY ARE ASKING FOR
            soup = browser.return_current_soup()
            question_xpath_section ='''/html/body/div[2]/div/div/div[1]/div/div/div[2]/div[2]/div/div/div/main/div[1]/div'''
            current_url = browser.WEBDRIVER.current_url
            print("CURRENT URL", current_url)
            
            # HUGE IF TREE
            if current_url == 'https://smartapply.indeed.com/beta/indeedapply/form/resume-selection-module/resume-selection':
                log.checkpoint()     
                          
                for i in range(1,7):
                    button_xpath = f'''//*[@id="mosaic-provider-module-apply-resume-selection"]/div/div/div/div/form/div/button[{i}]'''
                    
                    print("TRYING BUTTON", button_xpath)
                    try:      
                        browser.click_element(by_type="xpath", value=button_xpath,timeout=3)
                        time.sleep(2)
                        print("BREAKING INNER LOOP")
                        break
                    except Exception as e:
                        print("Error clicking button [1]:", e)
                        continue
            
            try:
                question_section = browser.get_elements(by_type="xpath", value=question_xpath_section)
                for j in question_section:
                    print("QUESTION SECTION", j)
            except Exception as e:
                print("Error getting data on page button [2]:", e)
            

        
        input("--")



if __name__ == "__main__":
    main()
