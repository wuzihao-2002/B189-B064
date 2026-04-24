# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['GoogleDrivePermissionSettingTool.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('AuthenticationConfig', 'AuthenticationConfig'),
    ],
    hiddenimports=[
        'google.auth.transport.requests',
        'google.oauth2.credentials',
        'google.oauth2.service_account',
        'googleapiclient.discovery',
        'googleapiclient.errors',
        'googleapiclient.http',
        'psutil',
        'rsa',
        'yaml',
        'sqlite3',
        'threading',
        'concurrent.futures',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GoogleDrivePermissionSettingTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
