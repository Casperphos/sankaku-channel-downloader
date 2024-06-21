# Author: Menelku
# Last modified: 2024-04-06

import logging
import os
import re
import time

import colorama
from colorama import Fore, Style

colorama.init()


class TimedColoredLogger:
    def __init__(self, log_file=None):
        self.log_file = log_file

        # Temporary fix for some bullshit with Tensorflow
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            f"%(asctime)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        if self.log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def _clean_log_file(self):
        if os.path.exists(self.log_file):
            with open(self.log_file, "r") as file:
                content = file.read()

            clean_content = re.sub(
                r"\x1B\[[0-9;]*[mK]", "", content
            )  # Remove ANSI escape codes

            with open(self.log_file, "w") as file:
                file.write(clean_content)

    def info(self, message):
        self.logger.info(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} {message}")
        if self.log_file:
            self._clean_log_file()

    def warning(self, message):
        self.logger.warning(
            f"{Fore.LIGHTYELLOW_EX}[WARNING]{Style.RESET_ALL} {message}"
        )
        if self.log_file:
            self._clean_log_file()

    def error(self, message):
        self.logger.error(f"{Fore.LIGHTRED_EX}[ERROR]{Style.RESET_ALL} {message}")
        if self.log_file:
            self._clean_log_file()

    def success(self, message):
        self.logger.info(f"{Fore.LIGHTGREEN_EX}[SUCCESS]{Style.RESET_ALL} {message}")
        if self.log_file:
            self._clean_log_file()


def wait(seconds, print_every_x_seconds, logger):
    initial_seconds = float(seconds)

    if (
        not (
            isinstance(seconds, (int, float))
            and isinstance(print_every_x_seconds, (int, float))
            and seconds > 0.001
        )
        or seconds < print_every_x_seconds
    ):
        logger.error(
            f"Invalid input: seconds and print_every_x_seconds should be integers or floats (>0.001 s), and n should be greater than or equal to print_every_n_seconds"
        )
        raise ValueError

    if isinstance(seconds, int):
        seconds = float(seconds)

    if isinstance(print_every_x_seconds, int):
        print_every_x_seconds = float(print_every_x_seconds)

    logger.info(f"Waiting for {seconds} seconds, {seconds} seconds left")

    while seconds >= print_every_x_seconds:
        time.sleep(print_every_x_seconds)
        seconds -= print_every_x_seconds

        if seconds >= 0.001:
            logger.info(
                f"Waiting for {initial_seconds} seconds, {seconds} seconds left"
            )

    if seconds <= 0.001:
        time.sleep(seconds)
        logger.success(f"Waited for {initial_seconds} seconds")


log = TimedColoredLogger()
wait = wait
