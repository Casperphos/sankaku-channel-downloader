import yaml

from selenium import webdriver

from utils.menelku_utils import log


def parse_config():
    log.info("Parsing config")

    with open("sankaku_config.yaml", "r") as f:
        config = yaml.safe_load(f)

    SANKAKU_SECRETS = config["SANKAKU_SECRETS"]

    log.success("Config successfully parsed")
    return SANKAKU_SECRETS


def set_up_driver():
    log.info("Setting up driver")

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--headless")
    options.add_argument("log-level=2")
    driver = webdriver.Chrome(options=options)

    log.success("Driver set up successfully")
    return driver
