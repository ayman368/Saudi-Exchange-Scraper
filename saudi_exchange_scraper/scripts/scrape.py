import json
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configuration
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'historical_data.json')
URL = "https://www.saudiexchange.sa/wps/portal/saudiexchange/newsandreports/reports-publications/historical-reports?locale=en"

def setup_driver():
    """Setup Chrome driver with robust options"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_latest_data():
    """Scrape data using exact selectors from analysis"""
    driver = None
    try:
        print(f"Launching browser to fetch {URL}...")
        driver = setup_driver()
        driver.get(URL)
        
        # Wait for the specific table identified in the screenshot
        print("Waiting for table #perfSummary...")
        wait = WebDriverWait(driver, 45)
        table = wait.until(EC.presence_of_element_located((By.ID, "perfSummary")))
        
        # Ensure rows are loaded
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#perfSummary tbody tr")))
        
        # Small buffer for data population
        time.sleep(3)
        
        data_rows = []
        rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
        
        print(f"Found {len(rows)} rows in table.")
        
        for row in rows:
            try:
                # Cells: Date, Open, High, Low, Close, Volume, Value, Trades
                cells = row.find_elements(By.TAG_NAME, "td")
                
                # Check if it's a valid data row (sometimes empty rows exist)
                if len(cells) < 8:
                    continue
                    
                # cell[0] is Date (dtr-control class in screenshot)
                date_text = cells[0].text.strip()
                
                # Simple validation
                if not date_text or '/' not in date_text:
                    continue

                row_data = {
                    "date": date_text,
                    "open": cells[1].text.strip(),
                    "high": cells[2].text.strip(),
                    "low": cells[3].text.strip(),
                    "close": cells[4].text.strip(),
                    "volume": cells[5].text.strip(),
                    "value": cells[6].text.strip(),
                    "trades": cells[7].text.strip()
                }
                data_rows.append(row_data)
                
            except Exception as e:
                print(f"Skipping a row due to error: {e}")
                continue

        if data_rows:
            print(f"Successfully scraped {len(data_rows)} rows via ID selector.")
            return data_rows
        else:
            print("No data rows extracted despite finding table.")
            return None

    except Exception as e:
        print(f"Error scraping: {e}")
        # Debug screenshot if failed
        if driver:
            try:
                driver.save_screenshot("debug_failed_scrape.png")
                print("Saved debug_failed_scrape.png")
            except:
                pass
        return None
    finally:
        if driver:
            driver.quit()

def update_json(new_data):
    """Update the JSON file with new data"""
    if not new_data:
        return

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

    history = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = []

    existing_dates = set(item['date'] for item in history)
    
    added = 0
    # Process in reverse to maintain chronological insertion order if needed, 
    # but we sort at the end anyway.
    for row in new_data:
        if row['date'] not in existing_dates:
            history.insert(0, row)
            added += 1
            existing_dates.add(row['date'])
    
    # Sort descending by date
    history.sort(key=lambda x: x['date'], reverse=True)

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)
    
    print(f"✓ Added {added} new rows. Total: {len(history)}")
    print(f"✓ Data saved to: {DATA_FILE}")

if __name__ == "__main__":
    print(f"Starting Scraper at {datetime.now()}")
    data = scrape_latest_data()
    if data:
        update_json(data)

