import requests
import re
from bs4 import BeautifulSoup
from hyperSel import parser

print("IT'S FINE BUT ONLY ACCOMEDATIONS FOR THE EMAIL, COOKED")

def fetch_soup(url, params=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception:
        return None

def find_emails(soup):
    # Regex to capture standard email formats
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    # Clean text from soup to avoid script tags or hidden metadata
    text = soup.get_text(separator=' ')
    emails = re.findall(email_regex, text)
    return list(set(emails))

def main():
    base_url = "https://www.juju.com/jobs"
    
    print("--- STARTING SCAN (Pages 1-100) ---")
    
    for page in range(1, 101):
        params = {'k': 'data', 'r': '20', 'page': page}
        page_soup = fetch_soup(base_url, params)
        
        if page_soup:
            # Pass soup to your specific parser
            job_data_list = parser.main(page_soup)
            
            for job_entry in job_data_list:
                # Identify the full URL from the parser's list output
                job_url = next((item for item in job_entry if isinstance(item, str) and item.startswith('http')), None)
                
                if job_url:
                    job_page_soup = fetch_soup(job_url)
                    if job_page_soup:
                        emails = find_emails(job_page_soup)
                        
                        if emails:
                            # Formatting for easy clicking in the terminal
                            for email in emails:
                                print(f"EMAIL: {email}")
                                print(f"URL:   {job_url}")
                                print("-" * 40)
        else:
            print(f"Skipping Page {page}: Request Failed")

if __name__ == "__main__":
    main()