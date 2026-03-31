"""
actions/apply_to_jobs/apply_to_indeed.py

Fetch easy-apply Indeed jobs matching software keywords, then apply.
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path
from typing import Any
import time
import requests
from hyperSel import instance, parser, log
import random
from collections import defaultdict
from datetime import date, datetime
from selenium.webdriver.support.ui import Select as SeleniumSelect

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from some_keywords import SOFTWARE_KEYWORDS

INDEED_DB   = ROOT / "src/_indeed_jobs/database.sqlite"
APPLIED_DB  = ROOT / "src/_indeed_jobs/applied_jobs.sqlite"


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

# ── Applied-jobs DB ───────────────────────────────────────────────────────── #

def _extract_jk(url: str) -> str | None:
    """Pull the 'jk' job-key from any Indeed URL — the stable canonical ID."""
    m = re.search(r'[?&]jk=([a-zA-Z0-9]+)', url or "")
    return m.group(1) if m else None


def init_applied_db() -> None:
    """Create the applied_jobs table if it doesn't exist yet."""
    APPLIED_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(APPLIED_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applied_jobs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            jk          TEXT,
            title       TEXT,
            company     TEXT,
            url         TEXT,
            applied_at  TEXT
        )
    """)
    conn.commit()
    conn.close()


def already_applied(job: dict) -> bool:
    """
    Dedup check.  Matches on jk (canonical ID) first, then falls back to
    normalised title + company so minor URL changes don't let dupes through.
    """
    if not APPLIED_DB.exists():
        return False
    url     = job.get("url", "")
    title   = (job.get("title",   "") or "").lower().strip()
    company = (job.get("company", "") or "").lower().strip()
    jk      = _extract_jk(url)
    conn = sqlite3.connect(APPLIED_DB)
    try:
        if jk:
            if conn.execute("SELECT 1 FROM applied_jobs WHERE jk=?", (jk,)).fetchone():
                return True
        if title and company:
            if conn.execute(
                "SELECT 1 FROM applied_jobs WHERE LOWER(title)=? AND LOWER(company)=?",
                (title, company),
            ).fetchone():
                return True
    finally:
        conn.close()
    return False


def record_application(job: dict) -> None:
    """Insert a successfully submitted job into applied_jobs with a timestamp."""
    url        = job.get("url", "")
    jk         = _extract_jk(url)
    title      = job.get("title",   "")
    company    = job.get("company", "")
    applied_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(APPLIED_DB)
    try:
        conn.execute(
            "INSERT INTO applied_jobs (jk, title, company, url, applied_at) VALUES (?,?,?,?,?)",
            (jk, title, company, url, applied_at),
        )
        conn.commit()
    finally:
        conn.close()
    _log(f"  -> RECORDED application: jk={jk!r}  title={title!r}  applied_at={applied_at}")


# ── Smart field defaults ──────────────────────────────────────────────────── #
DUMMY_TEXT     = "n/a"
NEXT_BTN_XPATH   = '//*[@id="mosaic-provider-module-apply-questions"]/div/div/button'
SUBMIT_BTN_XPATH = '//*[@id="mosaic-provider-module-apply-preview"]/div/div/div[3]/button'

# ── Pre-written long-form answers ─────────────────────────────────────────── #
_WORK_AUTH_ANSWER = (
    "I am a Canadian citizen and am fully authorized to work in Canada without any "
    "restrictions. I do not require, nor will I in the future require, employer "
    "sponsorship to work in Canada."
)

_PORTFOLIO_ANSWER = (
    "My portfolio is available at https://foreandr.github.io/, featuring 40+ interactive "
    "tools spanning data visualization, mathematics, graph networks, and game theory. "
    "One of the more complex user journeys I simplified was the World Data suite — users "
    "previously had to cross-reference IMF, World Bank, and WHO datasets across separate "
    "platforms; I consolidated everything into a single interactive 3D globe and flat "
    "choropleth map with unified controls, turning a multi-tab research workflow into a "
    "single spatial exploration experience. "
    "The result was a dramatically lower barrier to entry for non-specialist users trying "
    "to make sense of global economic and resource data."
)

_AI_UX_ANSWER = (
    "I integrate AI across the full development and design cycle rather than at a single "
    "stage — Claude for architecture decisions, code review, and writing clear technical "
    "documentation; GitHub Copilot and Codex for accelerating implementation so prototypes "
    "go from idea to working demo in hours instead of days; and Gemini/Bard for quick "
    "research synthesis when I need to survey a domain fast. "
    "For visual and UX work I use generative image tools to explore interface directions "
    "early, which lets me validate concepts with stakeholders before committing to "
    "high-fidelity builds. "
    "The net effect is a dramatically compressed feedback loop — I can ship a testable "
    "prototype, gather real user signal, and iterate in the same time it used to take "
    "just to finish the initial spec."
)


def _next_month_first() -> str:
    """Return YYYY-MM-DD for the 1st of next month."""
    today = date.today()
    month = today.month % 12 + 1
    year  = today.year + (1 if today.month == 12 else 0)
    return f"{year}-{month:02d}-01"


def _default_for_label(label: str) -> str:
    """
    Map a question label / question text to a sensible answer.
    Long-form question phrases are checked first (they are the most specific).
    """
    l = label.lower()

    # ── Long-form textarea questions (match on question content) ──────── #
    if ("authorization" in l or "work authorization" in l) and ("canada" in l or "sponsor" in l):
        return _WORK_AUTH_ANSWER
    if "portfolio" in l:
        return _PORTFOLIO_ANSWER
    if ("prototyping" in l or "user testing" in l or "asset generation" in l or "ux workflow" in l) \
            and ("ai" in l or "artificial intelligence" in l or "speed" in l):
        return _AI_UX_ANSWER

    # ── Short / structured field defaults ─────────────────────────────── #
    if l.strip() == "job title"                               : return "Software Engineer"
    if l.strip() in ("company", "company name")               : return "QuickQr"
    if "linkedin"                                          in l: return "n/a"
    if "date available"                                    in l: return _next_month_first()
    if "postal"         in l or "zip"                      in l: return "n5v 4e1"
    if "state"          in l or "province"                 in l: return "Ontario"
    if "city"                                              in l: return "London"
    if "address"                                           in l: return "745 Railton"
    if "pay"       in l or "salary"    in l or "wage"        in l: return "80000"
    if "sponsor"   in l or "visa"      in l or "sponsorship" in l: return "No"
    if "website"   in l or "blog"      in l or "portfolio"   in l: return "https://foreandr.github.io/"
    if "referred"  in l or "referral"  in l                      : return "n/a"
    if "education" in l or "highest level" in l or ("level" in l and "degree" in l): return "Bachelor's Degree"
    if "experience" in l or "years of" in l or "how many years" in l             : return "3"
    return DUMMY_TEXT


# Keywords that steer radio/checkbox answers away from "first option"
_PREFER_NO  = {"sponsor", "visa", "sponsorship", "criminal", "convicted", "felony"}
_PREFER_YES = {"authorized", "eligible", "legally", "citizen", "right to work"}


def _pick_radio_to_click(inputs, q_text: str):
    """
    Return the radio/checkbox input to click based on question context.
    Falls back to the first option if no keyword rule matches.
    """
    l = q_text.lower()
    target = None
    for kw in _PREFER_NO:
        if kw in l:
            target = "no"
            break
    if target is None:
        for kw in _PREFER_YES:
            if kw in l:
                target = "yes"
                break
    if target:
        for inp in inputs:
            if inp.get("value", "").lower() == target:
                return inp
    return inputs[0] if inputs else None


def _orphan_question_text(options_container) -> str:
    """
    For radio/checkbox groups NOT wrapped in a <fieldset>, walk up the DOM
    to find the nearest preceding sibling or ancestor text that looks like
    the question label.
    """
    # Walk up at most 4 levels, checking previous siblings at each level
    node = options_container
    for _ in range(4):
        if node is None:
            break
        for sib in node.previous_siblings:
            if not hasattr(sib, "get_text"):
                continue
            t = sib.get_text(strip=True)
            if t:
                return t
        node = node.parent
    return "(unknown question)"


def _log(msg: str) -> None:
    """Print and write to the hyperSel log file."""
    print(msg)
    log.log_function(log_string=msg)


def parse_and_fill_questions(browser, soup) -> None:
    """
    Walk every form element on the current Indeed application page.
    Prints + logs each question and the value filled.
    Uses hyperSel browser methods exclusively (no raw selenium calls).
    """
    _log("\n" + "=" * 60)
    _log("PARSING QUESTIONS ON PAGE")
    _log("=" * 60)

    # ------------------------------------------------------------------ #
    # 0. ORPHAN RADIO / CHECKBOX GROUPS  (not inside a <fieldset>)        #
    #    Indeed yes/no questions use  <label><input radio></label>  divs   #
    #    grouped only by the `name` attribute, with no wrapping fieldset.  #
    # ------------------------------------------------------------------ #
    fieldset_input_ids = {
        inp.get("id", "")
        for fs in soup.find_all("fieldset")
        for inp in fs.find_all("input")
    }
    orphan_groups: dict[str, list] = defaultdict(list)
    for inp in soup.find_all("input", type=lambda t: t in ("radio", "checkbox")):
        if inp.get("id", "") not in fieldset_input_ids:
            orphan_groups[inp.get("name", "")].append(inp)

    _log(f"\n  [orphan radio/checkbox groups found: {len(orphan_groups)}]")
    for name, inputs in orphan_groups.items():
        options_container = inputs[0].parent.parent
        q_text  = _orphan_question_text(options_container)
        to_click = _pick_radio_to_click(inputs, q_text)
        _log(f"\n  QUESTION (orphan radio): {q_text!r}  name={name!r}")
        for inp in inputs:
            inp_id   = inp.get("id", "")
            val      = inp.get("value", "?")
            lbl_text = inp.parent.get_text(strip=True) if inp.parent else val
            _log(f"    [radio]  id={inp_id!r}  value={val!r}  label={lbl_text!r}")

        if to_click is not None:
            chosen_id  = to_click.get("id", "")
            chosen_val = to_click.get("value", "?")
            if chosen_id:
                xpath = f'//*[@id="{chosen_id}"]'
                try:
                    browser.click_element(by_type="xpath", value=xpath, timeout=3)
                    _log(f"    -> ANSWERED: {chosen_val!r}  xpath={xpath!r}")
                except Exception as e:
                    _log(f"    -> could not click {chosen_val!r}: {e}")

    # ------------------------------------------------------------------ #
    # 1. FIELDSETS  →  radio groups & checkbox groups                     #
    # ------------------------------------------------------------------ #
    fieldsets = soup.find_all("fieldset")
    _log(f"\n  [fieldsets found: {len(fieldsets)}]")
    for fieldset in fieldsets:
        legend  = fieldset.find("legend")
        q_text  = legend.get_text(strip=True) if legend else "(no legend)"
        inputs  = fieldset.find_all("input", type=lambda t: t in ("radio", "checkbox"))
        to_click = _pick_radio_to_click(inputs, q_text)
        _log(f"\n  QUESTION (fieldset): {q_text!r}")

        for inp in inputs:
            inp_id   = inp.get("id", "")
            lbl_tag  = fieldset.find("label", attrs={"for": inp_id})
            lbl_text = lbl_tag.get_text(strip=True) if lbl_tag else inp.get("value", "?")
            _log(f"    [{inp.get('type')}]  id={inp_id!r}  label={lbl_text!r}")

        if to_click is not None:
            chosen_id  = to_click.get("id", "")
            chosen_val = to_click.get("value", "?")
            if chosen_id:
                xpath = f'//*[@id="{chosen_id}"]'
                try:
                    browser.click_element(by_type="xpath", value=xpath, timeout=3)
                    _log(f"    -> ANSWERED: {chosen_val!r}  xpath={xpath!r}")
                except Exception as e:
                    _log(f"    -> could not click {chosen_val!r}: {e}")

    # ------------------------------------------------------------------ #
    # 2. TEXT / NUMBER / EMAIL / TEL inputs  (skip radio/checkbox/hidden) #
    # ------------------------------------------------------------------ #
    skip_types = {"radio", "checkbox", "submit", "hidden", "button", "file", "image", "reset"}
    text_inputs = [
        i for i in soup.find_all("input")
        if i.get("type", "text").lower() not in skip_types
    ]
    _log(f"\n  [text-like inputs found: {len(text_inputs)}]")
    for inp in text_inputs:
        inp_id   = inp.get("id", "")
        lbl_tag  = soup.find("label", attrs={"for": inp_id})
        q_text   = lbl_tag.get_text(strip=True) if lbl_tag else inp.get("placeholder", inp.get("name", "?"))
        inp_type = inp.get("type", "text")
        value    = _default_for_label(q_text)
        _log(f"\n  QUESTION (input/{inp_type}): {q_text!r}  id={inp_id!r}")
        if inp_id:
            xpath = f'//*[@id="{inp_id}"]'
            try:
                browser.clear_and_enter_text(by_type="xpath", value=xpath, content_to_enter=value, timeout=3)
                _log(f"    -> ANSWERED: {value!r}  xpath={xpath!r}")
            except Exception as e:
                _log(f"    -> could not fill: {e}")

    # ------------------------------------------------------------------ #
    # 3. SELECT dropdowns                                                 #
    # ------------------------------------------------------------------ #
    selects = soup.find_all("select")
    _log(f"\n  [selects found: {len(selects)}]")
    for sel in selects:
        sel_id  = sel.get("id", "")
        lbl_tag = soup.find("label", attrs={"for": sel_id})
        q_text  = lbl_tag.get_text(strip=True) if lbl_tag else sel.get("name", "?")
        options = sel.find_all("option")
        _log(f"\n  QUESTION (select): {q_text!r}  id={sel_id!r}")
        for opt in options:
            _log(f"    option  value={opt.get('value')!r}  text={opt.get_text(strip=True)!r}")

        if not sel_id:
            continue
        xpath = f'//*[@id="{sel_id}"]'
        try:
            el      = browser.get_elements(by_type="xpath", value=xpath, condition="visible", timeout=3)
            sel_obj = SeleniumSelect(el)
            l = q_text.lower()
            if "country" in l or "nation" in l:
                sel_obj.select_by_visible_text("Canada")
                _log(f"    -> ANSWERED: 'Canada'  xpath={xpath!r}")
            elif "education" in l or "highest level" in l or ("level" in l and "degree" in l):
                sel_obj.select_by_visible_text("Bachelor's Degree")
                _log(f"    -> ANSWERED: \"Bachelor's Degree\"  xpath={xpath!r}")
            elif "experience" in l or "years of" in l or "how many years" in l:
                # Pick the option whose text or value contains "3"
                hit = next(
                    (o for o in options if "3" in o.get_text(strip=True) or "3" in o.get("value", "")),
                    None,
                )
                if hit is None:
                    hit = next((o for o in options if o.get("value", "").strip()), None)
                if hit:
                    sel_obj.select_by_value(hit["value"])
                    _log(f"    -> ANSWERED (experience): {hit.get_text(strip=True)!r}  xpath={xpath!r}")
            else:
                non_empty = [o for o in options if o.get("value", "").strip()]
                if non_empty:
                    sel_obj.select_by_value(non_empty[0]["value"])
                    _log(f"    -> ANSWERED: {non_empty[0]['value']!r}  xpath={xpath!r}")
        except Exception as e:
            _log(f"    -> could not select: {e}")

    # ------------------------------------------------------------------ #
    # 4. TEXTAREAS  (skip hidden / non-interactable ones like recaptcha)  #
    # ------------------------------------------------------------------ #
    textareas = soup.find_all("textarea")
    _log(f"\n  [textareas found: {len(textareas)}]")
    for ta in textareas:
        ta_id   = ta.get("id", "")
        lbl_tag = soup.find("label", attrs={"for": ta_id})
        q_text  = lbl_tag.get_text(strip=True) if lbl_tag else ta.get("name", "?")
        _log(f"\n  QUESTION (textarea): {q_text!r}  id={ta_id!r}")
        if "recaptcha" in ta_id.lower() or "recaptcha" in q_text.lower():
            _log(f"    -> skipping recaptcha textarea")
            continue
        value = _default_for_label(q_text)
        if ta_id:
            xpath = f'//*[@id="{ta_id}"]'
            try:
                browser.clear_and_enter_text(by_type="xpath", value=xpath, content_to_enter=value, timeout=3)
                _log(f"    -> ANSWERED: {value!r}  xpath={xpath!r}")
            except Exception as e:
                _log(f"    -> could not fill textarea: {e}")

    _log("\n" + "=" * 60 + "\n")


def click_submit_button(browser) -> bool:
    """
    Try to click the final Submit button on the preview/review page.
    Returns True if the button was found AND the URL changed after clicking
    (i.e. the application was actually submitted).
    Returns False silently if the button isn't present on this page yet.
    """
    url_before = browser.WEBDRIVER.current_url
    try:
        browser.click_element(by_type="xpath", value=SUBMIT_BTN_XPATH, timeout=3)
        time.sleep(2)
        url_after = browser.WEBDRIVER.current_url
        if url_after != url_before:
            _log(f"  -> SUBMITTED! URL changed to: {url_after}")
            return True
        _log("  -> Submit button clicked but URL did not change — may need another action.")
    except Exception:
        pass  # Not on the preview page yet — silently ignore
    return False


def click_next_button(browser) -> bool:
    """
    Click the Next / Continue button on the application form.
    Retries up to 5 times.  Returns True if the URL changed (page advanced).
    """
    url_before = browser.WEBDRIVER.current_url
    for attempt in range(1, 6):
        try:
            browser.click_element(by_type="xpath", value=NEXT_BTN_XPATH, timeout=3)
            time.sleep(2)
            url_after = browser.WEBDRIVER.current_url
            if url_after != url_before:
                print(f"  -> Next clicked, URL changed to: {url_after}")
                return True
            print(f"  -> URL unchanged after attempt {attempt}, retrying...")
        except Exception as e:
            print(f"  -> Next button not found / not clickable (attempt {attempt}): {e}")
            break
    return False


def main() -> None:
    init_applied_db()
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

        # ── Skip already-applied jobs ──────────────────────────────────── #
        if already_applied(job):
            jk    = _extract_jk(url or "")
            title = job.get("title")
            _log(f"  -> SKIPPING (already applied): jk={jk!r}  title={title!r}")
            continue

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
        
        
        loop_count = 0
        while True:
            loop_count += 1
            time.sleep(2)

            # ── Human-assist gate: if stuck for 20 iterations, pause ───── #
            if loop_count > 20:
                _log(f"\n  !! LOOPED {loop_count} TIMES — likely needs human input.")
                input("  >> Handle anything on screen then press ENTER to continue... ")
                loop_count = 0  # reset so we get another 20 attempts after human helps

            # DIAGNOSE AT EACH NEW PAGE WHAT THEY ARE ASKING FOR
            soup = browser.return_current_soup()
            question_xpath_section ='''/html/body/div[2]/div/div/div[1]/div/div/div[2]/div[2]/div/div/div/main/div[1]/div'''
            current_url = browser.WEBDRIVER.current_url
            print("CURRENT URL", current_url)

            # ── Check for successful submission confirmation ───────────── #
            if "your application has been submitted" in str(soup).lower():
                _log("  -> 'Your application has been submitted!' detected — moving to next job.")
                record_application(job)
                break

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

            # Parse + fill every input field visible on this page
            parse_and_fill_questions(browser, soup)

            # Try the final Submit button first (only present on the preview page)
            if click_submit_button(browser):
                _log("  -> Application submitted — moving to next job.")
                record_application(job)
                break

            # Not on preview page yet — click Next to advance
            click_next_button(browser)



if __name__ == "__main__":
    main()
