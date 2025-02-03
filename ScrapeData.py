import json
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import os

# # find all maps title is-small viewall-link
# all_maps = driver.find_element(By.CLASS_NAME, 'title.is-small.viewall-link')
# all_maps.click()
#
# # switch to list view
# driver.find_element(By.CLASS_NAME, 'mapcard-view-mode').click()
#
# # find all links with this class text is-caption is-txtGrey u-ellipsis cell--map-name__text
# links = driver.find_elements(By.CLASS_NAME, 'row.row--can-hover')

# ----------------------------------------------------------------------------------------------------------------------
# Get the Data

# download path
download_dir = "/Users/clairexu/Desktop/GitHub/cartoScrape"
os.makedirs(download_dir, exist_ok=True)

chrome_options = Options()
prefs = {"download.default_directory": download_dir}
chrome_options.add_experimental_option("prefs", prefs)

# 登录和导航到数据集页面（复用之前的登录代码）
# set up a webdriver for your browser
service = Service(executable_path="./Drivers/chromedriver")
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.get('https://ampitup.carto.com')

# find a class called Header-settingsItem js-login
login = driver.find_element(By.CLASS_NAME, 'Header-settingsItem.js-login')
login.click()

# find the session-email input
email = driver.find_element(By.ID, 'session_email')
email.send_keys('antievictionmap@riseup.net')

password = driver.find_element(By.ID, 'session_password')
password.send_keys('*********')

# login
login_button = driver.find_element(By.CLASS_NAME, 'button.button--arrow.is-cartoRed.u-width--100')
login_button.click()

# 点击进入数据集页面
# Navigate to "Data"
data_link = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, 'a.navbar-elementItem[href="/dashboard/datasets/"]'))
)
data_link.click()

# 抓取所有数据集
all_datasets = []

try:
    while True:
        # 等待数据集列表加载
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'DatasetListItem'))
        )
        datasets = driver.find_elements(By.CLASS_NAME, 'DatasetListItem')

        # 提取当前页数据集
        current_page_datasets = []
        for dataset in datasets:
            name = dataset.find_element(By.CLASS_NAME, 'DatasetListItem-title').text
            url = dataset.find_element(By.TAG_NAME, 'a').get_attribute('href')
            current_page_datasets.append((name, url))

        all_datasets.extend(current_page_datasets)

        # 翻页
        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.Pagination-next:not(.disabled)'))
            )
            next_button.click()
            WebDriverWait(driver, 10).until(EC.staleness_of(datasets[0]))
        except:
            break

finally:
    # 导出每个数据集
    for name, url in all_datasets:
        try:
            driver.get(url)
            export_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, 'ExportButton'))
            )
            export_button.click()

            Select(driver.find_element(By.NAME, 'export_format')).select_by_visible_text('CSV')
            driver.find_element(By.XPATH, '//button[text()="Export"]').click()
            time.sleep(5)  # 根据实际网络速度调整

            # 重命名文件
            latest_file = max(
                [os.path.join(download_dir, f) for f in os.listdir(download_dir)],
                key=os.path.getctime
            )
            os.rename(latest_file, os.path.join(download_dir, f"{name}.csv"))

        except Exception as e:
            print(f"导出数据集 {name} 失败: {e}")

    driver.quit()