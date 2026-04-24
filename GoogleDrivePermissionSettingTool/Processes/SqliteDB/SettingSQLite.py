import sqlite3
import threading
import traceback
from time import sleep

from DTO.FileAccessSettingInfo import FileAccessSettingInfo
from DTO.FileActualPermissionInfo import FileActualPermissionInfo
from DTO.FileDetail import FileDetail
from DTO.FileMovingInfo import FileMovingInfo
from DTO.FileTransferSettingInfo import FileTransferSettingInfo
from Processes.PermissionGet import ActualPermissionResearcher
from Processes.SqliteDB import SqlCommand
from Processes.basic import BasicCheckLauncher, BasicSettingLauncher
from Common import TsvHelper, LogHelper


class SettingSQLite:

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.save_exit = False
        self.commit_thread = None
        self.lock = threading.Lock()

    def init_db(self):
        init_command = SqlCommand.create_tbl_file_detail_sql
        init_command += SqlCommand.create_tbl_file_access_setting_info_sql
        init_command += SqlCommand.create_tbl_file_transfer_setting_info_sql
        init_command += SqlCommand.create_tbl_file_moving_info_sql
        init_command += SqlCommand.create_tbl_file_actual_permission_info_sql
        init_command += SqlCommand.vacuum_sql

        with self.lock:
            self.conn.executescript(init_command)

    def re_init(self):
        self.__init__(db_path=self.db_path)

    def save_check_result(self, data):
        """
            save google drive file check result
        :param data:
        :return:
        """
        try:
            if data is not None:
                # save file info to db
                insert_sql = self.get_save_check_result_sql(data)
                self.execute(insert_sql, data.get_values())

        except Exception as e:
            LogHelper.info("Save CheckResult To Sqlite Err: %s" % e)
            LogHelper.debug(traceback.format_exc())
            BasicCheckLauncher.BasicCheckLauncher.set_exception_interrupt(True)
            ActualPermissionResearcher.ActualPermissionResearcher.set_exception_interrupt(True)

    def save_set_result(self, data):
        """
            save google drive file set result
        :param data:
        :return:
        """
        try:
            if data is not None:
                file_detail = data["file_detail"]
                need_update_writer = data["update_writer"]
                # save setting result
                if need_update_writer:
                    # update field:writer,setting_result
                    update_sql = SqlCommand.update_file_detail_set_result_and_writer_sql
                    self.execute(update_sql,
                                 [file_detail.setting_result, file_detail.err_info,
                                  file_detail.writer, file_detail.line_num])
                else:
                    # update field:setting_result
                    update_sql = SqlCommand.update_file_detail_set_result_sql
                    self.execute(update_sql,
                                 [file_detail.setting_result, file_detail.err_info,
                                  file_detail.line_num])

        except Exception as e:
            LogHelper.info("Save SettingResult To Sqlite Err: %s" % e)
            LogHelper.debug(traceback.format_exc())
            BasicSettingLauncher.BasicSettingLauncher.set_exception_interrupt(True)

    def retrieve_work_iterator(self, research_tbl):
        """
            retrieve the google file that need to be set
        :param research_tbl:
        :return:
        """
        try:
            mapper = None

            # get handle object
            select_sql, work_info = self.get_research_target_work(research_tbl)
            if select_sql is None and work_info is None:
                return

            # get the google file that need to be set
            cursor = self.execute(select_sql)
            if cursor.description is not None:
                mapper = self.get_cursor_mapper(cursor.description)

            # add task to thread_pool
            for record in cursor:
                if self.save_exit:
                    return

                # setting info
                require_setting_work = work_info.create_new()
                require_setting_work.set_values_from_db(record, mapper)
                # file detail
                file_detail = FileDetail()
                file_detail.set_values_from_db(record, mapper)

                yield {"setting_work": require_setting_work, "file_detail": file_detail}

        except Exception as e:
            LogHelper.info("Get Setting items From Sqlite Err: %s" % e)
            LogHelper.debug(traceback.format_exc())
            BasicSettingLauncher.BasicSettingLauncher.set_exception_interrupt(True)

    def execute(self, sql, *args, **kwargs):
        with self.lock:
            return self.conn.execute(sql, *args, **kwargs)

    def commit(self):
        with self.lock:
            self.conn.commit()

    def _auto_commit(self, second):
        """
            interval point second commit
        :param second:
        :return:
        """
        try:
            while True:
                sleep(second)

                if self.save_exit:
                    return

                self.commit()
        except Exception as e:
            LogHelper.error("Sqlite commit Err:%s" % e)
            LogHelper.debug(traceback.format_exc())
            BasicSettingLauncher.BasicSettingLauncher.set_exception_interrupt(True)
            BasicCheckLauncher.BasicCheckLauncher.set_exception_interrupt(True)
            ActualPermissionResearcher.ActualPermissionResearcher.set_exception_interrupt(True)

    def auto_commit(self, second=10):
        self.commit_thread = threading.Thread(target=self._auto_commit, args=(second,))
        self.commit_thread.setDaemon(True)
        self.commit_thread.start()

    @staticmethod
    def get_save_check_result_sql(handle_work):
        """
            get the insert sql statement based on the handle_work
        :param handle_work:
        :return:
        """
        insert_sql = None

        # save file detail
        if isinstance(handle_work, FileDetail):
            insert_sql = SqlCommand.insert_file_detail_sql
        # save require set permission
        elif isinstance(handle_work, FileAccessSettingInfo):
            insert_sql = SqlCommand.insert_file_access_setting_info_sql
        # save require transfer owner
        elif isinstance(handle_work, FileTransferSettingInfo):
            insert_sql = SqlCommand.insert_file_transfer_setting_info_sql
        # save require move file
        elif isinstance(handle_work, FileMovingInfo):
            insert_sql = SqlCommand.insert_file_moving_info_sql
        elif isinstance(handle_work, FileActualPermissionInfo):
            insert_sql = SqlCommand.insert_file_actual_permission_info_sql

        return insert_sql

    @staticmethod
    def get_research_target_work(research_tbl):
        """
            get the target object of the research worker
        :param research_tbl:
        :return:
        """
        select_sql = None
        work_info = None

        # access permission handler
        if research_tbl == SqlCommand.access_setting_tbl:
            select_sql = SqlCommand.select_access_setting_info_sql
            work_info = FileAccessSettingInfo()
        # transfer owner handler
        elif research_tbl == SqlCommand.transfer_setting_tbl:
            select_sql = SqlCommand.select_transfer_setting_and_file_detail_info_sql
            work_info = FileTransferSettingInfo()
        # folder moving handler
        elif research_tbl == SqlCommand.file_moving_tbl:
            select_sql = SqlCommand.select_file_moving_and_file_detail_info_sql
            work_info = FileMovingInfo()

        return select_sql, work_info

    def close(self):
        """
            stop task
        :return:
        """
        self.save_exit = True

        self.conn.close()

    def file_info_to_tsv(self, output_file):
        """
            write google file info to tsv
        :param output_file:
        :return:
        """
        cursor = self.execute(SqlCommand.select_file_detail_sql)
        mapper = self.get_cursor_mapper(cursor.description)

        # loop write
        for record in cursor:
            record_dict = self.record_to_write_dict(record, mapper)
            TsvHelper.write_to_tsv(output_file, record_dict)

    @staticmethod
    def record_to_write_dict(record, mapper):
        """
            convert db line to dict
        :param record:
        :param mapper:
        :return:
        """
        from Common.TsvItemEnum import TsvItemEnum
        record_dict = {
            TsvItemEnum.FILE.value: record[mapper["file"]],
            TsvItemEnum.TYPE.value: record[mapper["type"]],
            TsvItemEnum.LAST_UPDATE_DATE.value: record[mapper["last_update_date"]],
            TsvItemEnum.LAST_UPDATE_TIME.value: record[mapper["last_update_time"]],
            TsvItemEnum.LAST_UPDATER.value: record[mapper["last_updater"]],
            TsvItemEnum.URI.value: record[mapper["uri"]],
            TsvItemEnum.PARENT_FOLDER.value: record[mapper["parent_folder"]],
            TsvItemEnum.PARENT_URI.value: record[mapper["parent_uri"]],
            TsvItemEnum.WRITERS_CAN_SHARE.value: record[mapper["writers_can_share"]],
            TsvItemEnum.DOMAIN.value: record[mapper["domain"]],
            TsvItemEnum.OWNER.value: record[mapper["owner"]],
            TsvItemEnum.WRITER.value: record[mapper["writer"]],
            TsvItemEnum.READER.value: record[mapper["reader"]],
            TsvItemEnum.CHECK_RESULT.value: record[mapper["check_result"]],
            TsvItemEnum.SETTING_RESULT.value: record[mapper["setting_result"]],
            TsvItemEnum.ERR_INFO.value: record[mapper["err_info"]]
        }

        return record_dict

    @staticmethod
    def get_cursor_mapper(cursor_description):
        """
            record select fields index
        :param cursor_description:
        :return:
        """
        mapper = {}
        cursor_description_len = len(cursor_description)
        for index in range(cursor_description_len):
            mapper[cursor_description[index][0]] = index

        return mapper
