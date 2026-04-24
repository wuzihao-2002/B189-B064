import os
import sys
import traceback

import psutil

from Checker import YamlInfoChecker
from GoogleAPI.GoogleApiAuth import GoogleApiAuth
from GoogleAPI.GoogleApiDriveService import GoogleApiDriveService
from Processes.FolderMove.FolderMover import FolderMover
from Processes.FolderMove.FolderMovingChecker import FolderMovingChecker
from Processes.PermissionSet.PermissionSetter import PermissionSetter
from Processes.PermissionSet.PermissionSettingChecker import PermissionSettingChecker
from Processes.SqliteDB.SettingSQLite import SettingSQLite
from Processes.ThreadPool.MaxThreadsAutoStat import MaxThreadsAutoStat
from Processes.ThreadPool.SettingThreadPool import CheckAndSetThreadPool
from Common import LogHelper, TsvHelper

# MSG
LAUNCH_PARAMETER_COUNT_NG_MSG = "起動引数をご指定お願いいたします。"
LAUNCH_PARAMETER_GET_NG_MSG = "起動引数2（何番目）は正の整数で設定してください。"
OTHER_PROGRAM_LAUNCH_PARAMETER_GET_NG_MSG = "全体プログラムの起動引数の取得が失敗しました。"
HANDLER_FOLDER_IS_USED_MSG = "設定対象フォルダ「%s」は使用中です。"
OK_END_MSG = "正常終了。"
NG_END_MSG = "異常終了。"
MULTIPLE_START_NG_MSG = "番号「%d」は使用中です。"

GOOGLE_ACCOUNT_INFO_MSG = "・Googleアカウント: "
SETTING_TSV_PATH = "・設定対象ファイルバス: "
SAVE_TSV_PATH = "・設定結果出力ファイルバス: "
MAX_THREADS_PROJECTID_MSG = "・合計スレッド数制限:"
RUNNING_TERMINAL_FILE_URI_MSG = "・「IP_n.txt」を保存URI:"
MAX_THREADS_TERMINAL_MSG = "・最大スレッド数制限:"
TERMINAL_FILE_UPDATE_SCHEDULE_MSG = "・「IP_n.txt」更新計画(min):"
TSV_FILE_LINE_COUNT = "「%s」総件数: %d"

# LOG
PERMISSION_SETTING_START_LOG = "GoogleDrive権限設定を開始します。"
PERMISSION_SETTING_OK_END_LOG = "GoogleDrive権限設定が正常に終了しました。"
PERMISSION_SETTING_NG_END_LOG = "GoogleDrive権限設定が異常に終了しました。"

FOLDER_MOVING_START_LOG = "GoogleDriveフォルダ移動を開始します。"
FOLDER_MOVING_OK_END_LOG = "GoogleDriveフォルダ移動が正常に終了しました。"
FOLDER_MOVING_NG_END_LOG = "GoogleDriveフォルダ移動が異常に終了しました。"

ERR_LOG = "エラー情報: %s"

SETTINGS_PATH = "AuthenticationConfig/settings.yaml"
DB_PATH = "GoogleDriveSetting.db"

# google drive service
google_drive: GoogleApiDriveService
# login user information
login_user: dict

thread_pool: CheckAndSetThreadPool
setting_sqlite: SettingSQLite


def google_account_login():
    """
        Google authentication
    :return:
    """
    global google_drive, login_user, creds
    auth = GoogleApiAuth(credential_file, credential_key)
    creds = auth.login()
    google_drive = GoogleApiDriveService(creds)
    login_user = google_drive.about("user")


def int_parse(value):
    _parse_flg = True
    _parse_value = -1
    try:
        _parse_value = int(value)
    except ValueError:
        _parse_flg = False

    return _parse_flg, _parse_value


def launch_parameter_chk():
    """
    入力パラメータを取得する
    :rtype: object
    """
    # check the number of parameters
    len_argv = len(sys.argv)
    if len_argv == 2 or len_argv == 3:
        for argv in sys.argv:
            print(argv, end=" ")
        print()

        # check terminal order
        _terminal_order = 1
        if len_argv == 3:
            _terminal_order = sys.argv[2]
            parse_flg, parse_value = int_parse(_terminal_order)
            if not parse_flg or parse_value <= 0:
                raise Exception(LAUNCH_PARAMETER_GET_NG_MSG)
            _terminal_order = parse_value

        return sys.argv[1], _terminal_order
    else:
        raise Exception(LAUNCH_PARAMETER_COUNT_NG_MSG)


