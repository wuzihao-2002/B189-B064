import json
import re

from datetime import datetime

from Common.TsvItemEnum import TsvItemEnum
from DTO.FileAccessSettingInfo import FileAccessSettingInfo
from DTO.FileExpectPermissionInfo import FileExpectPermissionInfo
from DTO.FileTransferSettingInfo import FileTransferSettingInfo


def gid_get(google_file_uri):
    """
        get id about google file
    :param google_file_uri:
    :return:
    """
    # file
    if google_file_uri.__contains__("/d/"):
        gid = re.findall(r"/d/(.+)|$", google_file_uri)[0]
    # folder
    else:
        gid = re.findall(r"/folders/(.+)|$", google_file_uri)[0]

    if gid.__contains__("/"):
        gid = gid[: gid.index("/")]
    if gid.__contains__("?"):
        gid = gid[: gid.index("?")]

    return gid


class BasicTsvInfoChecker:
    # CHECK ERR
    NETWORK_TIMEOUT_ERR = "タイムアウトが発生しました。"
    GOOGLE_FOLDER_NOT_EXISTS_ERR = "対象フォルダが存在しません。"
    GOOGLE_PARENT_FOLDER_NOT_EXISTS_ERR = "移動先フォルダが存在しません。"
    NO_ACCESS_PERMISSION_ERR = "実行ユーザーは閲覧者なので、アクセス権限情報が取得できません。"
    GOOGLE_FOLDER_TRASHED_ERR = "対象フォルダはゴミ箱にある。"

    # LOG
    PERMISSION_SETTING_CHECK_ERR_LOG = "「%d」行目 「%s」フォルダの権限設定チェックに間違いがあります。エラー情報:%s"
    FOLDER_MOVING_CHECK_ERR_LOG = "「%d」行目 「%s」フォルダの移動チェックに間違いがあります。エラー情報:%s"

    # TSV CONTENT CHECK
    FORMAT_CHECK_EMPTY_ERR = "項目%sは、空白にすることはできません。"
    FORMAT_CHECK_URI_PATTERN_ERR = "項目%sのURIが不正です。"
    FORMAT_CHECK_TYPE_ERR = "項目「種類」の内容は、（D）、（F）、（S）ではありません。"
    FORMAT_CHECK_WRITERS_CAN_SHARE_ERR = "項目「共有設定」の内容は、(TRUE)、(FALSE)ではありません。"
    FORMAT_CHECK_EMAIL_ERR = "指定のアカウント「%s」はメール形式ではありません。"
    FORMAT_CHECK_OWNER_NOT_ONLY_ERR = "複数のアカウントを「Owner」に指定されました。"
    FORMAT_CHECK_EMAIL_REPEAT_ERR = "項目「編集者」と「閲覧者」に同じアカウント「%s」が存在しています。"
    FORMAT_CHECK_LAST_UPDATE_DATE_ERR = "項目「最終更新年月日」の形式が「YYYY/mm/dd」ではありません。"
    FORMAT_CHECK_LAST_UPDATE_TIME_ERR = "項目「最終更新時間」の形式が「HH:MM:SS」ではありません。"
    FORMAT_CHECK_LAST_UPDATER_ERR = "項目「最終更新者」で指定するアカウント「%s」はメール形式ではありません。"

    # TSV CHECK
    GOOGLE_FILE_CHECKING_MSG = "フォルダ権限チェック中..."
    GOOGLE_FILE_CHECK_OK_MSG = "フォルダ権限チェック完了　エラー無し"
    GOOGLE_FILE_CHECK_NG_MSG = "フォルダ権限チェック完了　エラー有り"

    # google file query parameter
    PARAM = "id,mimeType,ownedByMe,trashed,writersCanShare,permissions"
    # regex
    TAB_LINEFEED_REPLACE_REGEX = r"[\t\r\n]"
    SERIES_REPLACE_REGEX = r"[｜─└]"
    URI_REGEX = r"^https://drive\.google\.com/drive/(\S*)folders/(.+)$|^https://(\S*)google\.com/(\S*)d/(.+)$"
    EMAIL_REGEX = r"^\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$"

    class BasicCheckResult:
        # tsv title
        fieldnames = []
        # check result True: check success False: check fail
        check_result = True

    def __init__(self, tsv_path, google_drive):
        self.tsv_path = tsv_path
        self.google_drive = google_drive

    def format_chk(self, file_detail, expect_permission):
        """
            tsv content format check
        :param file_detail:
        :param expect_permission:
        :return:
        """
        format_chk_result = []

        # empty check
        empty_chk_result = self.empty_item_chk(file_detail)
        if empty_chk_result:
            format_chk_result.append(empty_chk_result)

        # update time and updater check
        update_time_chk_result = self.last_update_info_chk(file_detail)
        if update_time_chk_result:
            format_chk_result.extend(update_time_chk_result)

        # uri check
        uri_chk_result = self.uri_pattern_chk(file_detail)
        if uri_chk_result:
            format_chk_result.append(uri_chk_result)

        # type and writersCan Share value check
        fixed_chk_result = self.fixed_value_chk(file_detail)
        if fixed_chk_result:
            format_chk_result.extend(fixed_chk_result)

        # user account check
        account_chk_result = self.account_chk(expect_permission)
        if account_chk_result:
            format_chk_result.append(account_chk_result)

        if format_chk_result:
            return " ".join(format_chk_result)
        return None

    def empty_item_chk(self, file_detail):
        """
            check whether tsv content is empty
        :param file_detail:
        :return:
        """
        empty_items = []
        # ファイル
        self.empty_chk(file_detail.file, TsvItemEnum.FILE.value, empty_items)
        # 種類
        self.empty_chk(file_detail.type, TsvItemEnum.TYPE.value, empty_items)
        # 最終更新年月日
        self.empty_chk(file_detail.last_update_date, TsvItemEnum.LAST_UPDATE_DATE.value, empty_items)
        # 最終更新時間
        self.empty_chk(file_detail.last_update_time, TsvItemEnum.LAST_UPDATE_TIME.value, empty_items)
        # 最終更新者
        self.empty_chk(file_detail.last_updater, TsvItemEnum.LAST_UPDATER.value, empty_items)
        # URI
        self.empty_chk(file_detail.uri, TsvItemEnum.URI.value, empty_items)
        # 親フォルダ
        self.empty_chk(file_detail.parent_folder, TsvItemEnum.PARENT_FOLDER.value, empty_items)
        # 親URI
        self.empty_chk(file_detail.parent_uri, TsvItemEnum.PARENT_URI.value, empty_items)
        # 共有設定
        self.empty_chk(file_detail.writers_can_share, TsvItemEnum.WRITERS_CAN_SHARE.value, empty_items)
        # リンク設定
        self.empty_chk(file_detail.domain, TsvItemEnum.DOMAIN.value, empty_items)
        # Owner
        self.empty_chk(file_detail.owner, TsvItemEnum.OWNER.value, empty_items)

        # empty item is exists
        if len(empty_items) > 0:
            return self.FORMAT_CHECK_EMPTY_ERR % "、".join(empty_items)
        return None

    @staticmethod
    def empty_chk(value, item, empty_items):
        if len(value.strip()) == 0:
            empty_items.append("「%s」" % item)

    def last_update_info_chk(self, file_detail):
        chk_result = []
        # 最終更新年月日
        last_update_date = file_detail.last_update_date.strip()
        if len(last_update_date) and not self.datetime_format_chk(last_update_date, "%Y/%m/%d"):
            chk_result.append(self.FORMAT_CHECK_LAST_UPDATE_DATE_ERR)
        # 最終更新時間
        last_update_time = file_detail.last_update_time.strip()
        if len(last_update_time) and not self.datetime_format_chk(last_update_time, "%H:%M:%S"):
            chk_result.append(self.FORMAT_CHECK_LAST_UPDATE_TIME_ERR)
        # 最終更新者
        last_updater = file_detail.last_updater.strip()
        updater_email = self.email_get(last_updater)
        if len(last_updater) and not re.match(self.EMAIL_REGEX, updater_email):
            chk_result.append(self.FORMAT_CHECK_LAST_UPDATER_ERR % updater_email)

        return chk_result

    @staticmethod
    def datetime_format_chk(str_datetime, pattern):
        try:
            datetime.strptime(str_datetime, pattern)
            return True
        except ValueError:
            return False

    def uri_pattern_chk(self, file_detail):
        """
            check the format of the uri
        :param file_detail:
        :return:
        """
        pattern_err_uris = []

        # uri
        uri = file_detail.uri.strip()
        if len(uri) > 0 and not re.match(self.URI_REGEX, uri):
            pattern_err_uris.append("「%s」" % TsvItemEnum.URI.value)
        # parent uri
        parent_uri = file_detail.parent_uri.strip()
        if len(parent_uri) > 0 and parent_uri != "-" and not re.match(self.URI_REGEX, parent_uri):
            pattern_err_uris.append("「%s」" % TsvItemEnum.PARENT_URI.value)

        if len(pattern_err_uris) > 0:
            return self.FORMAT_CHECK_URI_PATTERN_ERR % "、".join(pattern_err_uris)

        return None

    def fixed_value_chk(self, file_detail):
        """
            type:D/F/S
            writersCanShare:TRUE/FALSE
        :param file_detail:
        :return:
        """
        chk_result = []
        file_type = file_detail.type.strip().upper()
        if len(file_type) and file_type != "D" and file_type != "F" and file_type != "S":
            chk_result.append(self.FORMAT_CHECK_TYPE_ERR)
        writers_can_share = file_detail.writers_can_share.strip().upper()
        if len(writers_can_share) and writers_can_share != "TRUE" and writers_can_share != "FALSE":
            chk_result.append(self.FORMAT_CHECK_WRITERS_CAN_SHARE_ERR)

        return chk_result

    def account_chk(self, except_permission):
        """
            Owner,Editor,Reader account check
        :param except_permission:
        :return:
        """
        account_chk_result = []

        repeat_chk_result = self.account_repeat_check(except_permission)
        if repeat_chk_result:
            account_chk_result.append(repeat_chk_result)

        format_chk_result = self.account_format_check(except_permission)
        if format_chk_result:
            account_chk_result.append(format_chk_result)

        if account_chk_result:
            return ";".join(account_chk_result)
        return None

    def account_repeat_check(self, except_permission):
        """
            check whether email is repeat
        :param except_permission:
        :return:
        """
        repeat_chk_result = []

        # owner repeat check
        owner = except_permission.owner
        if owner is not None and len(re.split(r'[,，]', owner)) > 1:
            repeat_chk_result.append(self.FORMAT_CHECK_OWNER_NOT_ONLY_ERR)

        # writer and reader repeat check
        writers = except_permission.writer
        readers = except_permission.reader
        repeat_emails = set(writers).intersection(readers)
        repeat_emails.discard("")
        if repeat_emails:
            repeat_chk_result.append(self.FORMAT_CHECK_EMAIL_REPEAT_ERR % "」、「".join(repeat_emails))

        if repeat_chk_result:
            return " ".join(repeat_chk_result)
        return None

    def account_format_check(self, except_permission):
        """
            check whether email format is right
        :param except_permission:
        :return:
        """
        format_chk_result = []

        owner = except_permission.owner
        if owner is not None and not re.match(self.EMAIL_REGEX, owner):
            owner_list = re.split(r'[,，]', owner)
            for owner in owner_list:
                if not re.match(self.EMAIL_REGEX, owner):
                    format_chk_result.append(owner)

        writers = except_permission.writer
        for writer in writers:
            if len(writer) == 0:
                continue
            if not re.match(self.EMAIL_REGEX, writer):
                format_chk_result.append(writer)

        readers = except_permission.reader
        for reader in readers:
            if len(reader) == 0:
                continue
            if not re.match(self.EMAIL_REGEX, reader):
                format_chk_result.append(reader)

        if format_chk_result:
            return self.FORMAT_CHECK_EMAIL_ERR % "」、「".join(format_chk_result)
        return None

    def google_file_metadata_get(self, uri, gid=None, parent_folder=False):
        """
            get google file information by gid
        :param uri:
        :param gid:
        :param parent_folder:
        :return:
        """
        try:
            if gid is None:
                gid = gid_get(uri)
            file = self.google_drive.get_file_metadata(gid, self.PARAM)
        except Exception as e:
            ex_message = e.__str__()
            if ex_message.upper().__contains__("FILE NOT FOUND"):
                if parent_folder:
                    raise Exception(self.GOOGLE_PARENT_FOLDER_NOT_EXISTS_ERR)
                else:
                    raise Exception(self.GOOGLE_FOLDER_NOT_EXISTS_ERR)
            elif ex_message.upper().__contains__("TIMEOUT") or ex_message.__contains__("応答しなかったため"):
                raise Exception(self.NETWORK_TIMEOUT_ERR)
            else:
                raise e
        return file

    @staticmethod
    def email_get(email):
        """
            emailAddress(email name) remove email name
        :param email:
        :return:
        """
        if email.__contains__("("):
            email = email[: email.index("(")]

        if not email.__contains__("@"):
            email += "@broadleaf.co.jp"

        return email

    def expect_permission_get(self, file_detail):
        """
           use dictionary to save modify permission info
        :param file_detail:
        :return:
        """
        expect_permission = FileExpectPermissionInfo()

        # setting permissions information
        owners = re.split(r'[,，]', file_detail.owner)
        owner_list = []
        for owner in owners:
            if len(owner.strip()):
                owner_list.append(self.email_get(owner.lower().strip()))

        if len(owner_list):
            expect_permission.owner = ",".join(owner_list)

        expect_permission.writer = []
        writers = re.split(r'[,，]', file_detail.writer)
        for writer in writers:
            if len(writer.strip()):
                expect_permission.writer.append(self.email_get(writer.lower().strip()))

        expect_permission.reader = []
        readers = re.split(r'[,，]', file_detail.reader)
        for reader in readers:
            if len(reader.strip()):
                expect_permission.reader.append(self.email_get(reader.lower().strip()))

        return expect_permission

    def setting_todo_info_get(self, expect_permission, actual_permission):
        """
            use dictionary save the permission need to be changed
        :param expect_permission:
        :param actual_permission:
        :return:
        """
        access_setting_info = FileAccessSettingInfo()

        permission_info_dic = json.loads(actual_permission.permission_info)

        # insert or update permission
        actual_writer = []
        if actual_permission.actual_writer is not None:
            actual_writer = re.split(r'[,，]', actual_permission.actual_writer)

        add_or_upd_writers = self.permission_difference(expect_permission.writer, expect_permission.owner,
                                                        actual_writer, actual_permission.actual_owner)
        if add_or_upd_writers:
            access_setting_info.add_upd_writer = ",".join(self.get_add_upd_permissions(add_or_upd_writers))

        actual_reader = []
        if actual_permission is not None:
            actual_reader = re.split(r'[,，]', actual_permission.actual_reader)

        add_or_upd_readers = self.permission_difference(expect_permission.reader, expect_permission.owner,
                                                        actual_reader, actual_permission.actual_owner)
        if add_or_upd_readers:
            access_setting_info.add_upd_reader = ",".join(self.get_add_upd_permissions(add_or_upd_readers))

        # remove permission
        removers = set(actual_writer).union(actual_reader)
        removers.discard(expect_permission.owner)
        removers.discard(actual_permission.actual_owner)
        removers = removers.difference(expect_permission.reader)
        removers = removers.difference(expect_permission.writer)
        removers.difference(add_or_upd_writers)
        removers.difference(add_or_upd_readers)
        removers.discard("")

        if removers:
            remover_permission_ids = []
            remover_permission_ids.extend(
                permission_info_dic[email] for email in permission_info_dic if email in removers)
            access_setting_info.remover = ",".join(remover_permission_ids)

        if len(add_or_upd_writers) == 0 and len(add_or_upd_readers) == 0 and len(removers) == 0:
            access_setting_info = None

        # check the owner permission need to be changed
        transfer_setting_info = None
        expect_owner = expect_permission.owner
        if expect_owner != actual_permission.actual_owner:
            transfer_setting_info = FileTransferSettingInfo()
            transfer_setting_info.transfer_owner = expect_owner

        return access_setting_info, transfer_setting_info

    # check the access permission need to be changed
    @staticmethod
    def permission_difference(expect_role_permissions, except_owner, actual_access_permission, actual_owner):
        add_or_upd_user = set(expect_role_permissions).difference(actual_access_permission)
        add_or_upd_user.discard(except_owner)
        add_or_upd_user.discard(actual_owner)
        add_or_upd_user.discard("")
        return add_or_upd_user

    # change permissions add to dic
    @staticmethod
    def get_add_upd_permissions(account_list):
        add_upd_permissions = []
        for account in account_list:
            add_upd_permissions.append(account)

        return add_upd_permissions
