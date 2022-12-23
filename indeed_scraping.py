from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from bs4 import BeautifulSoup
from tqdm import tqdm
import pandas as pd
import urllib.parse


def getHtml(urls, next_urls=[], extracted_data=None, cb=lambda **kwargs: kwargs['page'].content() ):
    with sync_playwright() as pw:
        try:
            print("Browser(FireFox) Openning...")
            browser = pw.firefox.launch(
                ignore_default_args=["--mute-audio"], 
                headless=True, timeout=0)

            print("Incocgnito Openning... ")
            context = browser.new_context()

            result = next_urls, extracted_data

            for url in urls:

                try_num = 3
                try_counter = 1
                while try_counter <= try_num:
                    try:
                        
                        print("Page Configurating...")
                        page = context.new_page()
                        page.set_viewport_size({"width": 1920, "height": 1080})
                        page.set_default_timeout(timeout=0)

                        print("Going to the page...")
                        stealth_sync(page)
                        page.goto(url, wait_until='domcontentloaded')
                        page.wait_for_selector("body")

                        result = cb(
                            page = page, 
                            context = context, 
                            browser = browser, 
                            url = url, 
                            urls = urls, 
                            next_urls = result[0], 
                            extracted_data = result[1])
                        break 

                    except Exception as e:
                        print(e)
                        print(url)
                        print(f"Try {try_counter} was failed!")
                        try_counter = try_counter + 1
                                
                    finally:
                        page.close()

        except Exception as e:
            print(e)
            return

        else:
            return result
        
        finally:
            context.close()
            browser.close()


def job_scraping(page_num=1, **kwargs):
    print('job scraping...')
    page = kwargs['page']
    next_urls = kwargs['next_urls']
    extracted_data = kwargs['extracted_data']

    pagination=1
    while pagination <= page_num:
        
        if page.locator('.job_seen_beacon').nth(0).is_visible():
            content = BeautifulSoup(page.content(), 'lxml') 
            for post in tqdm(content.select('.job_seen_beacon')):
                try:
                    data = pd.Series({
                        "job_title":post.select('.jobTitle')[0].get_text().strip(),
                        "company":post.select('.companyName')[0].get_text().strip(),
                        "rating":post.select('.ratingNumber')[0].get_text().strip(),
                        "location":post.select('.companyLocation')[0].get_text().strip(),
                        "date":post.select('.date')[0].get_text().strip(),
                        "job_desc":post.select('.job-snippet')[0].get_text().strip(),
                        "link": domain+post.select('a')[0].get('href').strip()
                    })
                    extracted_data = pd.concat([extracted_data, data.to_frame().T], ignore_index = True)
                except IndexError:
                    continue
    
        if page.locator('a[aria-label="Next Page"]').nth(0).is_visible():
            page.locator('a[aria-label="Next Page"]').click()
            page.wait_for_selector(".jobsearch-SerpMainContent")
            pagination = pagination + 1
        else:
            break

    return next_urls, extracted_data


if __name__ == '__main__':

    domain = 'https://www.indeed.com'
    what = input("What is your job? ")
    where = input("Where is your job? ")
    page_num = 10

    params = {'q': what, 'l': where}
    query = urllib.parse.urlencode(params)
    url = f'{domain}/jobs?{query}'

    _, extracted_data = getHtml([url], extracted_data=pd.DataFrame(), 
    cb=lambda **kwargs: job_scraping(page_num=page_num, **kwargs))

    if not extracted_data.empty:
        extracted_data.to_csv("job_dataset.csv")
        print(extracted_data)
        print('done')
    else:
        print('Data is not exist')