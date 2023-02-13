from playwright.sync_api import Playwright, sync_playwright, expect
from playwright._impl._api_types import TimeoutError as PlaywrightTimeoutError
import time
import pandas as pd
import datetime as dt
import re

start = time.time()

places = [{'city':'Dallas','State':'Texas','adults':2,'children':0,'infants':0,'pets':0},{'city':'Chicago','State':'Illinois','adults':2,'children':0,'infants':0,'pets':0}]
rows = []



errors = []

def runsearch(playwright: Playwright,place:dict) -> None:

    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()

    city = place['city']
    State = place['State']

    page = context.new_page()

    page.goto("https://www.airbnb.com/")
    context.set_default_timeout(14000)
    try:
        page.on('popup',page.get_by_role("button", name="Close").click())
    except PlaywrightTimeoutError:
        pass

    def guest_count_click(guesttype: str,count: int):
            for i in range(count):
                page.get_by_test_id(f"stepper-{guesttype}-increase-button").click()
    guesttypes = ['adults','children','infants','pets']
            
    page.get_by_role("button", name="Location Anywhere").click()

    page.get_by_test_id("structured-search-input-field-query").click()

    page.get_by_test_id("structured-search-input-field-query").fill(f'{city}, {State}')

    page.get_by_test_id("structured-search-input-field-guests-button").click()

    for t in guesttypes:
        guest_count_click(t,place[t])

    page.get_by_test_id("structured-search-input-search-button").click()
    page.wait_for_url("https://www.airbnb.com/s/**")

    listings = []
    context.set_default_timeout(30000)
    while True:
        
        for i in range(20):        #           //*[@id="site-content"]/div[2]/div[3]/div/div/div/div/div/div[1]/div/div[2]/div/div/div/div[1]/a
            try:   #                           //*[@id="site-content"]/div[2]/div[2]/div/div/div/div/div/div[1]/div/div[2]/div/div/div/div[1]/a
                listings.append(page.locator(f'//*[@id="site-content"]/div[2]/div[2]/div/div/div/div/div/div[{str(i+1)}]/div/div[2]/div/div/div/div[1]/a').get_attribute('href'))
            except:
                break

        try:
            page.get_by_role('link',name='Next').click()
        except:
            break

    
    for i in range(len(listings)):
        page1 = context.new_page()
        try:
            if i != 0:
                print('\033[1A',end='\x1b[2K')
            else:
                page.close()
            print(f'{city}, {State}:{i+1}/{len(listings)}')
            page1.goto('https://www.airbnb.com'+listings[i][0:listings[i].find('?')])
            page1.wait_for_url('https://www.airbnb.com'+listings[i][0:listings[i].find('?')])

            try:    
                page1.get_by_role("button", name="Clear dates").click()
            except PlaywrightTimeoutError:
                page1.on('popup',page1.get_by_role("button", name="Close").click())
                page1.get_by_role("button", name="Clear dates").click()

            try:
                context.set_default_timeout(20000)
                reviewregex = re.search('\d+(?= review)',page1.get_by_role('button').filter(has_text=' review').nth(0).inner_text())
                if reviewregex != None:
                    reviews = reviewregex.group()
                else:
                    reviews = '0'
                context.set_default_timeout(30000)
            except PlaywrightTimeoutError or AttributeError:
                reviews = '0'
            
            row = {
                'room':listings[i][7:listings[i].find('?')],
                'text':'',
                'days booked(1 month)':0,
                'days booked(2 months)':0,
                'days booked(3 months)':0,
                'days booked(4 months)':0,
                'date':dt.datetime.now(),
                'search position':i+1,
                'city':city,
                'state':State,
                'reviews': int(reviews),
                'adults':place['adults'],
                'children':place['children'],
                'infants':place['infants'],
                'pets':place['pets']
            }
                
            
            alltext = page1.locator('div').all_text_contents()
            for s in alltext:
                row['text'] += ' ' + s
            
            monthword = ['January','February','March','April','May','June','July','August','September','October','November','December']
            weekdayword = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
            now = dt.datetime.now()
            
            page1.wait_for_selector('td',state='attached')
            while True:
                try:
                    page1.get_by_role("button", name="Move backward to switch to the previous month.").click()
                except:
                    break
            context.set_default_timeout(4000)
            for j in range(120):
                daypoint = now + dt.timedelta(days=j+1)
                try:
                    if page1.get_by_role('button',name=f'{str(daypoint.day)}, {weekdayword[daypoint.weekday()]}, {monthword[daypoint.month -1]} {str(daypoint.year)}').get_attribute('aria-label').find('Unavailable') > -1:
                        row['days booked(4 months)'] += 1
                        if j < 90:
                            row['days booked(3 months)'] +=1
                        if j < 60:
                            row['days booked(2 months)'] +=1
                        if j < 30:
                            row['days booked(1 month)'] +=1
                    
                        
                except PlaywrightTimeoutError:
                    page1.get_by_role('button', name='Move forward to switch to the next month').click()
                    if page1.get_by_role('button',name=f'{str(daypoint.day)}, {weekdayword[daypoint.weekday()]}, {monthword[daypoint.month -1]} {str(daypoint.year)}').get_attribute('aria-label').find('Unavailable') > -1:
                        row['days booked(4 months)'] += 1
                        if j < 90:
                            row['days booked(3 months)'] +=1
                        if j < 60:
                            row['days booked(2 months)'] +=1
                        if j < 30:
                            row['days booked(1 month)'] +=1
            context.set_default_timeout(30000)            
            rows.append(row)
            page1.close()

        except Exception as e:
            context.set_default_timeout(30000)
            page1.close()
            errors.append(e)

            
            
            

##################################################################

for place in places:
    with sync_playwright() as playwright:
        runsearch(playwright,place)
print('date:',dt.datetime.now().date())
print('rows:',len(rows))
print('errors: ',len(errors))
print(errors)
df = pd.read_csv('airbnb.csv',index_col=[0])
newdf = pd.DataFrame(rows)
df = pd.concat([df,newdf],ignore_index=True)
df.to_csv('airbnb.csv')
print('time: ',(time.time() - start)/60)