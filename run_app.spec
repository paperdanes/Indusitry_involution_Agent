# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import copy_metadata
from PyInstaller.utils.hooks import collect_submodules
import streamlit
import os
datas = []
streamlit_pkg_dir = os.path.dirname(streamlit.__file__)
datas += [
    (os.path.join(streamlit_pkg_dir, "static"),  "streamlit/static"),
    (os.path.join(streamlit_pkg_dir, "runtime"), "streamlit/runtime"),
]
project_dir = "G:\我的文件\重庆大学\小项目\Industry_involution_agent"
#datas += collect_data_files("streamlit")
datas += copy_metadata("streamlit")   ###元数据
datas += [('./app.py', '.')]

hiddenimports = collect_submodules('faiss')
hiddenimports += ["matplotlib.pyplot","matplotlib.backends.backend_agg"]
hiddenimports += collect_submodules('numpy')
hiddenimports += collect_submodules('openai')
hiddenimports += collect_submodules('openpyxl')
hiddenimports += collect_submodules('pandas')
hiddenimports += collect_submodules('pypdf')
hiddenimports += collect_submodules('docx')
hiddenimports += collect_submodules('streamlit')
hiddenimports += collect_submodules('rag')
hiddenimports += collect_submodules('utils')
hiddenimports += collect_submodules('UI_funtion')
hiddenimports += collect_submodules('funtion')

excludes=[
    "tkinter",
    "_tkinter",
]
excludes += [
    "matplotlib.backends._backend_tk",
    "matplotlib.backends.backend_tkagg",
    "matplotlib.backends.tkagg",
]
a = Analysis(
    ['run_app.py'],
    pathex=[project_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['./hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='新能源汽车行业内卷分析Agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon="logo.ico",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
