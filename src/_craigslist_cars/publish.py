# maybe create a local little documentation website for each of the kinds of apis

import os
from dotenv import load_dotenv
from hyperSel import instance, log

load_dotenv()

RAPID_API_EMAIL = os.getenv("RAPID_API_EMAIL")
RAPID_API_PASSW = os.getenv("RAPID_API_PASSW")

print(RAPID_API_EMAIL)
print(RAPID_API_PASSW)

def sign_in_process(browser):
    browser.go_to_site("https://rapidapi.com/auth/login")
    print("SIGN IN")
    browser.clear_and_enter_text(by_type='xpath', value = '''/html/body/div[2]/main/div[1]/section/section/form/div[1]/div/input''', content_to_enter=RAPID_API_EMAIL)
    browser.clear_and_enter_text(by_type='xpath', value = '''/html/body/div[2]/main/div[1]/section/section/form/div[2]/div/div/input''', content_to_enter=RAPID_API_PASSW)
    browser.click_element(by_type='xpath', value = '''/html/body/div[2]/main/div[1]/section/section/button''')

    # cookies 
    
    browser.click_element(by_type='xpath', value = '''/html/body/div[4]/div[2]/div/div/div[2]/div/div/button[2]''')
    print("SIGN IN SUCCESSFUL")
    

def uploading_new_process(browser):

    def creation_process():

        # CLICK WORKSPACE

        # CLICK CREATE NEW PROJECT

        # ENTER NAME
        # ENTER DESC
        # SELECT CATEGORY, NOT SURE HOW TO DO..
        # click add api project

        pass

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