def other_program_launch_parameter_get():
    """
        retrieve the launch parameter of other program
    :return:
    """
    launch_param_set = set()

    try:
        for proc in psutil.process_iter(['name', 'pid', 'cmdline']):
            try:
                proc_info = proc.info
                proc_pid = proc_info['pid']
                proc_name = proc_info['name']
                proc_cmdline = proc_info['cmdline']

                if proc_pid == pid or proc_pid == ppid:
                    continue

                if proc_cmdline is not None and proc_name in ["GoogleDriveResearchTool.exe",
                                                              "GoogleDrivePermissionSettingTool.exe"]:
                    launch_param_set.add(tuple(proc_cmdline))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        return launch_param_set
    except Exception as ex:
        LogHelper.error(ex)
        LogHelper.debug(traceback.format_exc())
        raise Exception(OTHER_PROGRAM_LAUNCH_PARAMETER_GET_NG_MSG)


def is_continue_execution(_terminal_order):
    """
        if there is already a program with the same launch parameter order num in the current terminal,
            terminate the current program
        otherwise
            continue execution
    :param _terminal_order:
    :return:
    """
    launch_param_set = other_program_launch_parameter_get()

    for launch_param in launch_param_set:
        # get order num
        if len(launch_param) == 2:
            order_num = 1
        elif len(launch_param) == 3:
            parse_flg, order_num = int_parse(launch_param[2])
            if not parse_flg:
                continue
        else:
            continue

        # check if the order num has already been used
        if _terminal_order == order_num:
            return False

    return True


def yaml_info_chk():
    """
        check settings.yaml and GoogleDriveResearchTool.yaml
    :return:
    """
    global yaml_checker, settings_info_dic, google_file_settings_info_dic
    yaml_checker = YamlInfoChecker.YamlInfoChecker(SETTINGS_PATH, google_file_settings_path)
    yaml_checker.exists_chk()
    settings_info_dic, google_file_settings_info_dic = yaml_checker.read()
    yaml_checker.info_chk(settings_info_dic, google_file_settings_info_dic)


def yaml_info_get():
    """
        get information
    :return:
    """
    global launch_mode, setting_tsv_path, save_tsv_path, log_level, credential_file, credential_key, \
        max_threads_projectid, max_threads_terminal, update_schedule, running_terminal_file_uri, terminal_folder_gid
    # 起動パラメータ
    launch_mode = str(google_file_settings_info_dic[YamlInfoChecker.PARAM_LAUNCH_MODE]).strip().upper()
    # 設定対象ファイルバス
    setting_tsv_path = str(google_file_settings_info_dic[YamlInfoChecker.PARAM_SET_TSV_PATH]).strip()
    # 設定結果出力バス
    save_tsv_path = output_tsv_path_get()
    # ログレベル
    log_level = google_file_settings_info_dic[YamlInfoChecker.PARAM_LOG_LEVEL]
    # すべての端末で使用可能なスレッド数と制限
    max_threads_projectid = google_file_settings_info_dic[YamlInfoChecker.PARAM_MAX_THREADS_PROJECTID]
    # 当の端末で使用可能な最大スレッド数
    max_threads_terminal = google_file_settings_info_dic[YamlInfoChecker.PARAM_MAX_THREADS_TERMINAL]
    # 「IP_X.TXT」更新計画
    update_schedule = google_file_settings_info_dic[YamlInfoChecker.PARAM_TERMINAL_FILE_UPDATE_SCHEDULE]
    # 端末ファイル(IP_X.TXT)の保存場所(Google Folder URI)
    running_terminal_file_uri = str(
        google_file_settings_info_dic[YamlInfoChecker.PARAM_RUNNING_TERMINAL_FILE_URI]).strip()
    # 端末ファイル(IP_X.TXT)の保存場所(Google Folder URI)のgid
    terminal_folder_gid = yaml_checker.get_gid(running_terminal_file_uri, True)

    # Googleｱｶｳﾝﾄ認証ﾌｧｲﾙ
    credential_file = str(settings_info_dic[YamlInfoChecker.PARAM_CREDENTIALS]).strip()
    # Googleｱｶｳﾝﾄ認証ﾌｧｲﾙ復号化キー
    credential_key = str(settings_info_dic[YamlInfoChecker.PARAM_CREDENTIALS_KEY]).strip()


