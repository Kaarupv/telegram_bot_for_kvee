import requests
import os
import psycopg2
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
from selenium.common.exceptions import TimeoutException

# Configure logging
logging.basicConfig(level=logging.INFO)

# Telegram bot setup
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')  # Retrieve from env
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')      # Retrieve from env

# Database setup
DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

# Create a table for storing the listings (run this once)
def create_table():
    cur.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id SERIAL PRIMARY KEY,
            heading TEXT,
            price TEXT,
            area TEXT,
            link TEXT UNIQUE
        )
    """)
    conn.commit()

# Function to load previous listings from the database
def load_previous_listings():
    cur.execute("SELECT heading, price, area, link FROM listings")
    return cur.fetchall()

# Function to save new listings to the database
def save_new_listings(new_listings):
    for listing in new_listings:
        cur.execute("""
            INSERT INTO listings (heading, price, area, link) 
            VALUES (%s, %s, %s, %s)
            ON CONFLICT(link) DO NOTHING
        """, (listing['heading'], listing['price'], listing['area'], listing['link']))
    conn.commit()

# Function to send message to Telegram
def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    response = requests.post(url, data=data)
    if response.status_code == 200:
        logging.info("Message sent successfully")
    else:
        logging.error(f"Failed to send message: {response.text}")

# Function to scrape new listings
def scrape_listings():
    # Configure Chrome options for headless operation
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN", "/app/.chrome-for-testing/chrome-linux64/chrome")

    # Initialize the Service object with the Chromedriver path
    service = Service(executable_path=os.environ.get("CHROME_DRIVER_PATH", "/app/.chrome-for-testing/chromedriver-linux64/chromedriver"))

    # Initialize the WebDriver with the Service and options
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Target URL
    target_url = 'https://www.kv.ee/search?deal_type=2&county=1&parish=1061&city%5B0%5D=5701&city%5B1%5D=1003&city%5B2%5D=1004&rooms_min=2&price_min=600&price_max=700&area_total_min=45&f%5B31%5D=1&f%5B84%5D=1'
    logging.info(f"Navigating to {target_url}")
    driver.get(target_url)

    try:
        # Wait until at least one <article> element is present
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article.object-type-apartment"))
        )
    except TimeoutException:
        logging.error("Timed out waiting for page to load")
        driver.quit()
        return []

    html_text = driver.page_source
    soup = BeautifulSoup(html_text, 'lxml')
    driver.quit()

    # Find all article elements with class containing 'object-type-apartment'
    articles = soup.find_all('article', class_=lambda x: x and 'object-type-apartment' in x)
    logging.info(f"Found {len(articles)} <article> elements")

    listings = []

    for article in articles:
        description = article.find('div', class_='description')
        if not description:
            continue

        h2 = description.find('h2')
        if not h2:
            continue

        # Find all <a> tags within <h2>
        a_tags = h2.find_all('a')
        if len(a_tags) < 2:
            continue

        # The second <a> tag contains the address/title
        heading_tag = a_tags[1]
        heading = heading_tag.get_text(strip=True)

        # Extract the href for the link
        link = heading_tag.get('href')
        if not link:
            continue
        full_link = f"https://www.kv.ee{link}"

        # Extract price
        price_div = article.find('div', class_='price')
        price = price_div.get_text(strip=True) if price_div else "No price"

        # Extract area
        area_div = article.find('div', class_='area')
        area = area_div.get_text(strip=True) if area_div else "No area"

        listings.append({
            'heading': heading,
            'price': price,
            'area': area,
            'link': full_link
        })

    logging.info(f"Scraped {len(listings)} listings")
    return listings

# Function to compare and update listings
def compare_and_update_listings():
    previous_listings = load_previous_listings()
    current_listings = scrape_listings()

    # Compare listings
    new_listings = [
        listing for listing in current_listings
        if (listing['heading'], listing['price'], listing['area'], listing['link']) not in previous_listings
    ]

    if new_listings:
        logging.info("New listings found!")
        for listing in new_listings:
            message = f"New Listing:\n{listing['heading']}\nPrice: {listing['price']}\nArea: {listing['area']}\nLink: {listing['link']}"
            send_telegram_message(message)
        save_new_listings(new_listings)
    else:
        logging.info("No new listings found.")

    return new_listings

# Run the function to compare and update the listings
if __name__ == '__main__':
    try:
        create_table()
        new_listings = compare_and_update_listings()

        if new_listings:
            for listing in new_listings:
                logging.info(f"New Listing: {listing['heading']} - {listing['price']} - {listing['area']} - {listing['link']}")
        else:
            logging.info("No new listings to show.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        # Close the cursor and connection when done
        cur.close()
        conn.close()
