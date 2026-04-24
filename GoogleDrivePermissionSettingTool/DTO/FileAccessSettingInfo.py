class FileAccessSettingInfo(object):
    line_num = None
    file_id = None
    add_upd_writer = None
    add_upd_reader = None
    remover = None

    def __init__(self):
        pass

    def set_values_from_db(self, record, mapper):
        self.line_num = self.set_value(record, mapper, "line_num")
        self.file_id = self.set_value(record, mapper, "file_id")
        self.add_upd_writer = self.set_value(record, mapper, "add_upd_writer")
        self.add_upd_reader = self.set_value(record, mapper, "add_upd_reader")
        self.remover = self.set_value(record, mapper, "remover")

    def get_values(self):
        values = [self.line_num, self.file_id, self.add_upd_writer, self.add_upd_reader, self.remover]
        return values

    @staticmethod
    def create_new():
        return FileAccessSettingInfo()

    @staticmethod
    def set_value(record, mapper, field):
        if field not in mapper:
            return None

        return record[mapper[field]]
