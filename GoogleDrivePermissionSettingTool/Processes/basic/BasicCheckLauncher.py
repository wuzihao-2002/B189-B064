import csv
import threading
import traceback
from time import sleep

from Common.TsvItemEnum import TsvItemEnum
from DTO.FileActualPermissionInfo import FileActualPermissionInfo
from DTO.FileDetail import FileDetail
from Processes.SqliteDB import SqlCommand
from Processes.basic.BasicTsvInfoChecker import gid_get
from Common import LogHelper

exception_interrupt = threading.Event()


class BasicCheckLauncher:

    def __init__(self, setting_sqlite, thread_pool, mode, max_threads_stat):
        self.setting_sqlite = setting_sqlite
        self.thread_pool = thread_pool
        self.mode = mode
        self.max_threads_stat = max_threads_stat

    def launch_check(self, target, tsv_path):
        try:
            self.thread_pool.re_init()
            self.setting_sqlite.re_init()
            self.max_threads_stat.schedule_task()

            # launch thread_pool,startup check
            self.thread_pool.set_target(target)
            self.thread_pool.run()

            # read google file info will be checked by the thread_pool
            read_thread = threading.Thread(target=self.tsv_read, args=(tsv_path,))
            read_thread.setDaemon(True)
            read_thread.start()

            # wait task end
            read_thread.join()
            while not exception_interrupt.is_set() and self.thread_pool.state():
                sleep(5)

            # shutdown thread pool and commit data to db
            self.thread_pool.shutdown()
            self.setting_sqlite.commit()

            # close task thread
            self.thread_pool.close()
            self.setting_sqlite.close()
        except Exception as e:
            LogHelper.debug(traceback.format_exc())
            raise Exception("CheckLauncher Err: %s" % e)

    def tsv_read(self, tsv_path):
        try:
            # get fields structure
            cursor = self.setting_sqlite.execute(SqlCommand.select_file_actual_permission_by_file_id_sql, [-1])
            mapper = self.setting_sqlite.get_cursor_mapper(cursor.description)

            with open(tsv_path, 'r', encoding='UTF-8') as file:
                iterator = csv.DictReader(file, delimiter='\t')
                line_num = 1
                for line_dict in iterator:
                    line_num += 1
                    file_id = gid_get(line_dict[TsvItemEnum.URI.value])
                    parent_id = gid_get(line_dict[TsvItemEnum.PARENT_URI.value])

                    # file info
                    file_detail = FileDetail()
                    file_detail.set_values_from_tsv(line_num, file_id, line_dict)

                    # file actual permission
                    actual_permission = self.get_actual_permission(file_id, mapper)

                    if self.mode == "/MODE:M":
                        parent_actual_permission = self.get_actual_permission(parent_id, mapper)
                        self.thread_pool.add_work({"file_detail": file_detail, "actual_permission": actual_permission,
                                                   "parent_actual_permission": parent_actual_permission})
                    else:
                        self.thread_pool.add_work({"file_detail": file_detail, "actual_permission": actual_permission})
            cursor.close()
        except Exception as e:
            LogHelper.info("Tsv Read Err: %s" % e)
            LogHelper.debug(traceback.format_exc())
            self.set_exception_interrupt(True)

    def get_actual_permission(self, gid, mapper):
        cursor = self.setting_sqlite.execute(SqlCommand.select_file_actual_permission_by_file_id_sql, [gid])
        actual_permission = None
        actual_permission_record = cursor.fetchone()
        if actual_permission_record is not None:
            actual_permission = FileActualPermissionInfo()
            actual_permission.set_values_from_db(actual_permission_record, mapper)

        return actual_permission

    @staticmethod
    def get_exception_interrupt():
        return exception_interrupt.is_set()

    @staticmethod
    def set_exception_interrupt(flg):
        if flg:
            exception_interrupt.set()
        else:
            exception_interrupt.clear()
