import datetime
import io
import re
import socket
import threading
import traceback
from time import sleep

import ntplib
import yaml
from pytz import timezone

from GoogleAPI.GoogleApiDriveService import GoogleApiDriveService
from Common import LogHelper


class MaxThreadsAutoStat:
    TERMINAL_FILE_REGEX = r"^((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})(\.((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})){3}_\d+\.txt$"

    def __init__(self, g_drive: GoogleApiDriveService, terminal_folder_g_id, update_schedule, max_threads,
                 total_threads, terminal_order, handle_uri):
        self.TerminalFileOPS = _TerminalFileOPS(g_drive, terminal_folder_g_id)
        self.schedule = _Scheduler(g_drive, update_schedule)
        self.max_threads = max_threads
        self.total_threads = total_threads
        self.host = self._get_host()
        self.terminal_file_name = f"{self.host}_{terminal_order}.txt"
        self.terminal_file = None
        self.thread_count = 0
        self.scheduler_started = False
        self.scheduler_lock = threading.Lock()
        self.handler_gid = self.get_gid(handle_uri)
        self.terminal_file_content = f"ToolType: SettingTool\nHandlerURI: {handle_uri}".encode()

    def init_terminal_file(self):
        """
            remove expired terminal files and create the current terminal file
        :return:
        """
        # get the same terminal files as the specified IP
        current_terminal_files = self.TerminalFileOPS.get_current_terminal_files(self.host)
        # remove the expired terminal file with same IP
        self._remove_expired_file(current_terminal_files)
        # create the terminal file for the current instance
        self.terminal_file = self.TerminalFileOPS.create_file(self.terminal_file_name, self.terminal_file_content)

    def handler_folder_is_used(self):
        """
            Verify if the handler folder is being used
        :return:
        """
        expire_time = network_time.get_expired_time(expired_minutes=2 * self.schedule.update_schedule)
        terminal_files = self.TerminalFileOPS.get_all_terminal_files()

        for file in terminal_files:
            if self._terminal_file_match(file["name"]):
                if self.terminal_file_name.lower() == file["name"].lower() \
                        and self.terminal_file["id"] == file["id"]:
                    continue

                # not expired
                if not network_time.expired(file["modifiedTime"], expire_time):
                    try:
                        media = self.TerminalFileOPS.get_media(file["id"])
                        yaml_info = yaml.safe_load(media)
                        handler_uri = yaml_info["HandlerURI"]
                        gid = self.get_gid(handler_uri)

                        # there are multiple tools handling the same folder
                        if self.handler_gid == gid:
                            return True
                    except Exception as e:
                        LogHelper.error("ターミナルファイルの読み取りに失敗しました。Err:%s" % e)
                        LogHelper.debug(traceback.format_exc())

        return False

    def init_thread_count(self):
        """
            calculate thread count
        :return:
        """
        return self.calculate_thread_count()

    def schedule_run(self, thread_pool):
        """
            use sub thread to periodically check and update the maximum thread count
        :param thread_pool:
        :return:
        """
        self.schedule.thread_pool = thread_pool
        self.schedule.TerminalFileOPS = self.TerminalFileOPS
        self.schedule.pre_thread_count = self.thread_count
        self.schedule.terminal_file = self.terminal_file
        self.schedule.allocate_update_schedule()

        # start schedule task
        self.schedule_task()

    def schedule_task(self):
        with self.scheduler_lock:
            if self.scheduler_started:
                return
            self.scheduler_started = True

        # update terminal file task
        update_thread = threading.Thread(target=self.schedule.update_terminal_file_schedule,
                                         args=(self.update_terminal_file,))
        update_thread.setDaemon(True)
        update_thread.start()

        # adjust thread pool task
        adjust_thread = threading.Thread(target=self.schedule.adjust_thread_count_schedule,
                                         args=(self.calculate_thread_count,))
        adjust_thread.setDaemon(True)
        adjust_thread.start()

    def update_terminal_file(self):
        """
            update the Google file, and if the file doesn't exist, create it anew
        :return:
        """
        try:
            self.TerminalFileOPS.update_file_content(self.terminal_file["id"], self.terminal_file_content)
        except Exception as e:
            msg = e.__str__().upper()
            if msg.__contains__("NOT FOUND"):
                self.terminal_file = self.TerminalFileOPS.create_file(self.terminal_file["name"],
                                                                      self.terminal_file_content)
            else:
                raise e
        return self.terminal_file

    def calculate_thread_count(self):
        """
            calculate the number of files updated at a specified time
        :return:
        """
        LogHelper.info("Max Threads数を計算します。")

        running_procs_count = self._calculate_running_procs_count()

        thread_count = self.total_threads // running_procs_count

        if thread_count > self.max_threads:
            thread_count = self.max_threads

        if thread_count <= 0:
            thread_count = 1

        self.thread_count = thread_count

        LogHelper.info("Max Threads数を計算しました。Max Threads: %d" % self.thread_count)

        return self.thread_count

    def _calculate_running_procs_count(self):
        """

        :return:
        """
        expire_time = network_time.get_expired_time(expired_minutes=2 * self.schedule.update_schedule)
        terminal_files = self.TerminalFileOPS.get_all_terminal_files()

        running_procs_count = 1
        for file in terminal_files:
            if self._terminal_file_match(file["name"]):
                if self.terminal_file_name.lower() == file["name"].lower() \
                        and self.terminal_file["id"] == file["id"]:
                    continue

                if not network_time.expired(file["modifiedTime"], expire_time):
                    running_procs_count += 1

        return running_procs_count

    def _remove_expired_file(self, current_terminal_files):
        """
            move expired files to the trash can
        :param current_terminal_files:
        :return:
        """
        try:
            expired_ntp_time = network_time.get_expired_time(expired_minutes=2 * self.schedule.update_schedule)

            # Move files that meet the criteria to the trash can
            for file in current_terminal_files:
                try:
                    if self._terminal_file_match(file["name"]) and file["ownedByMe"] is True \
                            and (network_time.expired(file["modifiedTime"], expired_ntp_time)
                                 or file["name"].lower() == self.terminal_file_name.lower()):
                        self.TerminalFileOPS.trash(file["id"])
                except Exception as e:
                    LogHelper.error("「%s」(gid：%s)の削除が失敗しました。Err: %s" % (file["name"], file["id"], e))
                    LogHelper.debug(traceback.format_exc())
                    continue
        except Exception as e:
            LogHelper.error(e)
            LogHelper.debug(traceback.format_exc())

    def remove_terminal_file(self):
        name = ""
        gid = ""
        try:
            if self.terminal_file is not None:
                name = self.terminal_file["name"]
                gid = self.terminal_file["id"]
                self.TerminalFileOPS.trash(self.terminal_file["id"])
                LogHelper.info("「%s」(gid：%s)を削除しました。" % (name, gid))
        except Exception as e:
            LogHelper.error(
                "「%s」(gid：%s)の削除が失敗しました。Err: %s" % (name, gid, e))
            LogHelper.debug(traceback.format_exc())

    def _current_terminal_file_exists(self, terminal_files):
        """
            check if the current terminal file exists
        :param terminal_files:
        :return:
        """
        for file in terminal_files:
            if file["name"] == self.terminal_file_name \
                    and file["id"] == self.terminal_file["id"]:
                return True

        return False

    def _terminal_file_match(self, string):
        """
            check the file name format(IP_X.txt)
        :param string:
        :return:
        """
        return re.match(self.TERMINAL_FILE_REGEX, string, re.I)

    @staticmethod
    def _get_host():
        """
            retrieve the terminal host
        :return:
        """
        try:
            hostname = socket.gethostname()
            host = socket.gethostbyname(hostname)
            return host
        except Exception as e:
            LogHelper.error(e)
            LogHelper.debug(traceback.format_exc())
            raise Exception("端末のIPアドレスの取得が失敗しました。")

    @staticmethod
    def get_gid(google_uri):
        """
            get google file id
        :param google_uri:
        :return:
        """
        gid = re.findall(r"/folders/(.+)|$", google_uri.strip())[0]

        if gid.__contains__("/"):
            gid = gid[: gid.index("/")]
        if gid.__contains__("?"):
            gid = gid[: gid.index("?")]
        return gid


