import os
import platform
import shutil
import zipfile

from src import banner

print(f'\033[31m {banner.banner1} \033[0m')
print(f'Build for {platform.system()}')
from pip._internal.cli.main import main as _main

with open('requirements.txt', 'r', encoding='utf-8') as l:
    for i in l.read().split("\n"):
        print(f"Installing {i}")
        _main(['install', i])
local = os.getcwd()
if platform.system() == 'Linux':
    name = 'TIK-linux.zip'
else:
    name = 'TIK-win.zip'


def zip_folder(folder_path):
    # 获取文件夹的绝对路径和文件夹名称
    abs_folder_path = os.path.abspath(folder_path)

    # 创建一个同名的zip文件
    zip_file_path = os.path.join(local, name)
    archive = zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED)

    # 遍历文件夹中的所有文件和子文件夹
    for root, dirs, files in os.walk(abs_folder_path):
        for file in files:
            if file == name:
                continue
            if file.endswith(".py") or file.endswith(".ico") or file.endswith(".txt"):
                continue
            file_path = os.path.join(root, file)
            if ".git" in file_path:
                continue
            print(f"Adding: {file_path}")
            # 将文件添加到zip文件中
            archive.write(file_path, os.path.relpath(file_path, abs_folder_path))

    # 关闭zip文件
    archive.close()
    print(f"Done!")


import PyInstaller.__main__

PyInstaller.__main__.run(['-F', 'run.py', '--exclude-module=numpy', '-i', 'icon.ico'])

if os.name == 'nt':
    if os.path.exists(local + "/dist/run.exe"):
        shutil.move(local + "/dist/run.exe", local)
    if os.path.exists(local + "/bin/Linux"):
        shutil.rmtree(local + "/bin/Linux")
    if os.path.exists(local + "/bin/Android"):
        shutil.rmtree(local + "/bin/Android")
    if os.path.exists(local + "/bin/Darwin"):
        shutil.rmtree(local + "/bin/Darwin")
elif os.name == 'posix':
    if os.path.exists(local + "/dist/run"):
        shutil.move(local + "/dist/run", local)
    if os.path.exists(local + "/bin/Windows"):
        shutil.rmtree(local + "/bin/Windows")
    for i in os.listdir(local + "/bin/Linux"):
        if i == platform.machine():
            continue
        shutil.rmtree(local + "/bin/Linux/" + i)
for i in os.listdir(local):
    if i not in ['run', 'run.exe', 'bin', 'LICENSE'] and not i.endswith(".py") and not i.endswith(".ico") and not i.endswith(".txt"):
        print(f"Removing {i}")
        if os.path.isdir(local + os.sep + i):
            try:
                shutil.rmtree(local + os.sep + i)
            except Exception or OSError as e:
                print(e)
        elif os.path.isfile(local + os.sep + i):
            try:
                os.remove(local + os.sep + i)
            except Exception or OSError as e:
                print(e)
    else:
        print(i)
if os.name == 'posix':
    for root, dirs, files in os.walk(local, topdown=True):
        for i in files:
            print(f"Chmod {os.path.join(root, i)}")
            os.system(f"chmod a+x {os.path.join(root, i)}")

zip_folder(".")
