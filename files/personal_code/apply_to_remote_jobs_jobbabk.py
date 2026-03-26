from datetime import datetime
import re
import time

from hyperSel import instance, parser


KEYWORDS = [
    "software",
    "data",
    "devops",
    "engineer",
    "programming",
    "program",
    "remote software",
    "remote developer",
    "remote engineer",
    "remote devops",
]


browser = instance.Browser(zoom_level=100, headless=False)
browser.init_browser()


def extract_job_urls(job_entries):
    urls = []
    for entry in job_entries:
        for text in entry:
            match = re.search(r'/jobsearch/jobposting/\d+\?source=searchresults', text)
            if match:
                urls.append(f"https://www.jobbank.gc.ca{match.group(0)}")
                break
    return urls


def job_search_url(keyword: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] keyword: {keyword}")
    template = "https://www.jobbank.gc.ca/jobsearch/jobsearch?searchstring=@KEYWORD&locationstring="
    url = template.replace("@KEYWORD", keyword)
    browser.go_to_site(url)

    soup = browser.return_current_soup()
    results = parser.main(soup)
    #all_urls = extract_job_urls(results)
    #for i, item in enumerate(all_urls):
    #    print(i, item)

    browser.scroll_to_bottom()
    button_xpath = '//*[@id="moreresultbutton"]'
    try:
        browser.click_element(by_type='xpath', value=button_xpath)
    except:
        pass
    time.sleep(2)
    soup = browser.return_current_soup()
    data = parser.main(soup)
    for j in data:
        print(j)
        print("----")
    print("--")
    time.sleep(2)


def main():
    for keyword in KEYWORDS:
        job_search_url(keyword)


if __name__ == "__main__":
    main()
