import os
import time
import shutil
import traceback

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

BASE_DOWNLOAD_DIR = "/Users/clairexu/Desktop/GitHub/cartoScrape/Carto-Datasets"
TEMP_DOWNLOAD_DIR = os.path.expanduser("/Users/clairexu/Desktop/GitHub/cartoScrape/Data")
CARTO_URL = "https://ampitup.carto.com"
EMAIL = "antievictionmap@riseup.net"
PASSWORD = "Ampitup2013!"  # Replace with actual password
CHROME_DRIVER_PATH = "./Driver/chromedriver"
FAILED_DOWNLOADS_FILE = "failed_downloads.txt"

# Ensure download directory exists
os.makedirs(BASE_DOWNLOAD_DIR, exist_ok=True)

def log_failed_download(page_number, dataset_name):
    """Log failed downloads to a file."""
    with open(FAILED_DOWNLOADS_FILE, "a") as f:
        f.write(f"Page {page_number}, Dataset: {dataset_name}\n")

def setup_driver():
    chrome_options = Options()
    prefs = {"download.default_directory": TEMP_DOWNLOAD_DIR}
    chrome_options.add_experimental_option("prefs", prefs)

    service = Service(executable_path=CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def move_downloaded_files(dataset_folder):
    """Move the most recently downloaded file to the dataset's folder."""
    time.sleep(10)
    files = [f for f in os.listdir(TEMP_DOWNLOAD_DIR) if not f.startswith('.')]

    if not files:
        print("No downloaded files found.")
        return

    latest_file = max(files, key=lambda f: os.path.getctime(os.path.join(TEMP_DOWNLOAD_DIR, f)))
    source_path = os.path.join(TEMP_DOWNLOAD_DIR, latest_file)
    destination_path = os.path.join(dataset_folder, latest_file)

    try:
        shutil.move(source_path, destination_path)
        print(f"Moved {latest_file} to {dataset_folder}")
    except Exception as e:
        print(f"Error moving file: {e}")

def login(driver):
    """Log into Carto"""
    driver.get(CARTO_URL)

    login_button = driver.find_element(By.CLASS_NAME, 'Header-settingsItem.js-login')
    login_button.click()

    driver.find_element(By.ID, 'session_email').send_keys(EMAIL)
    driver.find_element(By.ID, 'session_password').send_keys(PASSWORD)

    driver.find_element(By.CLASS_NAME, 'button.button--arrow.is-cartoRed.u-width--100').click()


def navigate_to_datasets(driver):
    """Navigate to Data Dashboard"""
    data_link = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'a.navbar-elementItem[href="/dashboard/datasets/"]'))
    )
    data_link.click()


def get_dataset_links(driver):
    """Retrieve all dataset links in a page"""
    dataset_elements = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.dataset-row.dataset-row--can-hover'))
    )
    return [elem.get_attribute('href') for elem in dataset_elements]

def download_dataset(driver, dataset_link, page_number):
    """Download a dataset in available formats (GeoJSON, SHP, CSV)."""
    driver.get(dataset_link)

    try:
        # Extract dataset name
        dataset_name = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'h2.CDB-Text.CDB-Size-huge.js-title'))
        ).text

        dataset_folder = os.path.join(BASE_DOWNLOAD_DIR, dataset_name)
        os.makedirs(dataset_folder, exist_ok=True)

        # Click export button
        locate_export_button(driver).click()

        downloaded_geojson = False
        downloaded_shp = False

        if try_download_format(driver, 'geojson', page_number, dataset_name):
            move_downloaded_files(dataset_folder)
            print(f"Downloaded GeoJSON for {dataset_name}")
            time.sleep(5)  # Allow DOM to stabilize
            locate_export_button(driver).click()  # Click export again for downloading SHP
            downloaded_geojson = True

        if try_download_format(driver, 'shp', page_number, dataset_name):
            move_downloaded_files(dataset_folder)
            print(f"Downloaded SHP for {dataset_name}")
            downloaded_shp = True

        if not downloaded_geojson and not downloaded_shp:
            move_downloaded_files(dataset_folder)
            try_download_format(driver, 'csv', page_number, dataset_name)
            print(f"Downloaded CSV for {dataset_name}")

        print(f"Download complete for {dataset_name}")

        # Return to dashboard
        back_to_dashboard(driver)

    except Exception as e:
        print(f"Error downloading dataset: {e}")
        log_failed_download(page_number, dataset_name = "Unkown")

def locate_export_button(driver):
    """Ensure we always get a fresh export button."""
    return WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.CLASS_NAME, 'js-export'))
    )

def get_export_formats(driver):
    """Get the available export formats for a dataset"""
    export_options = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'ul.js-formats input.js-format'))
    )
    return {opt.get_attribute("data-format").lower(): opt for opt in export_options if opt.get_attribute("data-format")}

def try_download_format(driver, format_type, page_number, dataset_name):
    """Attempt to download a dataset in a specific format, re-locating elements each time."""
    try:
        export_formats = get_export_formats(driver)  # Re-locate options
        if format_type in export_formats and 'disabled' not in export_formats[format_type].get_attribute('class'):
            export_formats[format_type].click()
            download_button = WebDriverWait(driver, 180).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.CDB-Button.js-confirm'))
            )
            # download_button.click()
            driver.execute_script("arguments[0].click();", download_button)
            time.sleep(15)  # Allow time for download
            return True
    except Exception as e:
        print(f"Error downloading {format_type}: {e}")
        log_failed_download(page_number, dataset_name)
        traceback.print_exc()
    return False


def back_to_dashboard(driver):
    """Use browser's back button to return to dataset list"""
    try:
        driver.back()
        time.sleep(15)
        print("Returned to the Data Dashboard")
    except Exception as e:
        print(f"Error returning to the Data Dashboard: {e}")

def navigate_to_next_page(driver):
    """Navigate to the next page by selecting the page following the current one"""
    try:
        # Locate the current page
        current_page = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li.Pagination-listItem.is-current"))
        )

        # Find the next page element
        next_page = current_page.find_element(By.XPATH, "following-sibling::li")

        if next_page:
            next_page.click()
            time.sleep(15)
            print("Navigated to the next page")
            return True
        else:
            print("No next page available")
            return False

    except Exception as e:
        print(f"Error navigating to next page: {e}")
        return False

def main():
    driver = setup_driver()
    total_start_time = time.time()

    try:
        login(driver)
        navigate_to_datasets(driver)

        page_number = 1

        while True:
            page_start_time = time.time()
            print(f"Processing page {page_number}...")

            dataset_links = get_dataset_links(driver)

            if not dataset_links:
                print("No datasets found on this page.")
                break

            for idx, dataset_link in enumerate(dataset_links, start=1):
                print(f"Processing dataset {idx} on page {page_number}...")
                download_dataset(driver, dataset_link, page_number)

            page_end_time = time.time()
            print(f"Time taken for page {page_number}: {page_end_time - page_start_time:.2f} seconds")

            if not navigate_to_next_page(driver):
                break  # Exit loop if no next page exists

            page_number += 1

        print("All datasets downloaded successfully.")
        total_end_time = time.time()
        print(f"Total time taken to download all datasets: {total_end_time - total_start_time:.2f} seconds")

    except Exception as e:
        print(f"Error encountered: {e}")

    finally:
        driver.quit()
        print("Browser closed.")

if __name__ == "__main__":
    main()