import csv
import os

from Common.TsvItemEnum import TsvItemEnum

TSV_WRITE_ERR = "TSVファイル「%s」の書き込みに失敗しました,エラー情報:%s"
fieldnames = list(kv.value for kv in TsvItemEnum)


def tsv_read(file):
    """
        tsv file read
    :param file:
    :return:
    """
    return csv.DictReader(file, delimiter='\t')


def write_to_tsv(file, line):
    """
        Write content to tsv
    :param file:
    :param line:
    :return:
    """
    try:

        csv_writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter='\t',
                                    extrasaction='ignore')
        csv_writer.writerow(line)
    except Exception as e:
        raise Exception(TSV_WRITE_ERR % (file.name, e))


def write_title(tsv_path):
    """
        write title
    :param tsv_path:
    :return:
    """
    try:
        with open(tsv_path, 'w', encoding='UTF-8', newline="", errors='ignore') as file:
            csv_writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter='\t',
                                        extrasaction='ignore')
            csv_writer.writeheader()
    except Exception as e:
        raise Exception(TSV_WRITE_ERR % (tsv_path, e))


def tsv_exists(tsv_path):
    """
        tsv file exists check
    :param tsv_path:
    :return:
    """
    is_exists = True
    if not os.path.exists(tsv_path):
        is_exists = False

    return is_exists


def get_tsv_lines_count(tsv_path):
    lines_count = 0
    with open(tsv_path, 'r', encoding='UTF-8') as file:
        csv_iterator = tsv_read(file)
        for line in csv_iterator:
            lines_count += 1

    return lines_count


def get_first_line_uri(tsv_path):
    with open(tsv_path, 'r', encoding='UTF-8') as file:
        csv_iterator = tsv_read(file)
        for line in csv_iterator:
            return line[TsvItemEnum.URI.value]
