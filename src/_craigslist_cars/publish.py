import os
from dotenv import load_dotenv
from hyperSel import instance, log

load_dotenv()

RAPID_API_EMAIL = os.getenv("RAPID_API_EMAIL")
RAPID_API_PASSW = os.getenv("RAPID_API_PASSW")

print(RAPID_API_EMAIL)
print(RAPID_API_PASSW)

def sign_in_process(browser):
    # CLICK SIGN IN
    pass

def main():
    browser = instance.Browser(
        headless=False,
        zoom_level=100
    )
    browser.init_browser()
    browser.go_to_site("https://rapidapi.com/auth/login")

    browser.clear_and_enter_text(by_type='xpath', value = '''/html/body/div[2]/main/div[1]/section/section/form/div[1]/div/input''', content_to_enter=RAPID_API_EMAIL)
    browser.clear_and_enter_text(by_type='xpath', value = '''/html/body/div[2]/main/div[1]/section/section/form/div[2]/div/div/input''', content_to_enter=RAPID_API_PASSW)
    browser.click_element(by_type='xpath', value = '''/html/body/div[2]/main/div[1]/section/section/button''')

    # cookies 
    
    browser.click_element(by_type='xpath', value = '''/html/body/div[4]/div[2]/div/div/div[2]/div/div/button[2]''')
    input("stop")

if __name__ == "__main__":
    main()