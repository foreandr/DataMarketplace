import os
from dotenv import load_dotenv
from hyperSel import instance, log

load_dotenv()

RAPID_API_EMAIL = os.getenv("RAPID_API_EMAIL")
RAPID_API_PASSW = os.getenv("RAPID_API_PASSW")

def sign_in_process(browser):
    # CLICK SIGN IN
    pass

def main():
    print(RAPID_API_EMAIL)
    print(RAPID_API_PASSW)

    browser = instance.Browser(
        headless=False,
        zoom_level=100
    )
    browser.init_browser()
    browser.go_to_site("https://rapidapi.com/")
    input("stop")

if __name__ == "__main__":
    main()