class _Scheduler:
    lock = threading.Lock()

    def __init__(self, g_drive: GoogleApiDriveService, update_schedule):
        self.g_drive = g_drive
        self.update_schedule = update_schedule
        self.update_next_run = None
        self.thread_pool = None
        self.TerminalFileOPS = None
        self.updating_terminal_file_flag = False
        self.adjusting_thread_count_flag = False
        self.terminal_file = None

    def update_terminal_file_schedule(self, target):
        """
            update terminal file
        :param target:
        :return:
        """
        while True and not self.thread_pool.stop:
            sleep(10)

            if self.thread_pool.stop:
                return

            try:
                if self._should_run(self.update_next_run):
                    LogHelper.info("「%s」(gid:%s)を更新します。" % (self.terminal_file["name"], self.terminal_file["id"]))

                    with self.lock:
                        self.updating_terminal_file_flag = True

                        if not self.adjusting_thread_count_flag:
                            # pause the addition of tasks to the thread pool
                            self.thread_pool.set_suspend(True)
                            self.g_drive.set_suspend(True)

                    # update terminal file
                    self.terminal_file = target()

                    LogHelper.info("「%s」(gid:%s)を更新しました。" % (self.terminal_file["name"], self.terminal_file["id"]))

                    # get the next start time for the task
                    self._schedule_update_next_run()
            except Exception as e:
                LogHelper.error(
                    "「%s」(gid:%s)の更新が失敗しました。Err:%s" % (self.terminal_file["name"], self.terminal_file["id"], e))
                LogHelper.debug(traceback.format_exc())
            finally:
                self.updating_terminal_file_flag = False
                with self.lock:
                    if not self.adjusting_thread_count_flag:
                        # resume adding tasks to the thread pool
                        self.thread_pool.set_suspend(False)
                        self.g_drive.set_suspend(False)

    def adjust_thread_count_schedule(self, target):
        """
            calculate max thread count and reset tread pool
        :param target:
        :return:
        """
        while True and not self.thread_pool.stop:
            sleep(10)

            if self.thread_pool.stop:
                return

            try:
                # calculate max thread count
                thread_count = target()

                if self.thread_pool.max_workers != thread_count:
                    with self.lock:
                        self.adjusting_thread_count_flag = True

                    # pause the addition of tasks to the thread pool
                    self.thread_pool.set_suspend(True)

                    # When the thread count changes, reset the thread pool.
                    self.g_drive.set_suspend(False)
                    # reset thread pool
                    self.thread_pool.reset(thread_count)
            except Exception as e:
                LogHelper.error("Max Threads数を計算し、ThreadPoolの再作成に失敗しました。Err:%s" % e)
                LogHelper.debug(traceback.format_exc())
            finally:
                self.adjusting_thread_count_flag = False
                with self.lock:
                    if not self.updating_terminal_file_flag:
                        # resume adding tasks to the thread pool
                        self.thread_pool.set_suspend(False)
                        self.g_drive.set_suspend(False)

    @staticmethod
    def _should_run(next_run):
        current_time = network_time.get_network_time()
        return current_time >= next_run

    def _schedule_update_next_run(self):
        self.update_next_run += datetime.timedelta(minutes=self.update_schedule)

    def allocate_update_schedule(self):
        now_ntp_time = network_time.get_network_time()
        self.update_next_run = now_ntp_time + datetime.timedelta(minutes=self.update_schedule)


