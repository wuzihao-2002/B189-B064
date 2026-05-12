import re
import threading

from DTO.FileActualPermissionInfo import FileActualPermissionInfo
from Processes.basic.BasicSettingLauncher import BasicSettingLauncher
from Processes.PermissionSet import PermissionSetter
from Processes.SqliteDB import SqlCommand
from Common import LogHelper

GOOGLE_FOLDER_NOT_EXISTS_ERR = "対象フォルダが存在しない"
NETWORK_TIMEOUT_ERR = "タイムアウトが発生しました"
FOLDER_MOVING_EXECUTE_ERR_LOG = "「%d」行目 「%s」フォルダの移動に間違いあり。エラー情報:%s"
TAB_LINEFEED_REPLACE_REGEX = "[\t\r\n]"
SERIES_REPLACE_REGEX = r"[｜─└]"

FOLDER_MOVING_MSG = "フォルダ移動中..."
FOLDER_MOVE_OK_MSG = "フォルダー移動完了　エラー無し"
FOLDER_MOVE_NG_MSG = "フォルダー移動完了　エラー有り"

FOLDER_MOVE_SUCCESS_COUNT = "   成功件数: %d"
FOLDER_MOVE_FAIL_COUNT = "   失敗件数: %d"


class FolderMover(BasicSettingLauncher):
    class ExecuteResult:
        lock = threading.Lock()
        # フォルダ移動成功件数
        move_success_count = 0
        # フォルダ移動失敗件数
        move_fail_count = 0
        # folder move result
        execute_result = True

    def __init__(self, drive_service, checker, setting_sqlite, thread_pool, max_threads_stat):
        super().__init__(setting_sqlite, thread_pool, max_threads_stat)
        self.checker = checker
        self.drive_service = drive_service

    def todo_list_execute(self, output_tsv_path):
        """
            folder moving, result save and display
        :param output_tsv_path:
        :return:
        """
        if self.checker.CheckResult.folder_moving_count:
            # folder moving
            print(FOLDER_MOVING_MSG)

            # launch folder move setting
            self.launch_setting(self.folder_move, SqlCommand.file_moving_tbl)

            # exception occurs
            if self.get_exception_interrupt():
                self.set_exception_interrupt(False)
                self.ExecuteResult.execute_result = False

            # move result display
            self.execute_result_display()

        if self.checker.CheckResult.folder_moving_count:
            # save setting result to tsv
            self.setting_result_to_tsv(output_tsv_path)

    def folder_move(self, handle_methods):
        """
            folder moving
        :param handle_methods:
        :return:
        """
        moving_info = handle_methods["setting_work"]
        file_detail = handle_methods["file_detail"]

        line_num = moving_info.line_num
        err_info = None
        try:
            file_id = moving_info.file_id
            parent_id = moving_info.parent_id

            # get current parents before moving
            current_file_info = self.drive_service.get_file_metadata(file_id, "parents")
            current_parents = ",".join(current_file_info.get("parents", []))

            # move file: addParents/removeParents as query params
            google_file_metadata = self.drive_service.move_file(file_id, parent_id, current_parents)

            # confirm move result: only target parent should remain
            moved_parents = google_file_metadata.get("parents", [])
            if parent_id not in moved_parents or len(moved_parents) != 1:
                raise Exception("フォルダ移動後のparents確認失敗。期待: [%s], 実際: %s" % (parent_id, moved_parents))

            # when permission is changed, reset access permission
            self.permission_reset(file_id, google_file_metadata, file_detail)
        except Exception as e:
            err_info = re.sub(TAB_LINEFEED_REPLACE_REGEX, "", e.__str__())
            if err_info.upper().__contains__("FILE NOT FOUND"):
                err_info = GOOGLE_FOLDER_NOT_EXISTS_ERR
            elif err_info.upper().__contains__("TIMEOUT") or err_info.__contains__("応答しなかったため"):
                err_info = NETWORK_TIMEOUT_ERR

        # move result
        self.execute_result_record(file_detail, err_info, line_num)

        # update set result
        self.setting_sqlite.save_set_result({"file_detail": file_detail, "update_writer": False, "update_reader": False})

    def permission_reset(self, file_id, google_file_metadata, file_detail):
        """
            check whether permission is changed,changed: reset access permission
        :param file_id:
        :param google_file_metadata:
        :param file_detail:
        :return:
        """
        actual_permission = FileActualPermissionInfo()
        actual_permission.set_values(google_file_metadata)
        expect_permission = self.checker.expect_permission_get(file_detail)

        access_setting_info, transfer_setting_info = self.checker.setting_todo_info_get(expect_permission,
                                                                                        actual_permission)
        # after folder move,permission is change,reset reader and writer
        if access_setting_info is not None:
            if access_setting_info.add_upd_reader is not None:
                reader_list = re.split(r'[,，]', access_setting_info.add_upd_reader)
                PermissionSetter.access_permission_add_or_upd(self.drive_service, file_id, reader_list, "reader")

            if access_setting_info.add_upd_writer is not None:
                writer_list = re.split(r'[,，]', access_setting_info.add_upd_writer)
                PermissionSetter.access_permission_add_or_upd(self.drive_service, file_id, writer_list, "writer")

            if access_setting_info.remover is not None:
                remover_list = re.split(r'[,，]', access_setting_info.remover)
                PermissionSetter.access_permission_remove(self.drive_service, file_id, remover_list)

    def execute_result_record(self, file_detail, err_info, line_num):
        """
            folder move result and permission reset result
        :param file_detail:
        :param err_info:
        :param line_num:
        :return:
        """
        if err_info:
            file_detail.err_info = err_info
            file_detail.setting_result = "×"
            # count the number of items that setting fail
            with self.ExecuteResult.lock:
                self.ExecuteResult.move_fail_count += 1

            LogHelper.info(FOLDER_MOVING_EXECUTE_ERR_LOG % (
                line_num + 2, re.sub(SERIES_REPLACE_REGEX, "", file_detail.file),
                err_info))
        else:
            file_detail.setting_result = "○"
            # count the number of items that setting success
            with self.ExecuteResult.lock:
                self.ExecuteResult.move_success_count += 1

    def execute_result_display(self):
        """
            execute result output
        :return:
        """
        if self.ExecuteResult.move_fail_count == 0:
            print(FOLDER_MOVE_OK_MSG)
            LogHelper.info(FOLDER_MOVE_OK_MSG)
        else:
            self.ExecuteResult.execute_result = False
            print(FOLDER_MOVE_NG_MSG)
            LogHelper.info(FOLDER_MOVE_NG_MSG)

        folder_move_success_count = FOLDER_MOVE_SUCCESS_COUNT % self.ExecuteResult.move_success_count
        print(folder_move_success_count)
        LogHelper.info(folder_move_success_count)

        folder_move_fail_count = FOLDER_MOVE_FAIL_COUNT % self.ExecuteResult.move_fail_count
        print(folder_move_fail_count)
        LogHelper.info(folder_move_fail_count)

        print()
