from Common.TsvItemEnum import TsvItemEnum


class FileDetail(object):
    line_num = None  # 行番号
    file_id = None  # ファイルID
    file = None  # ファイル
    type = None  # 種類
    last_update_date = None  # 最終更新年月日
    last_update_time = None  # 最終更新時間
    last_updater = None  # 最終更新者
    uri = None  # URI
    parent_folder = None  # 親フォルダ
    parent_uri = None  # 親URI
    writers_can_share = None  # 共有設定
    domain = None  # リンク設定
    owner = None  # Owner
    writer = None  # Editor
    reader = None  # Reader
    check_result = None  # 権限ﾁｪｯｸ結果
    setting_result = None  # 権限設定結果
    err_info = None  # ErrInfo

    def __init__(self):
        pass

    def set_values_from_db(self, record, mapper):
        """
            mapper: [field1 name: record index1, field2 name: record index2...]
        :param record:
        :param mapper:
        :return:
        """
        self.line_num = self.set_value(record, mapper, "line_num")
        self.file_id = self.set_value(record, mapper, "file_id")
        self.file = self.set_value(record, mapper, "file")
        self.type = self.set_value(record, mapper, "type")
        self.last_update_date = self.set_value(record, mapper, "last_update_date")
        self.last_update_time = self.set_value(record, mapper, "last_update_time")
        self.last_updater = self.set_value(record, mapper, "last_updater")
        self.uri = self.set_value(record, mapper, "uri")
        self.parent_folder = self.set_value(record, mapper, "parent_folder")
        self.parent_uri = self.set_value(record, mapper, "parent_uri")
        self.writers_can_share = self.set_value(record, mapper, "writers_can_share")
        self.domain = self.set_value(record, mapper, "domain")
        self.owner = self.set_value(record, mapper, "owner")
        self.writer = self.set_value(record, mapper, "writer")
        self.reader = self.set_value(record, mapper, "reader")
        self.check_result = self.set_value(record, mapper, "check_result")
        self.setting_result = self.set_value(record, mapper, "setting_result")
        self.err_info = self.set_value(record, mapper, "err_info")

    def set_values_from_tsv(self, line_num, file_id, line_dict):
        """
            fill the line content in tsv into FileDetail
        :param line_num:
        :param file_id:
        :param line_dict:
        :return:
        """
        self.line_num = line_num
        self.file_id = file_id
        self.file = line_dict[TsvItemEnum.FILE.value]
        self.type = line_dict[TsvItemEnum.TYPE.value]
        self.last_update_date = line_dict[TsvItemEnum.LAST_UPDATE_DATE.value]
        self.last_update_time = line_dict[TsvItemEnum.LAST_UPDATE_TIME.value]
        self.last_updater = line_dict[TsvItemEnum.LAST_UPDATER.value]
        self.uri = line_dict[TsvItemEnum.URI.value]
        self.parent_folder = line_dict[TsvItemEnum.PARENT_FOLDER.value]
        self.parent_uri = line_dict[TsvItemEnum.PARENT_URI.value]
        self.writers_can_share = line_dict[TsvItemEnum.WRITERS_CAN_SHARE.value]
        self.domain = line_dict[TsvItemEnum.DOMAIN.value]
        self.owner = line_dict[TsvItemEnum.OWNER.value]
        self.writer = line_dict[TsvItemEnum.WRITER.value]
        self.reader = line_dict[TsvItemEnum.READER.value]
        self.check_result = line_dict[TsvItemEnum.CHECK_RESULT.value]
        self.setting_result = line_dict[TsvItemEnum.SETTING_RESULT.value]
        self.err_info = line_dict[TsvItemEnum.ERR_INFO.value]

    def get_values(self):
        values = [self.line_num, self.file_id, self.file, self.type, self.last_update_date, self.last_update_time,
                  self.last_updater, self.uri, self.parent_folder, self.parent_uri, self.writers_can_share, self.domain,
                  self.owner, self.writer, self.reader, self.check_result, self.setting_result, self.err_info]
        return values

    @staticmethod
    def set_value(record, mapper, field):
        if field not in mapper:
            return None

        return record[mapper[field]]
