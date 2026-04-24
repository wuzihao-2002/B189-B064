import queue
import threading
import traceback
from concurrent.futures.thread import ThreadPoolExecutor
from time import sleep

from Processes.PermissionGet import ActualPermissionResearcher
from Processes.basic import BasicCheckLauncher, BasicSettingLauncher
from Common import LogHelper


class CheckAndSetThreadPool(ThreadPoolExecutor):

    def __init__(self, max_workers, max_tasks=300, target=None):
        self.init_thread_pool(max_workers)
        self.max_workers = max_workers
        self.max_tasks = max_tasks
        self.work_queue = queue.LifoQueue(maxsize=max_tasks)
        self.target = target
        self.exit = False
        self.thread = None
        self.target_method = None
        self.suspend = False
        self.stop = False
        self.mutex = threading.Lock()
        self.working_count = 0

    def init_thread_pool(self, max_workers):
        LogHelper.info("ThreadPool（Max Threads: %d）を作成します。" % max_workers)
        super().__init__(max_workers=max_workers)
        self.max_workers = max_workers
        LogHelper.info("ThreadPool（Max Threads: %d）を作成しました。" % max_workers)

    def re_init(self):
        self.__init__(max_workers=self.max_workers, max_tasks=self.max_tasks, target=self.target)

    def set_target(self, target_method):
        """
            set thread task method
        :param target_method:
        :return:
        """
        self.target_method = target_method
        self.target = self.target_wrapper

    def target_wrapper(self, *args):
        """
            wrapper target method
        :param args:
        :return:
        """
        try:
            self.target_method(*args)
        except Exception as e:
            LogHelper.info("Target Method Execute Err: %s" % e)
            LogHelper.debug(traceback.format_exc())
            BasicCheckLauncher.exception_interrupt = True
            BasicSettingLauncher.exception_interrupt = True

        with self.mutex:
            self.working_count -= 1

    def add_work(self, work):
        """
            add task to work queue
        :param work:
        :return:
        """
        if not self.exit:
            with self.mutex:
                self.working_count += 1

            self.work_queue.put(work)

    def _submit(self, *args):
        """
            submit task
        :param args:
        :return:
        """
        while True:
            if self.exit:
                return

            with self.mutex:
                if not self.suspend:
                    super().submit(self.target, *args)
                    return

            sleep(1)

    def run(self):
        """
            task [worker] begin
        :return:
        """
        self.thread = threading.Thread(target=self.worker)
        self.thread.setDaemon(True)
        self.thread.start()

    def worker(self):
        """
            take work_queue's task to threadPool
        :return:
        """
        try:
            while True:
                if self.exit:
                    return

                while not self.work_queue.empty():
                    # End thread when an exception occurs
                    if BasicCheckLauncher.exception_interrupt or BasicSettingLauncher.exception_interrupt \
                            or ActualPermissionResearcher.exception_interrupt:
                        return

                    while self._work_queue.qsize() > 10:
                        sleep(0.1)

                    task = self.work_queue.get()
                    if task is not None:
                        self._submit(task)

                    if self.exit:
                        return
        except Exception as e:
            LogHelper.info("ThreadPool Execute Err: %s" % e)
            LogHelper.debug(traceback.format_exc())
            BasicCheckLauncher.exception_interrupt = True
            BasicSettingLauncher.exception_interrupt = True
            ActualPermissionResearcher.exception_interrupt = True

    def close(self, wait=True):
        """
            stop task
        :param wait:
        :return:
        """
        self.exit = True

        while self.thread is not None and self.thread.is_alive():
            sleep(1)

        super().shutdown(wait)
        self.stop = True

    def state(self):
        """
            return thread pool state
                true: at work
                false: at rest
        :return:
        """
        with self.mutex:
            state = self.working_count > 0 or self.suspend
        return state

    def reset(self, max_workers):
        """
            Reinitialize the thread pool
        :param max_workers:
        :return:
        """
        if self.stop:
            return

        super().shutdown(True)
        self.init_thread_pool(max_workers)

    def set_suspend(self, suspend):
        with self.mutex:
            self.suspend = suspend
