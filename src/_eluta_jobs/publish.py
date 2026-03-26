"""RapidAPI publishing automation for _eluta_jobs."""
from __future__ import annotations

import os
from dotenv import load_dotenv
from hyperSel import instance, log

load_dotenv()

# ── Crawler metadata ─────────────────────────────────────────────────────────
DISPLAY_NAME     = "Eluta Jobs"
SHORT_DESC       = "Job postings scraped from Eluta."
LONG_DESC        = """Eluta listings scraped from the Eluta results page. Records include job title, company, location, remote/work mode, posting age, and summary text."""
COLLECTION_PATH  = "/v1/collections/_eluta_jobs/search"

# ── Credentials (set in .env) ─────────────────────────────────────────────────
RAPID_API_EMAIL = os.getenv("RAPID_API_EMAIL")
RAPID_API_PASSW = os.getenv("RAPID_API_PASSW")


def sign_in_process(browser) -> None:
    browser.go_to_site("https://rapidapi.com/auth/login")
    browser.clear_and_enter_text(by_type="xpath", value='/html/body/div[2]/main/div[1]/section/section/form/div[1]/div/input', content_to_enter=RAPID_API_EMAIL)
    browser.clear_and_enter_text(by_type="xpath", value='/html/body/div[2]/main/div[1]/section/section/form/div[2]/div/div/input', content_to_enter=RAPID_API_PASSW)
    browser.click_element(by_type="xpath", value='/html/body/div[2]/main/div[1]/section/section/button')
    # accept cookies popup
    browser.click_element(by_type="xpath", value='/html/body/div[4]/div[2]/div/div/div[2]/div/div/button[2]')
    print("SIGN IN SUCCESSFUL")


def uploading_new_process(browser) -> None:
    def creation_process():
        # TODO: click Workspace
        # TODO: click Create New Project
        # TODO: enter DISPLAY_NAME
        # TODO: enter SHORT_DESC
        # TODO: select category = Data
        # TODO: click Add API Project
        pass

    def general_process():
        # TODO: upload logo (logo.png lives next to this file)
        # TODO: add LONG_DESC
        # TODO: add website link
        # TODO: tick 'I confirm I own or have rights'
        # TODO: add base URL  http://<your-server>:5000/
        pass

    def create_rest_endpoint():
        # TODO: click Create REST Endpoint
        # TODO: set name = DISPLAY_NAME
        # TODO: set description (payload desc)
        # TODO: set method = POST
        # TODO: set path = /v1/collections/_eluta_jobs/search
        # TODO: set payload name = body
        # TODO: paste example body from LISTING.md
        # TODO: paste schema JSON from LISTING.md
        # TODO: click Save
        pass

    creation_process()
    general_process()
    create_rest_endpoint()


def main() -> None:
    browser = instance.Browser(headless=False, zoom_level=100)
    browser.init_browser()
    sign_in_process(browser)
    uploading_new_process(browser)
    input("Paused — press Enter to close browser")


if __name__ == "__main__":
    main()
