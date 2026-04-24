import os
import re

from Common.TsvItemEnum import TsvItemEnum
from Common import YamlHelper, TsvHelper, LogHelper

# SETTINGS YAML CHECK ERR
SETTINGS_NOT_EXISTS_ERR = "settings.yamlが存在しないです。"
SETTINGS_CREDENTIALS_NOT_SPECIFIED_ERR = "Googleアカウント認証ファイルありません、Googleアカウント認証ファイル作成手順を参照し作成してください"
SETTINGS_CREDENTIALS_NOT_EXISTS_ERR = "yamlファイルに設定したGoogleアカウント認証ファイルが見つかりませんでした、Googleアカウント認証ファイル作成手順を参照し作成してください"
SETTINGS_CREDENTIALS_KEY_NOT_SPECIFIED_ERR = "Googleアカウント認証ファイル復号化キーありません、Googleアカウント認証ファイル作成手順を参照し作成してください"
SETTINGS_CREDENTIALS_KEY_NOT_EXISTS_ERR = "yamlファイルに設定したGoogleアカウント認証ファイル復号化キーが見つかりませんでした、Google" \
                                          "アカウント認証ファイル作成手順を参照し作成してください "

# CONFIG YAML CHECK ERR
GOOGLE_FILE_SETTINGS_NOT_EXISTS_ERR = "設定対象の設定ファイル「GoogleDriveSettingTool.yaml」が見つからないでした。設定対象ファイルの情報を設定してください。"
LAUNCH_MODE_ERR = "処理モード(「/MODE:S」、「/MODE:M」)を指定してください。"
SET_TSV_NOT_SPECIFIED_ERR = "設定対象ファイル(SettingTsvPath)を指定してください。"
SET_TSV_SPECIFIED_ERR = "設定対象ファイル(SettingTsvPath)設定に間違いがあります。ご確認ください。"
SET_TSV_STRUCTURE_ERR = "設定対象ファイル(SettingTsvPath)の構造が不正です。"

MAX_USER_ACCOUNTS_URI_NOT_SPECIFIED_ERR = "「GoogleDriveSettingTool.yaml」に最大使用人数" \
                                          "(MaxUserAccountsURI)をご設定してください。"
MAX_USER_ACCOUNTS_URI_FORMAT_ERR = "「GoogleDriveSettingTool.yaml」に設定された最大使用人数" \
                                   "(MaxUserAccountsURI)が不正です。ご確認ください。"
MAX_USER_ACCOUNTS_URI_NOT_EXISTS = "「MaxUserAccountsURI」が存在しない。"
MAX_USER_ACCOUNTS_URI_TRASHED_ERR = "「MaxUserAccountsURI」はゴミ箱にある。"
MAX_USER_ACCOUNTS_URI_MIMETYPE_ERR = "「MaxUserAccountsURI」で指定されたファイル内容が取得できませんでした。" \
                                     "ファイル種類を「TXT」または「Googleドキュメント」に変更してください。"
MAX_USER_ACCOUNTS_URI_CONTENT_ERR = "「MaxUserAccountsURI」で指定したファイルに最大使用人数をご設定してください。"
MAX_USER_ACCOUNTS_ERR = "最大使用人数を「1」以上に設定してください。"

NETWORK_TIMEOUT_ERR = "タイムアウトが発生しました。"

TERMINAL_FOLDER_URI_NOT_SPECIFIED_ERR = "「GoogleDriveResearchTool.yaml」に「IP_X.TXT」の保存場所「RunningTerminalFile_URI」を設定してください。"
TERMINAL_FOLDER_URI_FORMAT_ERR = "「GoogleDriveResearchTool.yaml」に設定された「IP_X.TXT」の保存場所「RunningTerminalFile_URI」が不正です。ご確認ください。"
TERMINAL_FOLDER_URI_NOT_EXISTS = "「RunningTerminalFile_URI」が存在しない。"
TERMINAL_FOLDER_URI_TRASHED_ERR = "「RunningTerminalFile_URI」はゴミ箱にある。"
TERMINAL_FOLDER_URI_MIMETYPE_ERR = "「RunningTerminalFile_URI」にGoogle フォルダのURIを設定してください。"
TERMINAL_FOLDER_URI_PERMISSION_ERR = "Googleアカウントを「RunningTerminalFile_URI」の編集権限に追加してください。"

# YAML INFO GET
INFO_GET_START_LOG = "YAMLファイル設定情報を取得します"
INFO_GET_END_LOG = "YAMLファイル設定情報を取得しました"

