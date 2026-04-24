import traceback
from time import sleep

from Common import TsvHelper, LogHelper

exception_interrupt = False


class BasicSettingLauncher:

    def __init__(self, setting_sqlite, thread_pool, max_threads_stat):
        self.setting_sqlite = setting_sqlite
        self.thread_pool = thread_pool
        self.max_threads_stat = max_threads_stat

    def launch_setting(self, target, research_tbl):
        """
            multi-thread set google drive file permission, or move google drive file
        :param target:
        :param research_tbl:
        :return:
        """
        try:
            self.thread_pool.re_init()
            self.setting_sqlite.re_init()
            self.max_threads_stat.schedule_task()

            # launch thread_pool,startup setting
            self.thread_pool.set_target(target)
            self.thread_pool.run()

            # retrieve the Google Files that required setting/moving from SQLite DB
            work_iterator = self.setting_sqlite.retrieve_work_iterator(research_tbl)

            for work in work_iterator:
                # setting/moving Google File using thread pool
                self.thread_pool.add_work(work)

            # wait task end
            while not exception_interrupt and self.thread_pool.state():
                sleep(5)

            # shutdown thread pool and commit data to db
            self.thread_pool.shutdown()
            self.setting_sqlite.commit()

            # close task thread
            self.setting_sqlite.close()
            self.thread_pool.close()
        except Exception as e:
            LogHelper.debug(traceback.format_exc())
            raise Exception("SettingLauncher Err: %s" % e)

    def setting_result_to_tsv(self, output_tsv_path):
        """
            write setting's result to tsv
        :param output_tsv_path:
        :return:
        """
        TsvHelper.write_title(output_tsv_path)

        self.setting_sqlite.re_init()

        with open(output_tsv_path, 'a', encoding='UTF-8', newline="", errors='ignore') as output_file:
            self.setting_sqlite.file_info_to_tsv(output_file)

        self.setting_sqlite.close()

    @staticmethod
    def get_exception_interrupt():
        return exception_interrupt

    @staticmethod
    def set_exception_interrupt(flg):
        global exception_interrupt
        exception_interrupt = flg
