import re
import threading
import traceback

from DTO.FileActualPermissionInfo import FileActualPermissionInfo
from DTO.FileDetail import FileDetail
from DTO.FileMovingInfo import FileMovingInfo
from Processes.PermissionGet.ActualPermissionResearcher import ActualPermissionResearcher
from Processes.basic.BasicCheckLauncher import BasicCheckLauncher
from Processes.basic.BasicTsvInfoChecker import BasicTsvInfoChecker, gid_get
from Common import LogHelper

GOOGLE_PARENT_FOLDER_TRASHED_ERR = "移動先フォルダはゴミ箱にある。"
GOOGLE_FOLDER_SHORTCUT_ERR = "対象フォルダはショートカットなので、移動できません。"
GOOGLE_PARENT_FOLDER_SHORTCUT_ERR = "ショートカットは移動先フォルダとして使用できません。"
GOOGLE_PARENT_FOLDER_TYPE_ERR = "ファイルは移動先フォルダとして使用できません。"
GOOGLE_PARENT_FOLDER_PERMISSION_ERR = "移動先フォルダの編集権限がありません。"

# CHECK RESULT
FOLDER_NEED_MOVE_COUNT = "   フォルダ移動必要件数: %d"
FOLDER_CANT_MOVE_COUNT = "   移動できない件数: %d"


