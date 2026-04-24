import re
import threading

from Processes.basic.BasicSettingLauncher import BasicSettingLauncher
from Processes.SqliteDB import SqlCommand
from Common import LogHelper

GOOGLE_FOLDER_NOT_EXISTS_ERR = "対象フォルダが存在しません。"
NETWORK_TIMEOUT_ERR = "タイムアウトが発生しました。"
PERMISSION_SETTING_EXECUTE_ERR_LOG = "「%d」行目 「%s」フォルダの移動に間違いがあります。エラー情報:%s"
TAB_LINEFEED_REPLACE_REGEX = "[\t\r\n]"
SERIES_REPLACE_REGEX = r"[｜─└]"

ACCESS_SETTING_MSG = "アクセス権限設定中..."
ACCESS_SET_OK_MSG = "アクセス権限設定完了　エラー無し"
ACCESS_SET_NG_MSG = "アクセス権限設定完了　エラー有り"

TRANSFERRING_MSG = "オーナー譲渡中..."
TRANSFER_OK_MSG = "オーナー譲渡完了　エラー無し"
TRANSFER_NG_MSG = "オーナー譲渡完了　エラー有り"

SUCCESS_COUNT = "   成功件数: %d"
FAIL_COUNT = "   失敗件数: %d"


def access_permission_add_or_upd(drive_service, file_id, account_list, role):
    for account in account_list:
        permission_info = drive_service.create_permission(file_id, {
            "type": "user",
            "emailAddress": account,
            "role": role
        }, {"sendNotificationEmail": False})

        if role != permission_info["role"]:
            drive_service.update_permission(file_id, permission_info["id"], {"role": role})


def access_permission_remove(drive_service, file_id, remover_list):
    # remover = permissionId
    for remover in remover_list:
        try:
            drive_service.remove_permission(file_id, remover)
        except Exception as e:
            err_info = re.sub(TAB_LINEFEED_REPLACE_REGEX, "", e.__str__())
            # the permission has been removed
            if err_info.upper().__contains__("PERMISSION NOT FOUND"):
                pass
            else:
                raise e