def output_tsv_path_get():
    """
        get program execute result save path
    :return:
    """
    path_without_ext, ext = os.path.splitext(setting_tsv_path)
    if launch_mode == "/MODE:S":
        _output_tsv_path = path_without_ext + "_設定結果.tsv"
    else:
        _output_tsv_path = path_without_ext + "_移動結果.tsv"

    return _output_tsv_path


def google_account_and_config_info_display():
    """
        google account login user and tsv path display
    :return:
    """
    login_user_info_msg = "   %s(%s)" % (login_user["user"]["emailAddress"], login_user["user"]["displayName"])
    display(GOOGLE_ACCOUNT_INFO_MSG, login_user_info_msg)

    setting_info_tsv_msg = "   %s" % setting_tsv_path
    display(SETTING_TSV_PATH, setting_info_tsv_msg)

    save_setting_result_tsv = "   %s" % save_tsv_path
    display(SAVE_TSV_PATH, save_setting_result_tsv)

    max_threads_projectid_msg = "   %s" % max_threads_projectid
    display(MAX_THREADS_PROJECTID_MSG, max_threads_projectid_msg)

    running_terminal_file_uri_msg = "   %s" % running_terminal_file_uri
    display(RUNNING_TERMINAL_FILE_URI_MSG, running_terminal_file_uri_msg)

    max_threads_terminal_msg = "   %s" % max_threads_terminal
    display(MAX_THREADS_TERMINAL_MSG, max_threads_terminal_msg)

    terminal_file_update_schedule_msg = "   %s" % update_schedule
    display(TERMINAL_FILE_UPDATE_SCHEDULE_MSG, terminal_file_update_schedule_msg)


def display(item, value):
    print(item)
    LogHelper.info(item)
    print(value)
    LogHelper.info(value)


def init_thread_pool_and_sqlite():
    """
        init thread pool、sqlite
    :return:
    """
    global thread_pool, setting_sqlite
    thread_pool = CheckAndSetThreadPool(max_workers=thread_count)
    setting_sqlite = SettingSQLite(DB_PATH)
    setting_sqlite.init_db()


def destroy_thread_pool_and_sqlite():
    global thread_pool, setting_sqlite
    if thread_pool:
        thread_pool.close()
    if setting_sqlite:
        setting_sqlite.close()
    thread_pool = None
    setting_sqlite = None


def get_tsv_line_count():
    """
    :return:
    """
    _tsv_line_count = TsvHelper.get_tsv_lines_count(setting_tsv_path)
    tsv_line_num_msg = TSV_FILE_LINE_COUNT % (os.path.basename(setting_tsv_path), _tsv_line_count)
    print(tsv_line_num_msg)
    LogHelper.info(tsv_line_num_msg)
    print()
    return _tsv_line_count


def check_and_execute(checker, executor):
    """
        get list and execute it
    :param checker:
    :param executor:
    :return:
    """
    result = True

    # get list /MODE:S access setting list owner setting list /MODE:M folder moving list
    checker.todo_list_get()

    # list get success
    if checker.CheckResult.check_result:
        executor.todo_list_execute(save_tsv_path)
        if not executor.ExecuteResult.execute_result:
            result = False
    else:
        executor.setting_result_to_tsv(save_tsv_path)
        result = False

    return result


def permission_set():
    """
        /MODE:S
    :return:
    """
    try:
        # permission set
        checker = PermissionSettingChecker(setting_tsv_path, google_drive, setting_sqlite, thread_pool, launch_mode,
                                           threads_auto_stat)
        executor = PermissionSetter(google_drive, login_user, checker.CheckResult, setting_sqlite, thread_pool,
                                    threads_auto_stat)

        # permission set main process
        execute_result = check_and_execute(checker, executor)

        if execute_result:
            LogHelper.info(PERMISSION_SETTING_OK_END_LOG)
            print(OK_END_MSG)
        else:
            LogHelper.info(PERMISSION_SETTING_NG_END_LOG)
            print(NG_END_MSG)
    except Exception as ex1:
        LogHelper.debug(traceback.format_exc())
        raise Exception(PERMISSION_SETTING_NG_END_LOG + "\n" + ERR_LOG % ex1)


