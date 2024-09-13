# KV.ee Apartment Scraper

This project is a Python-based web scraper that checks for new apartment listings on [KV.ee](https://www.kv.ee) and sends notifications to a specified Telegram chat. The project is designed to run periodically on Heroku using the Heroku Scheduler. 

## Features

- Scrapes apartment listings from KV.ee based on specified search criteria.
- Compares new listings with previously scraped data to identify new entries.
- Sends notifications about new listings to a Telegram bot.

## Deployment

The project is deployed on [Heroku](https://www.heroku.com/). The Heroku Scheduler runs the scraper every 10 minutes to check for new listings.

## API Keys

To run this project, you'll need to replace two API keys in the `main.py` file:

- **`TELEGRAM_BOT_TOKEN`**: Replace `TELEGRAM_BOT_TOKEN` with your Telegram bot's API token.
- **`TELEGRAM_CHAT_ID`**: Replace `TELEGRAM_CHAT_ID` with the chat ID where you want to receive the notifications.

Additionally, you will need to replace the placeholder in the `driver.get` function with your actual KV.ee search link:
```python
driver.get('your_kv.ee_link')