# SETTINGS YAML PARAMETER
PARAM_CREDENTIALS = "save_credentials_file"
PARAM_CREDENTIALS_KEY = "save_credentials_privatekey_file"

# SETTINGS YAML DEFAULT VALUE
SETTINGS_DEFAULT_CREDENTIALS_FILE = "saved_credentials.json"
SETTINGS_DEFAULT_CREDENTIALS_KEY_FILE = "privatekey_saved_credentials.bin"

# YAML PARAMETER
PARAM_LAUNCH_MODE = "LaunchMode"
PARAM_SET_TSV_PATH = "SettingTsvPath"
PARAM_LOG_LEVEL = "log_level"
PARAM_MAX_THREADS_TERMINAL = "MaxThreads_Terminal"
PARAM_MAX_THREADS_PROJECTID = "MaxThreads_ProjectID"
PARAM_RUNNING_TERMINAL_FILE_URI = "RunningTerminalFile_URI"
PARAM_TERMINAL_FILE_UPDATE_SCHEDULE = "TerminalFileUpdateSchedule"

FILE_URI_CHECK_REGEX = r"^https://(drive\.google\.com/file|docs\.google\.com/document)/d/(.+)$"
FOLDER_URI_CHECK_REGEX = r"^https://drive\.google\.com/drive/(\S*)folders/(.+)$"


