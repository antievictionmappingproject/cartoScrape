import os
import time
import json
import re
from typing import Dict, List, Tuple
from dotenv import load_dotenv
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_DOWNLOAD_DIR = "./Carto-Maps"
TEMP_DOWNLOAD_DIR = "./Data"
FAILED_DOWNLOADS_FILE = "failed_maps.txt"
CSV_OUTPUT = "./map_metadata.csv"
MAX_PAGES_TO_EXTRACT = 1000

os.makedirs(BASE_DOWNLOAD_DIR, exist_ok=True)


def log_failed_download(page_number, map_idx) -> None:
    with open(FAILED_DOWNLOADS_FILE, "a") as f:
        f.write(f"Page {page_number}: {map_idx}th Dataset\n")


def setup_driver() -> webdriver.Chrome:
    chrome_options = Options()
    chrome_options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": TEMP_DOWNLOAD_DIR,
            "download.prompt_for_download": False,
            "profile.default_content_settings.popups": 0,
            "safebrowsing.enabled": True,
        },
    )
    chrome_options.add_argument("--headless=new")
    service = Service("/usr/bin/chromedriver")

    return webdriver.Chrome(service=service, options=chrome_options)


def login(driver: webdriver.Chrome, url: str, username: str, password: str) -> None:
    driver.get(url)
    login_button = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "Header-settingsItem.js-login"))
    )
    login_button.click()
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "session_email"))
    ).send_keys(username)
    driver.find_element(By.ID, "session_password").send_keys(password)
    driver.find_element(
        By.CLASS_NAME, "button.button--arrow.is-cartoRed.u-width--100"
    ).click()


def get_map_links_for_page(driver: webdriver.Chrome, page_url: str) -> List[str]:
    driver.get(page_url)
    time.sleep(8)
    maps = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "a.card.map-card.card--can-hover")
        )
    )
    return [elem.get_attribute("href") for elem in maps]

def extract_json_from_script(page_source: str) -> Tuple[dict, dict]:
    def clean_and_load(match):
        if not match:
            return {}
        raw = match.group(1)
        try:
            # Replace single quotes with double quotes (carefully)
            cleaned = (
                raw.replace("\\'", "'")
                .replace('\\"', '"')
                .encode()
                .decode("unicode_escape")
            )
            return json.loads(cleaned)
        except Exception as e:
            print("Error parsing JSON:", e)
            return {}

    config_match = re.search(
        r"var\s+frontendConfig\s*=\s*JSON\.parse\(\s*'(.*?)'\s*\);",
        page_source,
        re.DOTALL,
    )
    viz_match = re.search(
        r"var\s+visualizationData\s*=\s*JSON\.parse\(\s*'(.*?)'\s*\);",
        page_source,
        re.DOTALL,
    )

    config_json = clean_and_load(config_match)
    viz_json = clean_and_load(viz_match)

    return config_json, viz_json


def flatten_json(prefix, obj) -> Dict:
    flat = {}
    for k, v in obj.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            flat.update(flatten_json(key, v))
        else:
            flat[key] = v
    return flat


def collect_metadata(driver: webdriver.Chrome, map_link: str) -> pd.DataFrame:
    driver.get(map_link)
    time.sleep(5)
    source = driver.page_source
    config, viz = extract_json_from_script(source)

    flat_data = flatten_json("frontendConfig", config)
    flat_data.update(flatten_json("visualizationData", viz))

    return pd.DataFrame({key: str(value) for key, value in flat_data.items()}, index = [0])


def main():
    print(f"Setting up driver")
    driver = setup_driver()
    page_number = 1
    first_write = True

    try:
        load_dotenv()
        print(f"Logging in")
        login(
            driver,
            url=os.getenv("CARTO_URL"),
            username=os.getenv("CARTO_USERNAME"),
            password=os.getenv("CARTO_PASSWORD"),
        )

        while True:
            print(f"Scraping page {page_number}")

            for link in get_map_links_for_page(driver, f"https://ampitup.carto.com/dashboard/maps/?page={page_number}"):
                metadata_df = collect_metadata(driver, link)
                time.sleep(3)

                print(f"Saving metadata to {CSV_OUTPUT}")
                if first_write:
                    metadata_df.to_csv(CSV_OUTPUT, mode='w')
                    first_write = False
                else:
                    metadata_df.to_csv(CSV_OUTPUT, mode='a',header=False)

            page_number += 1

            if page_number > MAX_PAGES_TO_EXTRACT:
                break

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
