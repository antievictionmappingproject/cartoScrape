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

BASE_DOWNLOAD_DIR = "/Users/clairexu/Desktop/GitHub/cartoScrape/Carto-Maps"
TEMP_DOWNLOAD_DIR = os.path.expanduser("/Users/clairexu/Desktop/GitHub/cartoScrape/Data")
CARTO_URL = "https://ampitup.carto.com"
EMAIL = "antievictionmap@riseup.net"
PASSWORD = "********"  # Replace with actual password
CHROME_DRIVER_PATH = "./Drivers/chromedriver"

# Ensure download directory exists
os.makedirs(BASE_DOWNLOAD_DIR, exist_ok=True)

def setup_driver():
    chrome_options = Options()
    prefs = {"download.default_directory": TEMP_DOWNLOAD_DIR}
    chrome_options.add_experimental_option("prefs", prefs)

    service = Service(executable_path=CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def move_downloaded_files():
    """Move the most recently downloaded file to the Carto-Maps folder."""
    time.sleep(5)
    try:
        files = [f for f in os.listdir(TEMP_DOWNLOAD_DIR) if not f.startswith('.')]
        if not files:
            print("WARNING: No downloaded files found.")
            return

        latest_file = max(files, key=lambda f: os.path.getctime(os.path.join(TEMP_DOWNLOAD_DIR, f)))
        source_path = os.path.join(TEMP_DOWNLOAD_DIR, latest_file)
        destination_path = os.path.join(BASE_DOWNLOAD_DIR, latest_file)

        shutil.move(source_path, destination_path)
        print(f"Moved {latest_file} to {BASE_DOWNLOAD_DIR}")
    except Exception as e:
        print(f"ERROR: Failed to move downloaded file - {e}")

def login(driver):
    """Log into Carto"""
    driver.get(CARTO_URL)

    login_button = driver.find_element(By.CLASS_NAME, 'Header-settingsItem.js-login')
    login_button.click()

    driver.find_element(By.ID, 'session_email').send_keys(EMAIL)
    driver.find_element(By.ID, 'session_password').send_keys(PASSWORD)

    driver.find_element(By.CLASS_NAME, 'button.button--arrow.is-cartoRed.u-width--100').click()


def navigate_to_maps(driver):
    """Navigate to Data Dashboard"""
    data_link = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'a.navbar-elementItem[href="/dashboard/maps/"]'))
    )
    data_link.click()


def get_map_links(driver):
    """Retrieve all dataset links in a page"""
    maps_elements = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.card.map-card.card--can-hover'))
    )
    return [elem.get_attribute('href') for elem in maps_elements]

def download_map(driver, map_link):
    """Download a dataset in available formats (GeoJSON, SHP, CSV)."""
    driver.get(map_link)

    # open toggle menu
    locate_toggle_menu(driver).click()

    # click download map
    locate_download_map(driver).click()

    # confirm download
    confirm_download(driver)

    # move downloaded map
    move_downloaded_files()
    time.sleep(5)

    print(f"Download complete")

    # Return to dashboard
    back_to_dashboard(driver)

def locate_toggle_menu(driver):
    """Ensure we always get a fresh export button."""
    return WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.CLASS_NAME, 'js-toggle-menu'))
    )

def locate_download_map(driver):
    """Ensure we always get a fresh export button."""
    return WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, '//li[@data-val="export-map"]//button'))
    )

def confirm_download(driver):
    try:
        download_button = WebDriverWait(driver, 180).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.CDB-Button.js-confirm'))
        )
        download_button.click()
        time.sleep(15)  # Allow time for download
    except Exception as e:
        print(f"Error when confirming download: {e}")
        traceback.print_exc()

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
        navigate_to_maps(driver)

        page_number = 1

        while True:
            page_start_time = time.time()
            print(f"Processing page {page_number}...")

            dataset_links = get_map_links(driver)

            if not dataset_links:
                print("No maps found on this page.")
                break

            for idx, dataset_link in enumerate(dataset_links, start=1):
                print(f"Processing dataset {idx} on page {page_number}...")
                download_map(driver, dataset_link)

            page_end_time = time.time()
            print(f"Time taken for page {page_number}: {page_end_time - page_start_time:.2f} seconds")

            if not navigate_to_next_page(driver):
                break  # Exit loop if no next page exists

            page_number += 1

        print("All maps downloaded successfully.")
        total_end_time = time.time()
        print(f"Total time taken to download all datasets: {total_end_time - total_start_time:.2f} seconds")

    except Exception as e:
        print(f"Error encountered: {e}")

    finally:
        driver.quit()
        print("Browser closed.")

if __name__ == "__main__":
    main()