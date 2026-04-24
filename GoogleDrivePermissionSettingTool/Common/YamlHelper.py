import os
import yaml

from Common import LogHelper

YAML_FILE_READ_FAILED_ERR = "yamlファイル「%s」の読み取りに失敗しました"


def yaml_read(yaml_path):
    """
        get yaml file information
    :param yaml_path:
    :return:
    """
    try:
        with open(yaml_path, 'r', encoding='utf-8') as reader:
            dic_data = yaml.safe_load(reader.read())
        return dic_data
    except Exception as e:
        LogHelper.error(e)
        raise Exception(YAML_FILE_READ_FAILED_ERR % yaml_path)


def yaml_exists(yaml_path):
    """
        yaml file exists check
    :param yaml_path:
    :return:
    """
    is_exists = False
    if os.path.exists(yaml_path):
        is_exists = True
    return is_exists