def folder_move():
    """
        /MODE:M
    :return:
    """
    try:
        # folder move
        checker = FolderMovingChecker(setting_tsv_path, google_drive, login_user, setting_sqlite, thread_pool,
                                      launch_mode, threads_auto_stat)
        executor = FolderMover(google_drive, checker, setting_sqlite, thread_pool, threads_auto_stat)

        # folder move main process
        execute_result = check_and_execute(checker, executor)

        if execute_result:
            LogHelper.info(FOLDER_MOVING_OK_END_LOG)
            print(OK_END_MSG)
        else:
            LogHelper.info(FOLDER_MOVING_NG_END_LOG)
            print(NG_END_MSG)
    except Exception as ex2:
        LogHelper.debug(traceback.format_exc())
        raise Exception(FOLDER_MOVING_NG_END_LOG + "\n" + ERR_LOG % ex2)


if __name__ == '__main__':
    """
        Program Entry
    """
    threads_auto_stat = None

    try:
        # ログの初期化
        LogHelper.logger_init()

        # 入力パラメータを取得する
        google_file_settings_path, terminal_order = launch_parameter_chk()
        pid = os.getpid()
        ppid = os.getppid()

        # 二重起動チェック
        if not is_continue_execution(terminal_order):
            print()
            print(MULTIPLE_START_NG_MSG % terminal_order)
            LogHelper.info(MULTIPLE_START_NG_MSG % terminal_order)
            exit(0)

        # 配置ファイル、Google Driveに設定Yamlファイルのチェック
        yaml_info_chk()
        yaml_info_get()

        LogHelper.set_level(log_level)

        print()

        if launch_mode == "/MODE:S":
            print(PERMISSION_SETTING_START_LOG)
            print()
            LogHelper.info(PERMISSION_SETTING_START_LOG)
        else:
            print(FOLDER_MOVING_START_LOG)
            print()
            LogHelper.info(FOLDER_MOVING_START_LOG)

        # use certify file login
        google_account_login()

        # verify terminal folder
        yaml_checker.terminal_folder_chk(running_terminal_file_uri, google_drive)

        # display user account info yaml info
        google_account_and_config_info_display()
        tsv_line_count = get_tsv_line_count()

        if tsv_line_count > 0:
            handler_uri = TsvHelper.get_first_line_uri(setting_tsv_path)

            # calculate thread count by google file
            threads_auto_stat = MaxThreadsAutoStat(google_drive, terminal_folder_gid, update_schedule,
                                                   max_threads_terminal, max_threads_projectid, terminal_order,
                                                   handler_uri)
            threads_auto_stat.init_terminal_file()

            # Verify if the handler folder is being used
            if threads_auto_stat.handler_folder_is_used():
                print()
                print(HANDLER_FOLDER_IS_USED_MSG % handler_uri)
                LogHelper.info(HANDLER_FOLDER_IS_USED_MSG % handler_uri)
                exit(0)

            thread_count = threads_auto_stat.init_thread_count()
            # initial thread pool and sqlite
            init_thread_pool_and_sqlite()

            # scheduled thread pool update
            threads_auto_stat.schedule_run(thread_pool)

            if launch_mode == "/MODE:S":
                # 権限設定
                permission_set()
            else:
                # フォルダ移動
                folder_move()
        else:
            if launch_mode == "/MODE:S":
                LogHelper.info(PERMISSION_SETTING_OK_END_LOG)
            else:
                LogHelper.info(FOLDER_MOVING_OK_END_LOG)
            print(OK_END_MSG)
    except Exception as e:
        destroy_thread_pool_and_sqlite()
        print(e)
        print(NG_END_MSG)
        LogHelper.error(e)
        LogHelper.debug(traceback.format_exc())
    finally:
        # after program end, remove the current instance terminal file
        if threads_auto_stat is not None:
            threads_auto_stat.remove_terminal_file()
