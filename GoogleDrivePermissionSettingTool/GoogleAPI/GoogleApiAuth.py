import json
import traceback

from google.oauth2.credentials import Credentials
from Common import LogHelper
from GoogleAPI.Decryption import DecryptFile

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']

DECRYPT_ERR = "Googleアカウント認証ファイルの復号化が失敗しました。Googleアカウント認証ファイル作成手順を参照し再作成してください"


class GoogleApiAuth:

    def __init__(self, certify_file, key_file):
        """
            google drive login files,
            using key decrypt secrets/credentials file
        :param certify_file:
        :param key_file:
        """
        self.certify_file = certify_file
        self.key_file = key_file

    def login(self):
        """
            login google account
        :return:
        """
        return self.load_credentials()

    def load_credentials(self):
        """
            read google account certify file
        :param self:
        :return:
        """
        try:
            decrypt_content = DecryptFile.decrypt(self.certify_file, self.key_file)
        except Exception:
            LogHelper.debug(traceback.format_exc())
            raise Exception(DECRYPT_ERR)

        json_credentials = json.loads(decrypt_content)
        credentials = Credentials.from_authorized_user_info(json_credentials, SCOPES)
        return credentials
