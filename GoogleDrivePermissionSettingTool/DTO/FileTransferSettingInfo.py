class FileTransferSettingInfo(object):
    line_num = None
    file_id = None
    transfer_owner = None

    def __init__(self):
        pass

    def set_values_from_db(self, record, mapper):
        self.line_num = self.set_value(record, mapper, "line_num")
        self.file_id = self.set_value(record, mapper, "file_id")
        self.transfer_owner = self.set_value(record, mapper, "transfer_owner")

    def get_values(self):
        values = [self.line_num, self.file_id, self.transfer_owner]
        return values

    @staticmethod
    def create_new():
        return FileTransferSettingInfo()

    @staticmethod
    def set_value(record, mapper, field):
        if field not in mapper:
            return None

        return record[mapper[field]]