class YamlInfoChecker:

    def __init__(self, settings_path, google_file_settings_path):
        self.settings_path = settings_path
        self.google_file_settings_path = google_file_settings_path

    def exists_chk(self):
        """
            settings.yaml exists check
        :return:
        """
        chk_result = []
        # settings.yaml exists check
        if not YamlHelper.yaml_exists(self.settings_path):
            chk_result.append(SETTINGS_NOT_EXISTS_ERR)

        # GoogleDriveSettingTool.yaml exists check
        if not YamlHelper.yaml_exists(self.google_file_settings_path):
            chk_result.append(GOOGLE_FILE_SETTINGS_NOT_EXISTS_ERR)

        if len(chk_result):
            raise Exception("\n".join(chk_result))

    def read(self):
        """
            read settings.yaml content
        :return:
        """
        LogHelper.info(INFO_GET_START_LOG)

        settings_info_dic = YamlHelper.yaml_read(self.settings_path)
        if settings_info_dic is None:
            settings_info_dic = {}

        google_file_settings_info_dic = YamlHelper.yaml_read(self.google_file_settings_path)
        if google_file_settings_info_dic is None:
            google_file_settings_info_dic = {}

        LogHelper.info(INFO_GET_END_LOG)

        return settings_info_dic, google_file_settings_info_dic

    def info_chk(self, settings_info_dic, google_file_settings_info_dic):
        self.settings_info_chk(settings_info_dic)
        self.google_file_settings_info_chk(google_file_settings_info_dic)

    def settings_info_chk(self, settings_info_dic):
        """
            settings.yaml content check
        :param settings_info_dic:
        :return:
        """
        chk_result = []

        credentials_chk_result = self.credentials_chk(settings_info_dic)
        if credentials_chk_result is not None:
            chk_result.append(credentials_chk_result)

        secrets_chk_result = self.secrets_chk(settings_info_dic)
        if secrets_chk_result is not None:
            chk_result.append(secrets_chk_result)

        if len(chk_result):
            raise Exception("\n".join(chk_result))

    def google_file_settings_info_chk(self, google_file_settings_info_dic):
        """
            GoogleDriveSettingTool.yaml check
        :param google_file_settings_info_dic:
        :return:
        """
        chk_result = []

        # 起動パラメータ
        mode_chk_result = self.mode_chk(google_file_settings_info_dic)
        if mode_chk_result is not None:
            chk_result.append(mode_chk_result)

        # 設定対象ファイルバス
        setting_tsv_chk_result = self.setting_tsv_chk(google_file_settings_info_dic)
        if setting_tsv_chk_result is not None:
            chk_result.append(setting_tsv_chk_result)

        # すべての端末で使用可能なスレッド数と制限
        self.max_threads_projectid_chk(google_file_settings_info_dic)

        # 端末ファイル「IP_n.txt」の保存場所
        terminal_folder_uri_chk_result = self.terminal_folder_uri_chk(google_file_settings_info_dic)
        if len(terminal_folder_uri_chk_result) > 0:
            chk_result.extend(terminal_folder_uri_chk_result)

        # 自端末で使用可能な最大スレッド数
        self.max_threads_terminal_chk(google_file_settings_info_dic)

        # 「IP_n.txt」更新計画(min)
        self.terminal_file_update_schedule_chk(google_file_settings_info_dic)

        self.log_level_chk(google_file_settings_info_dic)

        if len(chk_result):
            raise Exception("\n".join(chk_result))

    def credentials_chk(self, settings_info_dic):
        """
            Googleｱｶｳﾝﾄ認証ﾌｧｲﾙ exists check
        :param settings_info_dic:
        :return:
        """
        chk_result = None
        specified = True

        if self.empty_chk(settings_info_dic, PARAM_CREDENTIALS):
            specified = False
            # default value
            settings_info_dic[PARAM_CREDENTIALS] = SETTINGS_DEFAULT_CREDENTIALS_FILE

        # exists check
        if not os.path.exists(settings_info_dic[PARAM_CREDENTIALS]):
            if specified:
                chk_result = SETTINGS_CREDENTIALS_NOT_EXISTS_ERR
            else:
                chk_result = SETTINGS_CREDENTIALS_NOT_SPECIFIED_ERR

        return chk_result

    def secrets_chk(self, settings_info_dic):
        """
            Googleｱｶｳﾝﾄ認証ﾌｧｲﾙ復号化キー  exists check
        :param settings_info_dic:
        :return:
        """
        chk_result = None
        specified = True

        if self.empty_chk(settings_info_dic, PARAM_CREDENTIALS_KEY):
            specified = False
            # default value
            settings_info_dic[PARAM_CREDENTIALS_KEY] = SETTINGS_DEFAULT_CREDENTIALS_KEY_FILE

        # exists check
        if not os.path.exists(settings_info_dic[PARAM_CREDENTIALS_KEY]):
            if specified:
                chk_result = SETTINGS_CREDENTIALS_KEY_NOT_EXISTS_ERR
            else:
                chk_result = SETTINGS_CREDENTIALS_KEY_NOT_SPECIFIED_ERR

        return chk_result

    @staticmethod
    def log_level_chk(google_file_settings_info_dic):
        """
            log level 0:info 1:debug
            default:0
        :param google_file_settings_info_dic:
        :return:
        """
        log_level = "1"
        # ログレベル
        if not google_file_settings_info_dic.__contains__(PARAM_LOG_LEVEL) \
                or google_file_settings_info_dic[PARAM_LOG_LEVEL] is None \
                or str(google_file_settings_info_dic[PARAM_LOG_LEVEL]).strip() != "1":
            log_level = "0"
        google_file_settings_info_dic[PARAM_LOG_LEVEL] = log_level

    def mode_chk(self, google_file_settings_info_dic):
        """
            first parameter check
            either '/MODE:S' or '/MODE:M'
        :param google_file_settings_info_dic:
        :return:
        """
        chk_result = None

        if self.empty_chk(google_file_settings_info_dic, PARAM_LAUNCH_MODE):
            chk_result = LAUNCH_MODE_ERR
        else:
            mode = str(google_file_settings_info_dic[PARAM_LAUNCH_MODE]).strip()
            if mode != "/MODE:S" and mode != "/MODE:M":
                chk_result = LAUNCH_MODE_ERR

        return chk_result

    def setting_tsv_chk(self, google_file_settings_info_dic):
        """
            setting tsv file check
        :param google_file_settings_info_dic:
        :return:
        """
        if self.empty_chk(google_file_settings_info_dic, PARAM_SET_TSV_PATH):
            chk_result = SET_TSV_NOT_SPECIFIED_ERR
        else:
            tsv_path = str(google_file_settings_info_dic[PARAM_SET_TSV_PATH]).strip()
            if not TsvHelper.tsv_exists(tsv_path):
                chk_result = SET_TSV_SPECIFIED_ERR
            else:
                chk_result = self.tsv_structure_chk(tsv_path)

        return chk_result

    def max_threads_terminal_chk(self, google_file_settings_info_dic):
        self.num_chk(google_file_settings_info_dic, PARAM_MAX_THREADS_TERMINAL, 32)

    def max_threads_projectid_chk(self, google_file_settings_info_dic):
        self.num_chk(google_file_settings_info_dic, PARAM_MAX_THREADS_PROJECTID, 100)

    def terminal_file_update_schedule_chk(self, google_file_settings_info_dic):
        self.num_chk(google_file_settings_info_dic, PARAM_TERMINAL_FILE_UPDATE_SCHEDULE, 30)

    def num_chk(self, google_file_settings_info_dic, chk_key, default_value):
        """
            check the number settings
        :param google_file_settings_info_dic:
        :param chk_key:
        :param default_value:
        :return:
        """
        if not google_file_settings_info_dic.__contains__(chk_key) \
                or google_file_settings_info_dic[chk_key] is None \
                or len(str(google_file_settings_info_dic[chk_key]).strip()) == 0:
            google_file_settings_info_dic[chk_key] = default_value
        else:
            value = google_file_settings_info_dic[chk_key]

            if isinstance(value, list):
                value = str(value[0]).strip()

            parse_flg, parse_value = self.int_parse(str(value).strip())
            if parse_flg and parse_value > 0:
                google_file_settings_info_dic[chk_key] = parse_value
            else:
                google_file_settings_info_dic[chk_key] = default_value

    @staticmethod
    def terminal_folder_uri_chk(google_folder_info_dic):
        """
            check the content set for [RunningTerminalFile_URI]
        :param google_folder_info_dic:
        :return:
        """
        chk_result = []
        # check format
        if not google_folder_info_dic.__contains__(PARAM_RUNNING_TERMINAL_FILE_URI) \
                or google_folder_info_dic[PARAM_RUNNING_TERMINAL_FILE_URI] is None \
                or len(str(google_folder_info_dic[PARAM_RUNNING_TERMINAL_FILE_URI]).strip()) == 0:
            # not specified
            chk_result.append(TERMINAL_FOLDER_URI_NOT_SPECIFIED_ERR)
        else:
            value = google_folder_info_dic[PARAM_RUNNING_TERMINAL_FILE_URI]
            if isinstance(value, list):
                value = value[0]
                google_folder_info_dic[PARAM_RUNNING_TERMINAL_FILE_URI] = value

            if not re.match(FOLDER_URI_CHECK_REGEX, value.strip(), re.I):
                # does not match the regular expression
                chk_result.append(TERMINAL_FOLDER_URI_FORMAT_ERR)

        return chk_result

    def terminal_folder_chk(self, folder_uri, google_drive):
        """
            check the terminal folder
        :param folder_uri:
        :param google_drive:
        :return:
        """
        gid = self.get_gid(folder_uri, True)

        try:
            file = google_drive.get_file_metadata(gid, "trashed, mimeType, permissions")

            if file["trashed"]:
                raise Exception(TERMINAL_FOLDER_URI_TRASHED_ERR)

            if file["mimeType"] != "application/vnd.google-apps.folder":
                raise Exception(TERMINAL_FOLDER_URI_MIMETYPE_ERR)

            if not file.__contains__("permissions"):
                raise Exception(TERMINAL_FOLDER_URI_PERMISSION_ERR)
        except Exception as ex:
            ex_message = ex.__str__()
            if ex_message.upper().__contains__("NOT FOUND"):
                raise Exception(TERMINAL_FOLDER_URI_NOT_EXISTS)
            elif ex_message.upper().__contains__("TIMEOUT") or ex_message.upper().__contains__("応答しなかったため"):
                raise Exception(NETWORK_TIMEOUT_ERR)
            else:
                raise Exception(ex_message)

    @staticmethod
    def int_parse(value):
        """
            convert value to integer
        :param value:
        :return:
        """
        parse_flg = True
        parse_value = -1

        try:
            parse_value = int(value)
        except ValueError:
            parse_flg = False

        return parse_flg, parse_value

    @staticmethod
    def tsv_structure_chk(tsv_path):
        """
            check the tsv file structure
        :param tsv_path:
        :return:
        """
        chk_result = None
        with open(tsv_path, 'r', encoding='UTF-8') as file:
            tsv_iterator = TsvHelper.tsv_read(file)
            fieldnames = tsv_iterator.fieldnames

        if fieldnames is None or len(fieldnames) != len(TsvItemEnum.__members__):
            chk_result = SET_TSV_STRUCTURE_ERR
        else:
            tsv_not_contain_item = list(item for item in TsvItemEnum if item.value not in fieldnames)
            if len(tsv_not_contain_item):
                chk_result = SET_TSV_STRUCTURE_ERR

        return chk_result

    @staticmethod
    def empty_chk(info_dic, item_key):
        is_empty = False
        if not info_dic.__contains__(item_key) \
                or info_dic[item_key] is None \
                or len(str(info_dic[item_key]).strip()) == 0:
            is_empty = True
        return is_empty

    @staticmethod
    def get_gid(google_uri, is_folder):
        """
            get google file id
        :param google_uri:
        :param is_folder:
        :return:
        """
        if is_folder:
            gid = re.findall(r"/folders/(.+)|$", google_uri.strip())[0]
        else:
            gid = re.findall(r'/d/(.+)|$', google_uri.strip())[0]

        if gid.__contains__("/"):
            gid = gid[: gid.index("/")]
        if gid.__contains__("?"):
            gid = gid[: gid.index("?")]
        return gid
