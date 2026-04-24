import datetime
import logging
import os

logger = None


def logger_init():
    """
        create logging instance
    :return:
    """
    log_path = os.path.join(os.path.abspath("."), "Log")
    os.makedirs(log_path, exist_ok=True)

    global logger
    logger = logging.getLogger()
    fh = logging.FileHandler("Log\\GoogleDriveSettingTool_{}.log".format(datetime.datetime.now().strftime('%Y%m%d')),
                             encoding="utf-8", mode="a")
    formatter = logging.Formatter('%(asctime)s  %(name)s ThreadID(%(thread)s) %(levelname)s: %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.setLevel(logging.DEBUG)
    logger.name = "SettingTool"


def set_level(level):
    if str(level) == "0":
        logger.setLevel(logging.INFO)
    elif str(level) == "1":
        logger.setLevel(logging.DEBUG)


def error(msg):
    logger.error(msg)


def info(msg):
    logger.info(msg)


def debug(msg):
    logger.debug(msg)
