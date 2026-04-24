import base64
import rsa

PRIVATE = "PRIVATE"


def decrypt(encrypt_file, key_file):
    """
        using key_file decrypt encrypt_file
    :param encrypt_file:
    :param key_file:
    :return:
    """
    key_content = key_decrypt(key_file, PRIVATE)
    return rsa_long_decrypt(encrypt_file, key_content)


def key_decrypt(key_file, key_type):
    """
        rsa key decrypt
    :param key_file:
    :param key_type:
    :return:
    """
    key_content = binary2str(key_file)
    lines = key_content.split("\n")
    key_content = ""

    for line in lines:
        if line.strip() == "" or line == "-----BEGIN RSA " + key_type + " KEY-----" \
                or line == "-----END RSA " + key_type + " KEY-----":
            key_content += line + "\n"
            continue
        reverse_value = list(line[:: -1])
        if len(line) > 1:
            reverse_value.pop(1)
            reverse_value.pop(len(reverse_value) - 2)
        key_content += "".join(reverse_value) + "\n"

    key_content = key_content.encode()

    return key_content


def rsa_long_decrypt(encrypt_file, key_content):
    """
        decrypt file
    :param encrypt_file:
    :param key_content:
    :return:
    """
    decrypt_content = b''
    decrypt_key_content = rsa.PrivateKey.load_pkcs1(key_content)

    encrypt_file = base64.b64decode(open(encrypt_file, 'rb').read())
    divide = int(len(encrypt_file) / 256)
    divide = divide if (divide > 0) else divide + 1
    line = divide if (len(encrypt_file) % 256 == 0) else divide + 1

    for i in range(line):
        decrypt_content += rsa.decrypt(encrypt_file[i * 256: (i + 1) * 256], decrypt_key_content)

    decrypt_content = decrypt_content.decode()

    return decrypt_content


def binary2str(bin_content):
    """
        convert binary to string
    :param bin_content: 
    :return: 
    """
    content = open(bin_content, 'rb')
    content = base64.b64decode(content.read()).decode()
    str_content = ''.join([chr(i) for i in [int(b, 2) for b in content.split(' ')]])
    return str_content
