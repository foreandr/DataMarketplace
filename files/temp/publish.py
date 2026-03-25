# maybe create a local little documentation website for each of the kinds of apis

import os
from dotenv import load_dotenv
from hyperSel import instance, log
import time

load_dotenv()

RAPID_API_EMAIL = os.getenv("RAPID_API_EMAIL")
RAPID_API_PASSW = os.getenv("RAPID_API_PASSW")

print(RAPID_API_EMAIL)
print(RAPID_API_PASSW)

def rapid_api_cookie_clicker(browser):
    # cookies 
    try:
        browser.click_element(by_type='xpath', value = '''/html/body/div[4]/div[2]/div/div/div[2]/div/div/button[2]''')
    except Exception as e:
        # print(e)
        pass

def sign_in_process(browser):

    rapid_api_cookie_clicker(browser)

    browser.go_to_site("https://rapidapi.com/auth/login")

    rapid_api_cookie_clicker(browser)

    print("SIGN IN")
    browser.clear_and_enter_text(by_type='xpath', value = '''/html/body/div[2]/main/div[1]/section/section/form/div[1]/div/input''', content_to_enter=RAPID_API_EMAIL)
    time.sleep(0.5)
    browser.clear_and_enter_text(by_type='xpath', value = '''/html/body/div[2]/main/div[1]/section/section/form/div[2]/div/div/input''', content_to_enter=RAPID_API_PASSW)
    time.sleep(2) 

    for i in range(5):
        # /html/body/div[2]/main/div[1]/section/section/button
        try:
            browser.click_element(by_type='xpath', value = '''/html/body/div[2]/main/div[1]/section/section/button''')
            time.sleep(2)
        except Exception as e:
            pass

        if browser.WEBDRIVER.current_url != 'https://rapidapi.com/hub':
            print("IT BROKE DOING IT AGAAUIN")
            sign_in_process(browser)

        rapid_api_cookie_clicker(browser)

        print("SIGN IN SUCCESSFUL")
        break

def uploading_new_process(browser):

    def inject_coord_tracker():
        """Prints mouse coords from browser to Python console every second. Ctrl+C to stop."""
        browser.WEBDRIVER.execute_script("""
            window._mouseX = 0;
            window._mouseY = 0;
            document.addEventListener('mousemove', function(e) {
                window._mouseX = e.clientX;
                window._mouseY = e.clientY;
            });
        """)
        print("Coord tracker live — move mouse in browser, coords print here every second. Ctrl+C to stop.")
        try:
            while True:
                x = browser.WEBDRIVER.execute_script("return window._mouseX;")
                y = browser.WEBDRIVER.execute_script("return window._mouseY;")
                print(f"  x={x}  y={y}")
                time.sleep(1)
        except KeyboardInterrupt:
            print("Tracker stopped.")

    def js_click(x, y):
        """Click at viewport coordinates (x, y) using JS — does NOT move your real mouse."""
        browser.WEBDRIVER.execute_script(f"""
            var el = document.elementFromPoint({x}, {y});
            if (el) {{ el.click(); console.log('Clicked: ' + el.tagName + ' at {x},{y}'); }}
            else {{ console.log('No element found at {x},{y}'); }}
        """)

    def creation_process():
        print("https://rapidapi.com/studio")
        browser.go_to_site("https://rapidapi.com/studio")
        time.sleep(2)
        # inject_coord_tracker()
        while True:
            js_click(903, 6)   # CLICK WORKSPACE
            print("clicking???")
            time.sleep(1)
        # js_click(x, y)  # CLICK CREATE NEW PROJECT
        # js_click(x, y)  # ENTER NAME
        # js_click(x, y)  # ENTER DESC
        # js_click(x, y)  # SELECT CATEGORY = Data
        # js_click(x, y)  # CLICK ADD API PROJECT
        pass
    creation_process()
    input("-------")

    def general_process():
        # UPLOAD LOGO

        # ADD LONG DESCRIPTION

        # ADD WEBSITE LINK TO MY BASE WEBVSITE

        #CLICK I CONFIRM THAT I OWN OR HAVE RIGHTS
        # THEN CLICK BUTTON BENEATH

        # ADD BASE URL
        pass

    def create_rest_endpoint():
        # click  create rest endpoint

        #name ur endpoint
        
        # describe endpoint

        # click post from dropdown

        # ENTER PATH

        # enter payload name

        # put basic payload inside of example

        # click save
        
        pass
    print("GOING THROOUGH PBULISHING PROCESS")




    pass

def main():
    browser = instance.Browser(
        headless=False,
        zoom_level=100
    )
    browser.init_browser()  
    sign_in_process(browser)
    uploading_new_process(browser)

    input("stop")

if __name__ == "__main__":
    main()