class PermissionSetter(BasicSettingLauncher):
    class ExecuteResult:
        lock = threading.Lock()
        # アクセス権限設定成功件数
        access_set_success_count = 0
        # アクセス権限設定失敗件数
        access_set_fail_count = 0
        # オーナー譲渡成功件数
        owner_transfer_success_count = 0
        # オーナー譲渡失敗件数
        owner_transfer_fail_count = 0
        # permission set result
        execute_result = True

    def __init__(self, drive_service, login_user, checker_result, setting_sqlite, thread_pool, max_threads_stat):
        super().__init__(setting_sqlite, thread_pool, max_threads_stat)
        self.drive_service = drive_service
        self.login_user = login_user
        self.checker_result = checker_result

    def todo_list_execute(self, output_tsv_path):
        """
            permission set, result display and save
        :param output_tsv_path:
        :return:
        """

        if self.checker_result.access_setting_count:
            # reader writer permission set
            print(ACCESS_SETTING_MSG)
            LogHelper.info(ACCESS_SETTING_MSG)

            # launch access permission setting
            self.launch_setting(self.access_permission_set, SqlCommand.access_setting_tbl)

            # exception occurs
            if self.get_exception_interrupt():
                self.set_exception_interrupt(False)
                self.ExecuteResult.execute_result = False

            # display access permission set result
            self.access_set_result_display()

        if self.checker_result.transfer_setting_count:
            # owner transfer
            print(TRANSFERRING_MSG)
            LogHelper.info(TRANSFERRING_MSG)

            # launch owner transfer setting
            self.launch_setting(self.owner_transfer_set, SqlCommand.transfer_setting_tbl)

            # exception occurs
            if self.get_exception_interrupt():
                self.set_exception_interrupt(False)
                self.ExecuteResult.execute_result = False

            # display owner transfer result
            self.transfer_result_display()

        if self.checker_result.access_setting_count or self.checker_result.transfer_setting_count:
            # save setting result to tsv
            self.setting_result_to_tsv(output_tsv_path)

    def access_permission_set(self, handle_methods):
        """
            reader writer permission set
        :param handle_methods:
        :return:
        """
        access_permission_info = handle_methods["setting_work"]
        file_detail = handle_methods["file_detail"]

        err_info = None
        line_num = access_permission_info.line_num

        try:
            file_id = access_permission_info.file_id

            if access_permission_info.add_upd_reader is not None:
                reader_list = re.split(r'[,，]', access_permission_info.add_upd_reader)
                access_permission_add_or_upd(self.drive_service, file_id, reader_list, "reader")

            if access_permission_info.add_upd_writer is not None:
                writer_list = re.split(r'[,，]', access_permission_info.add_upd_writer)
                access_permission_add_or_upd(self.drive_service, file_id, writer_list, "writer")

            if access_permission_info.remover is not None:
                remover_list = re.split(r'[,，]', access_permission_info.remover)
                access_permission_remove(self.drive_service, file_id, remover_list)
        except Exception as e:
            err_info = re.sub(TAB_LINEFEED_REPLACE_REGEX, "", e.__str__())
            if err_info.upper().__contains__("FILE NOT FOUND"):
                err_info = GOOGLE_FOLDER_NOT_EXISTS_ERR
            elif err_info.upper().__contains__("TIMEOUT") or err_info.__contains__("応答しなかったため"):
                err_info = NETWORK_TIMEOUT_ERR

        # record set result
        self.execute_result_record(file_detail, err_info, line_num)

        # update set result
        self.setting_sqlite.save_set_result({"file_detail": file_detail, "update_writer": False})

    def owner_transfer_set(self, handle_methods):
        """
            owner transfer
        :param handle_methods:
        :return:
        """
        err_info = None
        site_is_change = False
        update_writer = False

        transfer_info = handle_methods["setting_work"]
        file_detail = handle_methods["file_detail"]

        line_num = transfer_info.line_num

        if file_detail.err_info != "-":
            self.ExecuteResult.owner_transfer_fail_count += 1
            return

        try:
            # owner transfer
            file_id = transfer_info.file_id
            owner = transfer_info.transfer_owner

            permission_info = self.drive_service.create_permission(file_id, {
                "type": "user",
                "emailAddress": owner,
                "role": "writer",
            })
            permission_id = permission_info["id"]

            if not self.login_user["user"]["emailAddress"].__contains__("@broadleaf.co.jp"):
                self.drive_service.update_permission(file_id, permission_id,
                                                     {"role": "writer", "pendingOwner": True})
            else:
                self.drive_service.update_permission(file_id, permission_id, {"role": "owner"},
                                                     {"transferOwnership": True})

            file_info = self.drive_service.get_file_metadata(file_id, "parents")
            if not file_info.__contains__("parents"):
                site_is_change = True

            # if tsv file [Editor] and [Reader] not contains login user, add login user to [Editor]
            login_user_email = re.sub("@broadleaf.co.jp", "", self.login_user["user"]["emailAddress"])
            login_user_name = self.login_user["user"]["displayName"]
            
            def contains_account(account_list, account):
                account = account.lower()
                for item in re.split(r'[,，]', account_list):
                    item = item.strip().lower()
                    if item == account or item.startswith("%s(" % account):
                        return True
                return False
            
            if not contains_account(file_detail.writer, login_user_email) and not contains_account(
                    file_detail.reader, login_user_email):
                update_writer = True
                if len(file_detail.writer) == 0:
                    file_detail.writer = "%s(%s)" % (login_user_email, login_user_name)
                else:
                    file_detail.writer += ",%s(%s)" % (login_user_email, login_user_name)
            
        except Exception as e:
            err_info = re.sub(TAB_LINEFEED_REPLACE_REGEX, "", e.__str__())
            if err_info.upper().__contains__("FILE NOT FOUND"):
                err_info = GOOGLE_FOLDER_NOT_EXISTS_ERR
            elif err_info.upper().__contains__("TIMEOUT") or err_info.__contains__("応答しなかったため"):
                err_info = NETWORK_TIMEOUT_ERR

        # record transfer result
        self.execute_result_record(file_detail, err_info, line_num, True, site_is_change)

        # update set result
        self.setting_sqlite.save_set_result({"file_detail": file_detail, "update_writer": update_writer})

    def execute_result_record(self, file_detail, err_info, line_num, transfer_mode=False, site_is_change=False):
        """
            record access permission set result,owner transfer result
        :param file_detail:
        :param err_info:
        :param line_num:
        :param transfer_mode:
        :param site_is_change:
        :return:
        """
        if err_info:
            file_detail.err_info = err_info
            file_detail.setting_result = "×"

            with self.ExecuteResult.lock:
                # count the number of items that setting fail
                if transfer_mode:
                    self.ExecuteResult.owner_transfer_fail_count += 1
                else:
                    self.ExecuteResult.access_set_fail_count += 1

            LogHelper.info(PERMISSION_SETTING_EXECUTE_ERR_LOG % (
                line_num + 2, re.sub(SERIES_REPLACE_REGEX, "", file_detail.file),
                err_info))
        else:
            file_detail.err_info = "-"
            if transfer_mode and site_is_change:
                file_detail.setting_result = "□"
            else:
                file_detail.setting_result = "○"

            with self.ExecuteResult.lock:
                # count the number of items that setting success
                if transfer_mode:
                    self.ExecuteResult.owner_transfer_success_count += 1
                else:
                    self.ExecuteResult.access_set_success_count += 1

    def access_set_result_display(self):
        """
            access setting result
        :return:
        """
        if self.ExecuteResult.access_set_fail_count == 0:
            print(ACCESS_SET_OK_MSG)
            LogHelper.info(ACCESS_SET_OK_MSG)
        else:
            self.ExecuteResult.execute_result = False
            print(ACCESS_SET_NG_MSG)
            LogHelper.info(ACCESS_SET_NG_MSG)

        access_set_success_count = SUCCESS_COUNT % self.ExecuteResult.access_set_success_count
        print(access_set_success_count)
        LogHelper.info(access_set_success_count)

        access_set_fail_count = FAIL_COUNT % self.ExecuteResult.access_set_fail_count
        print(access_set_fail_count)
        LogHelper.info(access_set_fail_count)

        print()

    def transfer_result_display(self):
        """
            transfer result
        :return:
        """
        if self.ExecuteResult.owner_transfer_fail_count == 0:
            print(TRANSFER_OK_MSG)
            LogHelper.info(TRANSFER_OK_MSG)
        else:
            self.ExecuteResult.execute_result = False
            print(TRANSFER_NG_MSG)
            LogHelper.info(TRANSFER_NG_MSG)

        transfer_success_count = SUCCESS_COUNT % self.ExecuteResult.owner_transfer_success_count
        print(transfer_success_count)
        LogHelper.info(transfer_success_count)

        transfer_fail_count = FAIL_COUNT % self.ExecuteResult.owner_transfer_fail_count
        print(transfer_fail_count)
        LogHelper.info(transfer_fail_count)

        print()
