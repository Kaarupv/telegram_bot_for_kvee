import requests
import os
import psycopg2
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options



# Telegram bot setup
TELEGRAM_BOT_TOKEN = 'TELEGRAM_BOT_TOKEN'  # Replace with your actual bot token
TELEGRAM_CHAT_ID = 'TELEGRAM_CHAT_ID'  # Replace with your chat ID

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
            VALUES (?, ?, ?, ?)
            ON CONFLICT(link) DO NOTHING
        """, (listing['heading'], listing['price'], listing['area'], listing['link']))
    conn.commit()

# Function to send message to Telegram
def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    response = requests.post(url, data=data)
    if response.status_code == 200:
        print("Message sent successfully")
    else:
        print("Failed to send message")

# Function to scrape new listings
def scrape_listings():
    # Configure Chrome options for headless operation
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN", "/app/.apt/usr/bin/google-chrome")

    # Initialize the WebDriver with headless Chrome
    driver = webdriver.Chrome(
    service=Service(os.environ.get("CHROMEDRIVER_PATH", "/app/.chromedriver/bin/chromedriver")),
    options=chrome_options
    )



    driver.get(
        'your_kv.ee_link')
    html_text = driver.page_source
    soup = BeautifulSoup(html_text, 'lxml')
    driver.quit()

    listings = []
    articles = soup.find_all('article')

    for article in articles:
        h2 = article.find('h2')
        if h2:
            for i_tag in h2.find_all('i'):
                i_tag.decompose()  # Remove the <i> tags

            heading = h2.get_text(strip=True)
            price_div = article.find('div', class_='price')
            price = price_div.get_text(strip=True) if price_div else "No price"
            area_div = article.find('div', class_='area')
            area = area_div.get_text(strip=True) if area_div else "No area"
            link = h2.find('a', href=True)['href']

            listings.append({
                'heading': heading,
                'price': price,
                'area': area,
                'link': f"https://www.kv.ee{link}"
            })

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
        print("New listings found!")
        for listing in new_listings:
            message = f"New Listing:\n{listing['heading']}\nPrice: {listing['price']}\nArea: {listing['area']}\nLink: {listing['link']}"
            send_telegram_message(message)
        save_new_listings(new_listings)
    else:
        print("No new listings found.")


    return new_listings

# Run the function to compare and update the listings
if __name__ == '__main__':
    create_table()
    new_listings = compare_and_update_listings()

    if new_listings:
        for listing in new_listings:
            print(f"New Listing: {listing['heading']} - {listing['price']} - {listing['area']} - {listing['link']}")
    else:
        print("No new listings to show.")

    # Close the cursor and connection when done
    cur.close()
    conn.close()