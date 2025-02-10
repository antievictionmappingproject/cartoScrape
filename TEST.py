import json
import os
import time
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Constants
# DOWNLOAD_DIR = "/Users/clairexu/Desktop/GitHub/cartoScrape/Carto-Datasets"
BASE_DOWNLOAD_DIR = "/Users/clairexu/Desktop/GitHub/cartoScrape/Carto-Datasets"
TEMP_DOWNLOAD_DIR = os.path.expanduser("/Users/clairexu/Desktop/GitHub/cartoScrape/Data")
CARTO_URL = "https://ampitup.carto.com"
EMAIL = "antievictionmap@riseup.net"
PASSWORD = "*********"  # Replace with actual password
CHROME_DRIVER_PATH = "./Drivers/chromedriver"