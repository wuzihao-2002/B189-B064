import json


class FileActualPermissionInfo(object):
    file_id = None
    mime_type = None
    trashed = None
    writers_can_share = None
    actual_owner = None
    actual_writer = None
    actual_reader = None
    owned_by_me = None
    permission_info = None

    def __init__(self):
        pass

    def set_values_from_db(self, record, mapper):
        self.file_id = self.set_value(record, mapper, "file_id")
        self.mime_type = self.set_value(record, mapper, "mime_type")
        self.trashed = self.set_value(record, mapper, "trashed")
        self.writers_can_share = self.set_value(record, mapper, "writers_can_share")
        self.actual_owner = self.set_value(record, mapper, "actual_owner")
        self.actual_writer = self.set_value(record, mapper, "actual_writer")
        self.actual_reader = self.set_value(record, mapper, "actual_reader")
        self.owned_by_me = self.set_value(record, mapper, "owned_by_me")
        self.permission_info = self.set_value(record, mapper, "permission_info")

    def set_values(self, info_dic):
        self.file_id = self.set_value_by_dic(info_dic, "id")
        self.mime_type = self.set_value_by_dic(info_dic, "mimeType")
        self.trashed = self.set_value_by_dic(info_dic, "trashed")
        self.owned_by_me = self.set_value_by_dic(info_dic, "ownedByMe")
        self.writers_can_share = self.set_value_by_dic(info_dic, "writersCanShare")

        if info_dic.__contains__("permissions"):
            permissions = info_dic["permissions"]
            permission_id_dic = {}
            actual_owner = None
            actual_writer = []
            actual_reader = []

            for permission in permissions:
                if permission["type"] == "user":
                    role = permission["role"]
                    permission_id = permission["id"]
                    email = permission["emailAddress"]
                    permission_id_dic[email] = permission_id
                    if role == "owner":
                        actual_owner = email
                    elif role == "writer":
                        actual_writer.append(email)
                    elif role == "reader":
                        actual_reader.append(email)

            self.actual_owner = actual_owner
            self.actual_writer = ",".join(actual_writer)
            self.actual_reader = ",".join(actual_reader)
            self.permission_info = json.dumps(permission_id_dic)

    def get_values(self):
        values = [self.file_id, self.mime_type, self.trashed, self.writers_can_share,
                  self.actual_owner, self.actual_writer, self.actual_reader,
                  self.owned_by_me, self.permission_info]
        return values

    @staticmethod
    def set_value(record, mapper, field):
        if field not in mapper:
            return None

        return record[mapper[field]]

    @staticmethod
    def set_value_by_dic(info_dic, field):
        if info_dic.__contains__(field) and info_dic[field] is not None:
            return str(info_dic[field])
        else:
            return None
