import re
import threading
import traceback

from DTO.FileActualPermissionInfo import FileActualPermissionInfo
from DTO.FileDetail import FileDetail
from Processes.PermissionGet.ActualPermissionResearcher import ActualPermissionResearcher
from Processes.basic.BasicCheckLauncher import BasicCheckLauncher
from Processes.basic.BasicTsvInfoChecker import BasicTsvInfoChecker
from Common import LogHelper

# CHECK ERR
GOOGLE_FOLDER_SHORTCUT_ERR = "対象フォルダはショートカットなので、権限設定ができません。"
NO_SETTING_PERMISSION_ERR = "編集者と閲覧者を変更する権限がありません。オーナー「%s」に連絡してください。"
NO_TRANSFER_PERMISSION_ERR = "実行ユーザーはOwnerではないので、オーナー譲渡ができません。オーナー「%s」に連絡してください。"

# CHECK RESULT
ACCESS_NEED_SET_COUNT = "   アクセス権限設定必要件数: %d"
ACCESS_CANT_SET_COUNT = "   アクセス権限設定できない件数: %d"
OWNER_NEED_TRANSFER_COUNT = "   オーナー譲渡必要件数: %d"
OWNER_CANT_TRANSFER_COUNT = "   実行ユーザーはオーナーではないフォルダ件数: %d"


class PermissionSettingChecker(BasicTsvInfoChecker, BasicCheckLauncher):
    # save tsv check result
    class CheckResult(BasicTsvInfoChecker.BasicCheckResult):
        lock = threading.Lock()
        # the count of owner permission need to be changed
        transfer_setting_count = 0
        # the count of access permission need to be changed
        access_setting_count = 0
        # 当ﾕｰｻﾞｰはオーナーではないﾌｫﾙﾀﾞ件数
        cant_transfer_file_count = 0
        # アクセス権限設定できない件数
        cant_set_access_file_count = 0

    def __init__(self, tsv_path, google_drive, setting_sqlite, thread_pool, mode, max_threads_stat):
        BasicTsvInfoChecker.__init__(self, tsv_path, google_drive)
        BasicCheckLauncher.__init__(self, setting_sqlite, thread_pool, mode, max_threads_stat)

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
            get access permission setting list and owner transfer list
        :param file_info_dic:
        :return:
        """
        file_detail = FileDetail()
        try:
            file_detail = file_info_dic["file_detail"]
            actual_permission = file_info_dic["actual_permission"]

            # get tsv file record permission
            expect_permission = self.expect_permission_get(file_detail)
            # check tsv file content
            format_check_result = self.format_chk(file_detail, expect_permission)
            if format_check_result:
                err_info = format_check_result
                log_info = err_info
            else:
                # get google file information
                if actual_permission is None:
                    google_file_metadata = self.google_file_metadata_get(file_detail.uri)
                    actual_permission = FileActualPermissionInfo()
                    actual_permission.set_values(google_file_metadata)

                # reader could not access permissions
                if actual_permission.permission_info is None or len(actual_permission.permission_info) == 0:
                    err_info = self.NO_ACCESS_PERMISSION_ERR
                    log_info = err_info
                else:
                    err_info, log_info = self.setting_todo_list_get(expect_permission, actual_permission,
                                                                    file_detail)
        except Exception as e:
            LogHelper.debug(traceback.format_exc())
            err_info = re.sub(self.TAB_LINEFEED_REPLACE_REGEX, "", e.__str__())
            log_info = err_info

        self.check_result_record(err_info, log_info, file_detail)

        # save check result
        self.setting_sqlite.save_check_result(file_detail)

    def setting_todo_list_get(self, expect_permission, actual_permission, file_detail):
        """
            get the list of access permission and owner permission need to be changed
        :param expect_permission:
        :param actual_permission:
        :param file_detail:
        :return:
        """
        err_info = None
        log_info = None

        # check the permission need to be changed
        access_setting_info, transfer_setting_info = self.setting_todo_info_get(expect_permission, actual_permission)
        if not access_setting_info and not transfer_setting_info:
            return err_info, log_info

        if access_setting_info or transfer_setting_info:
            # trashed check
            if actual_permission.trashed.upper() == "TRUE":
                err_info = self.GOOGLE_FOLDER_TRASHED_ERR
            # type check
            elif actual_permission.mime_type.__contains__("shortcut"):
                err_info = GOOGLE_FOLDER_SHORTCUT_ERR

            # access permission need to be changed
            if err_info is None and access_setting_info:
                if actual_permission.writers_can_share.upper() == "TRUE" \
                        or actual_permission.owned_by_me.upper() == "TRUE":

                    access_setting_info.line_num = file_detail.line_num
                    access_setting_info.file_id = file_detail.file_id

                    # access setting info will be save by setting_sqlite
                    self.setting_sqlite.save_check_result(access_setting_info)

                    # count the number of items that access permission require change
                    with self.CheckResult.lock:
                        self.CheckResult.access_setting_count += 1
                else:
                    err_info = NO_SETTING_PERMISSION_ERR % actual_permission.actual_owner
                    # count the number of items that could not change access setting
                    with self.CheckResult.lock:
                        self.CheckResult.cant_set_access_file_count += 1

            log_info = err_info

            # owner permission need to be changed
            if err_info is None and transfer_setting_info:
                if actual_permission.owned_by_me.upper() == "TRUE":
                    transfer_setting_info.line_num = file_detail.line_num
                    transfer_setting_info.file_id = file_detail.file_id

                    # transfer setting info will be save by setting_sqlite
                    self.setting_sqlite.save_check_result(transfer_setting_info)

                    # count the number of items that owner require change
                    with self.CheckResult.lock:
                        self.CheckResult.transfer_setting_count += 1
                else:
                    err_info = actual_permission.actual_owner
                    log_info = NO_TRANSFER_PERMISSION_ERR % actual_permission.actual_owner

                    # count the number of items that could not transfer owner
                    with self.CheckResult.lock:
                        self.CheckResult.cant_transfer_file_count += 1

            if err_info is None:
                file_detail.check_result = "○"

        return err_info, log_info

    def check_result_record(self, err_info, log_info, file_detail):
        """
            record result
        :param err_info:
        :param log_info:
        :param file_detail:
        :return:
        """
        # err info record and output
        if err_info is not None:
            self.CheckResult.check_result = False
            if log_info != err_info:
                file_detail.check_result = "△"
                file_detail.setting_result = "△"
            else:
                file_detail.check_result = "×"
            file_detail.err_info = err_info
            # log output
            LogHelper.info(self.PERMISSION_SETTING_CHECK_ERR_LOG % (
                file_detail.line_num, re.sub(self.SERIES_REPLACE_REGEX, "", file_detail.file),
                log_info))
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

        access_need_set_count = ACCESS_NEED_SET_COUNT % self.CheckResult.access_setting_count
        print(access_need_set_count)
        LogHelper.info(access_need_set_count)

        access_cant_set_count = ACCESS_CANT_SET_COUNT % self.CheckResult.cant_set_access_file_count
        print(access_cant_set_count)
        LogHelper.info(access_cant_set_count)

        owner_need_transfer_count = OWNER_NEED_TRANSFER_COUNT % self.CheckResult.transfer_setting_count
        print(owner_need_transfer_count)
        LogHelper.info(owner_need_transfer_count)

        owner_cant_transfer_count = OWNER_CANT_TRANSFER_COUNT % self.CheckResult.cant_transfer_file_count
        print(owner_cant_transfer_count)
        LogHelper.info(owner_cant_transfer_count)

        print()
