import os
import requests
from bs4 import BeautifulSoup
import logging
import re
from playwright.sync_api import sync_playwright

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def create_directory(domain):
    """Creates a directory to store extracted data (text + screenshot)."""
    folder_name = f"data/{domain.replace('.', '_')}"
    os.makedirs(folder_name, exist_ok=True)
    return folder_name

def scrape_website(domain):
    """Scrapes text and captures a screenshot for each website."""
    folder = create_directory(domain)
    possible_urls = [f"https://{domain}"]

    for url in possible_urls:
        try:
            logging.info(f"🔍 Fetching: {url}")
            response = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()

            response.encoding = response.apparent_encoding  
            soup = BeautifulSoup(response.text, "html.parser")

            main_content = extract_main_content(soup)
            clean_text = clean_scraped_text(main_content)

            if not clean_text.strip():
                logging.warning(f"⚠️ The page {url} may require JavaScript rendering!")
                clean_text = scrape_with_playwright(domain, folder)

            save_text_content(folder, clean_text, domain)
            capture_screenshot(domain, folder)

            return clean_text

        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Error fetching {url}: {e}")

    return "❌ Unable to fetch website content."

def scrape_with_playwright(domain, folder):
    """Uses Playwright to render JavaScript-based pages and extract text."""
    logging.info(f"🚀 Using Playwright for {domain}")
    url = f"https://{domain}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(url, timeout=30000)
            page.wait_for_timeout(3000)  # Allow JS execution
            
            elements = page.query_selector_all("p, div, article, span")
            text = "\n".join(el.inner_text() for el in elements if el.inner_text().strip())

            browser.close()

            if text.strip():
                clean_text = clean_scraped_text(text)
                save_text_content(folder, clean_text, domain)
                return clean_text
            return "⚠️ No readable content found after JavaScript execution."

        except Exception as e:
            logging.error(f"❌ Playwright error: {e}")
            browser.close()
            return "❌ Failed to render JavaScript content."

def capture_screenshot(domain, folder):
    """Captures a screenshot of the website."""
    logging.info(f"📸 Capturing screenshot for {domain}")
    url = f"https://{domain}"
    screenshot_path = os.path.join(folder, f"{domain}.png")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(url, timeout=30000)
            page.wait_for_timeout(5000)
            
            page.screenshot(path=screenshot_path, full_page=True)
            logging.info(f"✅ Screenshot saved at {screenshot_path}")

        except Exception as e:
            logging.error(f"❌ Screenshot error: {e}")

        finally:
            browser.close()

def extract_main_content(soup):
    """Extracts the most relevant text section."""
    unwanted_classes = ["nav", "header", "footer", "menu", "sidebar", "advertisement", "ad", "popup", "login"]

    for tag in soup.find_all(["nav", "header", "footer", "aside", "form", "script", "style"]):
        tag.decompose()

    for div in soup.find_all("div", class_=True):
        if any(keyword in div["class"] for keyword in unwanted_classes):
            div.decompose()

    paragraphs = soup.find_all("p")
    text_blocks = [" ".join(p.get_text() for p in paragraphs)]

    return max(text_blocks, key=len, default="❌ No useful content found.")

def clean_scraped_text(text):
    """Cleans extracted text."""
    text = text.encode("utf-8", "ignore").decode("utf-8")
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def save_text_content(folder, text, domain):
    """Saves the extracted text to a file."""
    text_file_path = os.path.join(folder, f"{domain}.txt")
    try:
        with open(text_file_path, "w", encoding="utf-8") as f:
            f.write(text)
        logging.info(f"✅ Scraped text saved at {text_file_path}")
    except Exception as e:
        logging.error(f"❌ Error saving text: {e}")

def run_scraper(domains):
    """Runs the scraper for a list of domains."""
    results = {}
    for domain in domains:
        results[domain] = scrape_website(domain)
    return results

if __name__ == "__main__":
    test_domains = ["youtube.com", "instagram.com", "linkedin.com", "tiktok.com"]
    results = run_scraper(test_domains)