class _TerminalFileOPS:
    TERMINAL_FILES_QUERY = "'%s' in parents and mimeType = 'text/plain' and trashed=false"
    SPECIAL_TERMINAL_FILES_QUERY = "'%s' in parents and name contains '%s' and mimeType='text/plain' and trashed=false"
    PARAM = "id, name, ownedByMe, modifiedTime"
    MIME_TYPE = "text/plain"

    def __init__(self, g_drive, p_gid):
        self.g_drive = g_drive
        self.p_gid = p_gid

    def get_current_terminal_files(self, prefix_ip):
        """
            retrieve the .txt files in the folder(p_gid) with terminal IP prefixes
        :param prefix_ip:
        :return:
        """
        current_terminal_files = self.get_file_list(self.SPECIAL_TERMINAL_FILES_QUERY % (self.p_gid, prefix_ip))
        return current_terminal_files

    def get_all_terminal_files(self):
        """
            retrieve all the .txt files in the folder(p_gid)
        :return:
        """
        terminal_files = self.get_file_list(self.TERMINAL_FILES_QUERY % self.p_gid)
        return terminal_files

    def get_file_list(self, q):
        """
            get files by search query {q}
        :param q:
        :return:
        """
        file_list = self.g_drive.list_file({"q": q, "fields": "nextPageToken,files(%s)" % self.PARAM},
                                           allow_suspend=False)
        return file_list

    def get_media(self, gid):
        return self.g_drive.get_media(gid)

    def create_file(self, filename, content, mimetype="text/plain", p_gid=None):
        """
            create terminal file in the specified folder
        :param filename:
        :param content:
        :param mimetype:
        :param p_gid:
        :return:
        """
        if p_gid is None:
            p_gid = self.p_gid

        body = {
            "name": filename,
            "mimeType": mimetype,
            "parents": [p_gid]
        }

        return self.g_drive.create_file(body, io.BytesIO(content), mimetype, allow_suspend=False)

    def update_file_content(self, g_id, content):
        """
            by modifying the file content, Google Drive can change the modifiedTime of the file
        :param g_id:
        :param content:
        :return:
        """
        self.g_drive.update_file_content(g_id, io.BytesIO(content), self.MIME_TYPE, allow_suspend=False)

    def trash(self, g_id):
        """
            move file to trash can
        :param g_id:
        :return:
        """
        self.g_drive.update_file(g_id, {"trashed": True}, allow_suspend=False)


