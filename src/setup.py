import os
from cx_Freeze import setup, Executable

src_dir = os.path.dirname(os.path.abspath(__file__))
build_dir = "build/SteamShine"

zip_include_packages = ['PyQt6']

include_files = [
    os.path.join(src_dir, 'icons/'),
    #os.path.join(src_dir, 'dependencies/'),
]

build_exe_options = {
    "include_files": include_files,
    "build_exe": build_dir,
    "zip_include_packages": zip_include_packages,
    "excludes": ["tkinter"],
}

executables = [
    Executable(os.path.join(src_dir, 'steamshine.py'), base=None, icon=os.path.join(src_dir, "icons/icon.ico"), target_name="SteamShine")
]


setup(
    name='SteamShine',
    version='1.0',
    options={"build_exe": build_exe_options},
    executables=executables,
)
