from enum import Enum


# TSV ITEM
class TsvItemEnum(Enum):
    FILE = "ファイル"
    TYPE = "種類"
    LAST_UPDATE_DATE = "最終更新年月日"
    LAST_UPDATE_TIME = "最終更新時間"
    LAST_UPDATER = "最終更新者"
    URI = "URI"
    PARENT_FOLDER = "親フォルダ"
    PARENT_URI = "親URI"
    WRITERS_CAN_SHARE = "共有設定"
    DOMAIN = "リンク設定"
    OWNER = "Owner"
    WRITER = "Editor"
    READER = "Reader"
    CHECK_RESULT = "権限ﾁｪｯｸ結果"
    SETTING_RESULT = "権限設定結果"
    ERR_INFO = "ErrInfo"