class _NetWorkTime:
    """

    """
    SERVER_ADDRESS = "time.google.com"
    TIMEZONE = "UTC"
    TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fz"
    SECONDS_OF_DAY = 60 * 60 * 24

    def __init__(self):
        pass

    def get_network_time(self, time_format=TIME_FORMAT):
        """
            obtain the current UTC network time
        :param time_format:
        :return:
        """
        ntp_client = ntplib.NTPClient()
        try_count = 0
        while True:
            try:
                response = ntp_client.request(self.SERVER_ADDRESS)
                ntp_time = datetime.datetime.fromtimestamp(response.tx_time, tz=timezone(self.TIMEZONE))
                ntp_time_str = self.time_2_str(ntp_time, time_format)
                return self.str_2_time(ntp_time_str, time_format)
            except Exception as e:
                if try_count == 3:
                    raise Exception("NetWork Time received failed。Err:%s" % e)
                try_count += 1
                LogHelper.error(e)
                LogHelper.debug(traceback.format_exc())
                LogHelper.error("NetWork Time received failed, try again: %d" % try_count)
                sleep(5)

    def get_expired_time(self, time_format=TIME_FORMAT, expired_minutes=0, expired_seconds=0):
        """
            obtain the expiry time point
        :param time_format:
        :param expired_minutes:
        :param expired_seconds:
        :return:
        """
        now_ntp_time = self.get_network_time(time_format)
        expired_time = now_ntp_time - datetime.timedelta(minutes=expired_minutes) - datetime.timedelta(
            seconds=expired_seconds)

        return expired_time

    def expired(self, time_str: str, expired_time: datetime.datetime, time_format=TIME_FORMAT):
        """
            check if the specified time has passed the expiry time
        :param time_str:
        :param expired_time:
        :param time_format:
        :return:
        """
        time = self.str_2_time(time_str, time_format)
        return time < expired_time

    @staticmethod
    def str_2_time(time_str: str, time_format=TIME_FORMAT):
        """
            string, format -> datetime
        :param time_str:
        :param time_format:
        :return:
        """
        return datetime.datetime.strptime(time_str, time_format)

    @staticmethod
    def time_2_str(time: datetime.datetime, time_format=TIME_FORMAT):
        """
            datetime -> string, format
        :param time:
        :param time_format:
        :return:
        """
        return time.strftime(time_format)


network_time = _NetWorkTime()
