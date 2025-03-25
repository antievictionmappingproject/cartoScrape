import os
import time
import json
import csv
import re
import traceback

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

BASE_DOWNLOAD_DIR = "/Users/clairexu/Desktop/GitHub/cartoScrape/Carto-Maps"
TEMP_DOWNLOAD_DIR = "/Users/clairexu/Desktop/GitHub/cartoScrape/Data"
CARTO_URL = "https://ampitup.carto.com"
EMAIL = "antievictionmap@riseup.net"
PASSWORD = "***"
FAILED_DOWNLOADS_FILE = "failed_maps.txt"
CSV_OUTPUT = "map_metadata.csv"

os.makedirs(BASE_DOWNLOAD_DIR, exist_ok=True)

def log_failed_download(page_number, map_idx):
    with open(FAILED_DOWNLOADS_FILE, "a") as f:
        f.write(f"Page {page_number}: {map_idx}th Dataset\n")

def setup_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": TEMP_DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "profile.default_content_settings.popups": 0,
        "safebrowsing.enabled": True
    })
    chrome_options.add_argument("--headless=new")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def login(driver):
    driver.get(CARTO_URL)
    login_button = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.CLASS_NAME, 'Header-settingsItem.js-login'))
    )
    login_button.click()
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, 'session_email'))).send_keys(EMAIL)
    driver.find_element(By.ID, 'session_password').send_keys(PASSWORD)
    driver.find_element(By.CLASS_NAME, 'button.button--arrow.is-cartoRed.u-width--100').click()

def get_map_links(driver):
    time.sleep(8)
    maps = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.card.map-card.card--can-hover'))
    )
    return [elem.get_attribute('href') for elem in maps]

import json
import re

def extract_json_from_script(page_source):
    def clean_and_load(match):
        if not match:
            return {}
        raw = match.group(1)
        try:
            # Replace single quotes with double quotes (carefully)
            cleaned = raw.replace("\\'", "'").replace('\\"', '"').encode().decode('unicode_escape')
            return json.loads(cleaned)
        except Exception as e:
            print("Error parsing JSON:", e)
            return {}

    config_match = re.search(r"var\s+frontendConfig\s*=\s*JSON\.parse\(\s*'(.*?)'\s*\);", page_source, re.DOTALL)
    viz_match = re.search(r"var\s+visualizationData\s*=\s*JSON\.parse\(\s*'(.*?)'\s*\);", page_source, re.DOTALL)

    config_json = clean_and_load(config_match)
    viz_json = clean_and_load(viz_match)

    return config_json, viz_json


def flatten_json(prefix, obj):
    flat = {}
    for k, v in obj.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            flat.update(flatten_json(key, v))
        else:
            flat[key] = v
    return flat

def collect_metadata(driver, map_link, all_keys, data_rows):
    try:
        driver.get(map_link)
        time.sleep(5)
        source = driver.page_source
        config, viz = extract_json_from_script(source)
        flat_data = flatten_json("frontendConfig", config)
        flat_data.update(flatten_json("visualizationData", viz))

        all_keys.update(flat_data.keys())
        data_rows.append(flat_data)
        print(f"Extracted data for: {map_link}")
    except Exception as e:
        print(f"Failed to extract from {map_link}: {e}")
        traceback.print_exc()

def write_csv(data_rows, all_keys):
    with open(CSV_OUTPUT, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
        writer.writeheader()
        for row in data_rows:
            full_row = {key: row.get(key, None) for key in all_keys}
            writer.writerow(full_row)

def main():
    driver = setup_driver()
    all_keys = set()
    data_rows = []
    page_number = 1
    base_url = "https://ampitup.carto.com/dashboard/maps/?page="

    try:
        login(driver)

        while True:
            driver.get(base_url + str(page_number))
            print(f"Scraping page {page_number}")
            map_links = get_map_links(driver)

            if not map_links:
                break

            for idx, link in enumerate(map_links):
                collect_metadata(driver, link, all_keys, data_rows)
                time.sleep(3)

            page_number += 1
            if page_number > 18: break

        write_csv(data_rows, all_keys)
        print(f"Saved metadata to {CSV_OUTPUT}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
