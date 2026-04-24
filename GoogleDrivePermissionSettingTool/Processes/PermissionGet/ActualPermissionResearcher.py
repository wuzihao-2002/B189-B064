import csv
import threading
import traceback
from time import sleep

from Common.TsvItemEnum import TsvItemEnum
from DTO.FileActualPermissionInfo import FileActualPermissionInfo
from Processes.basic.BasicTsvInfoChecker import gid_get
from Common import LogHelper

PARAM = "id,mimeType,ownedByMe,trashed,writersCanShare,permissions"

exception_interrupt = False


class ActualPermissionResearcher:

    def __init__(self, google_drive, setting_sqlite, thread_pool, mode):
        self.google_drive = google_drive
        self.setting_sqlite = setting_sqlite
        self.thread_pool = thread_pool
        self.mode = mode

    def research_actual_permission(self, tsv_path):
        try:
            # launch thread pool, get google file actual permission
            self.thread_pool.set_target(self.permission_get)
            self.thread_pool.run()

            # read tsv info
            read_thread = threading.Thread(target=self.tsv_read, args=(tsv_path,))
            read_thread.setDaemon(True)
            read_thread.start()

            # wait task end
            read_thread.join()
            while not exception_interrupt and self.thread_pool.state():
                sleep(5)

            # shutdown thread pool and commit data to db
            self.thread_pool.shutdown()
            self.setting_sqlite.commit()

            # close task thread
            self.thread_pool.close()
            self.setting_sqlite.close()
        except Exception as e:
            LogHelper.debug("Actual Permission Research Err: %s" % e)
            LogHelper.debug(traceback.format_exc())

        self.set_exception_interrupt(False)

    def tsv_read(self, tsv_path):
        try:
            with open(tsv_path, 'r', encoding='UTF-8') as file:
                iterator = csv.DictReader(file, delimiter='\t')
                for line_dict in iterator:
                    file_type = line_dict[TsvItemEnum.TYPE.value]
                    check_result = line_dict[TsvItemEnum.CHECK_RESULT.value]

                    if self.mode == "/MODE:M" and check_result == "□" \
                            or self.mode == "/MODE:S" and file_type.upper() == "D":
                        file_id = gid_get(line_dict[TsvItemEnum.URI.value])
                        self.thread_pool.add_work(file_id)
        except Exception as e:
            LogHelper.debug("Tsv Read Err: %s" % e)
            LogHelper.debug(traceback.format_exc())
            self.set_exception_interrupt(True)

    def permission_get(self, file_id):
        try:
            child_permissions = self.get_children(file_id)
            for child_permission in child_permissions:
                actual_permission_info = FileActualPermissionInfo()
                actual_permission_info.set_values(child_permission)

                self.setting_sqlite.save_check_result(actual_permission_info)
        except Exception as e:
            LogHelper.debug("Actual Permission Get Err: %s" % e)
            LogHelper.debug(traceback.format_exc())

    def get_children(self, parent_gid):
        """
        Get information under a folder by ID
        :param parent_gid:
        :return:Return information about the next level of the found folder
        """
        child_query = "\"" + parent_gid + "\"" + " in parents"
        file_list = self.google_drive.list_file({"q": child_query, "fields": "nextPageToken,files(%s)" % PARAM})

        return file_list

    @staticmethod
    def set_exception_interrupt(flg):
        global exception_interrupt
        exception_interrupt = flg
