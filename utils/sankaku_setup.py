import yaml
import os

from selenium import webdriver

from utils.menelku_utils import log


def choose_config():
    log.info("Choosing config")

    if os.path.isfile("sankaku_config.yaml"):
        log.success("Config file found")
        return "sankaku_config.yaml"

    if os.path.isfile("sankaku_config.example.yaml"):
        log.warning("No config file found, using example config")
        return "sankaku_config.example.yaml"

    log.error("No valid config file found")
    raise FileNotFoundError("No valid config file found")


def parse_config():
    log.info("Parsing config")

    with open(choose_config(), "r") as f:
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