class FolderMovingChecker(BasicTsvInfoChecker, BasicCheckLauncher):
    # save tsv check result
    class CheckResult(BasicTsvInfoChecker.BasicCheckResult):
        lock = threading.Lock()
        # the count of folder need to be moved
        folder_moving_count = 0
        # 移動できない件数
        cant_move_file_count = 0

    def __init__(self, tsv_path, google_drive, login_user, setting_sqlite, thread_pool, mode, max_threads_stat):
        BasicTsvInfoChecker.__init__(self, tsv_path, google_drive)
        BasicCheckLauncher.__init__(self, setting_sqlite, thread_pool, mode, max_threads_stat)
        self.login_user = login_user

    def todo_list_get(self):
        """
            check and find file that require change by multi-thread
        :return:
        """
        print(self.GOOGLE_FILE_CHECKING_MSG)
        LogHelper.info(self.GOOGLE_FILE_CHECKING_MSG)

        # research actual permission
        permission_researcher = ActualPermissionResearcher(self.google_drive, self.setting_sqlite, self.thread_pool,
                                                           self.mode)
        permission_researcher.research_actual_permission(self.tsv_path)

        # launch google file permission check
        self.launch_check(self._todo_list_get, self.tsv_path)

        # exception occurs
        if self.get_exception_interrupt():
            self.set_exception_interrupt(False)
            self.CheckResult.check_result = False

        # display check result
        self.todo_list_get_result_display()

    def _todo_list_get(self, file_info_dic):
        """
            get folder moving list
        :param file_info_dic:
        :return:
        """
        file_detail = FileDetail()
        err_info = None
        try:
            file_detail = file_info_dic["file_detail"]
            actual_permission = file_info_dic["actual_permission"]
            parent_actual_permission = file_info_dic["parent_actual_permission"]

            # get tsv file record permission
            expect_permission = self.expect_permission_get(file_detail)
            # tsv content format check
            format_chk_result = self.format_chk(file_detail, expect_permission)
            if format_chk_result:
                err_info = format_chk_result
            elif "□" == file_detail.setting_result \
                    and expect_permission.owner == self.login_user["user"]["emailAddress"]:
                err_info = self.moving_todo_list_get(file_detail, actual_permission, parent_actual_permission)
        except Exception as e:
            LogHelper.debug(traceback.format_exc())
            err_info = re.sub(self.TAB_LINEFEED_REPLACE_REGEX, "", e.__str__())

        # record result
        self.check_result_record(err_info, file_detail)

        # save check result
        self.setting_sqlite.save_check_result(file_detail)

    def moving_todo_list_get(self, file_detail, actual_permission, parent_actual_permission):
        """
            add google file to folder moving list
        :param file_detail:
        :param actual_permission:
        :param parent_actual_permission:
        :return:
        """
        # google file information
        uri = file_detail.uri
        gid = file_detail.file_id

        # not google file permission info in db, get file permission by google drive service
        if actual_permission is None:
            google_file_metadata = self.google_file_metadata_get(uri, gid)
            actual_permission = FileActualPermissionInfo()
            actual_permission.set_values(google_file_metadata)
            if actual_permission.mime_type.__contains__("folder"):
                self.setting_sqlite.save_check_result(actual_permission)

        parent_uri = file_detail.parent_uri
        parent_gid = gid_get(parent_uri)
        if parent_actual_permission is None:
            google_parent_folder_metadata = self.google_file_metadata_get(parent_uri, parent_gid, True)
            parent_actual_permission = FileActualPermissionInfo()
            parent_actual_permission.set_values(google_parent_folder_metadata)
            self.setting_sqlite.save_check_result(parent_actual_permission)

        # reader could not access permissions
        if actual_permission.permission_info is None:
            err_info = self.NO_ACCESS_PERMISSION_ERR
        else:
            # get folder moving list
            err_info = self.google_info_chk(actual_permission, parent_actual_permission)
            if err_info is None:
                # permission check
                if parent_actual_permission.permission_info is None:
                    err_info = GOOGLE_PARENT_FOLDER_PERMISSION_ERR

                    # count the number of items that file could not move
                    with self.CheckResult.lock:
                        self.CheckResult.cant_move_file_count += 1
                else:
                    file_moving_info = FileMovingInfo()
                    file_moving_info.line_num = file_detail.line_num
                    file_moving_info.file_id = gid
                    file_moving_info.parent_id = parent_gid

                    # file moving info will be save by setting_sqlite
                    self.setting_sqlite.save_check_result(file_moving_info)

                    # count the number of items that file require move
                    with self.CheckResult.lock:
                        self.CheckResult.folder_moving_count += 1

                    file_detail.check_result = "○"

        return err_info

    def google_info_chk(self, actual_permission, parent_actual_permission):
        """
            check target folder and destination folder info
        :param actual_permission:
        :param parent_actual_permission:
        :return:
        """
        err_info = None
        # trashed check
        if actual_permission.trashed.upper() == "TRUE":
            err_info = self.GOOGLE_FOLDER_TRASHED_ERR
        elif parent_actual_permission.trashed.upper() == "TRUE":
            err_info = GOOGLE_PARENT_FOLDER_TRASHED_ERR
        # file type check
        elif actual_permission.mime_type.__contains__("shortcut"):
            err_info = GOOGLE_FOLDER_SHORTCUT_ERR
        elif parent_actual_permission.mime_type.__contains__("shortcut"):
            err_info = GOOGLE_PARENT_FOLDER_SHORTCUT_ERR
        elif not parent_actual_permission.mime_type.__contains__("folder"):
            err_info = GOOGLE_PARENT_FOLDER_TYPE_ERR

        return err_info

    def check_result_record(self, err_info, file_detail):
        """
            record result
        :param err_info:
        :param file_detail:
        :return:
        """
        if err_info is not None:
            self.CheckResult.check_result = False
            file_detail.check_result = "×"
            file_detail.err_info = err_info
            # log output
            LogHelper.info(self.FOLDER_MOVING_CHECK_ERR_LOG % (
                file_detail.line_num, re.sub(self.SERIES_REPLACE_REGEX, "", file_detail.file), err_info))
        else:
            file_detail.err_info = "-"

    def todo_list_get_result_display(self):
        """
            check result output
        :return:
        """
        if self.CheckResult.check_result:
            print(self.GOOGLE_FILE_CHECK_OK_MSG)
            LogHelper.info(self.GOOGLE_FILE_CHECK_OK_MSG)
        else:
            print(self.GOOGLE_FILE_CHECK_NG_MSG)
            LogHelper.info(self.GOOGLE_FILE_CHECK_NG_MSG)

        folder_need_move_count = FOLDER_NEED_MOVE_COUNT % self.CheckResult.folder_moving_count
        print(folder_need_move_count)
        LogHelper.info(folder_need_move_count)

        folder_cant_move_count = FOLDER_CANT_MOVE_COUNT % self.CheckResult.cant_move_file_count
        print(folder_cant_move_count)
        LogHelper.info(folder_cant_move_count)

        print()
