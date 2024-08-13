#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
from difflib import SequenceMatcher
from re import escape
from typing import Generator, Dict, List

# 此前的判断 xxx in key似乎没有生效，改用正则表达式来匹配
fix_permission = {
    r"system/app/(.*)apk": "u:object_r:system_file:s0",
    r"system/app/(.*)odex": "u:object_r:system_file:s0",
    r"system/app/(.*)vdex": "u:object_r:system_file:s0",
    r"system/priv-app/(.*)apk": "u:object_r:system_file:s0",
    r"system/priv-app/(.*)odex": "u:object_r:system_file:s0",
    r"system/priv-app/(.*)vdex": "u:object_r:system_file:s0",
    r"system/preload/(.*)apk": "u:object_r:system_file:s0",
    r"system/preload/(.*)odex": "u:object_r:system_file:s0",
    r"system/preload/(.*)vdex": "u:object_r:system_file:s0",
    r"data-app/(.*)apk": "u:object_r:system_file:s0",
    r"android\.hardware\.wifi": "u:object_r:hal_wifi_default_exec:s0",
    r"bin/idmap": "u:object_r:idmap_exec:s0",
    r"bin/fsck": "u:object_r:fsck_exec:s0",
    r"bin/e2fsck": "u:object_r:fsck_exec:s0",
    r"bin/logcat": "u:object_r:logcat_exec:s0",
    r"system/bin": "u:object_r:system_file:s0",
    r"/system/bin/init": "u:object_r:init_exec:s0",
    r"/lost\+found": "u:object_r:rootfs:s0",
}


def scan_context(file) -> Dict[str, List[str]]:  # 读取context文件返回一个字典
    context = {}
    with open(file, "r", encoding="utf-8") as file_:
        for line_number, i in enumerate(file_.readlines(), start=1):
            if not i.strip():
                print(f"[Warn] line {line_number} is empty.Skip.")
                continue
            filepath, *other = i.strip().split()
            filepath = filepath.replace(r"\@", "@")
            context[filepath] = other
            if len(other) > 1:
                print(f"[Warn] line {line_number}: {i[0]} has too much data.Skip.")
                del context[filepath]
    return context


def scan_dir(unpacked_dir: str) -> Generator:
    """扫描已经解包的镜像的目录
    param unpacked_dir: 分解得到的文件目录
    """
    part_name = os.path.basename(unpacked_dir)
    allfiles = [
        "/",
        "/lost+found",
        f"/{part_name}/lost+found",
        f"/{part_name}",
        f"/{part_name}/",
        f"/{part_name}/{part_name}",  # add for f2fs
    ]
    for root, dirs, files in os.walk(unpacked_dir, topdown=True):
        for dir_ in dirs:
            yield os.path.join(root, dir_).replace(
                unpacked_dir, "/" + part_name
            ).replace("\\", "/")
        for file in files:
            yield os.path.join(root, file).replace(
                unpacked_dir, "/" + part_name
            ).replace("\\", "/")
        for rv in allfiles:
            yield rv


def str_to_selinux(string: str):
    return escape(string).replace("\\-", "-")


def context_patch(rules_from_config: Dict[str, List[str]], dir_path: str) -> tuple:
    """修补文件上下文
    param rules_from_config: 从现有的file_contexts文件中读取的数据，键值对为文件路径:规则
    param dir_path: 实际上的文件目录（以这个为准）
    """

    def pre(i):
        # 把不可打印字符替换为*
        if not i.isprintable():
            tmp = ""
            for c in i:
                tmp += c if c.isprintable() else "*"
            i = tmp
        if " " in i:
            i = i.replace(" ", "*")
        i = str_to_selinux(i)
        return i

    new_fs = {}
    # 定义已修补过的 避免重复修补（这一步是为了什么？文件不会有重名的啊）
    r_new_fs = {}
    add_new = 0

    print(f"ContextPatcher: Load origin {len(rules_from_config.keys())} entries")

    # 定义默认SeLinux标签，处理ab分区后缀
    if "_" in os.path.basename(dir_path):
        permission_d = [
            f"u:object_r:{os.path.basename(dir_path).split('_')[0]}_file:s0"
        ]
    else:
        permission_d = [f"u:object_r:{os.path.basename(dir_path)}_file:s0"]

    # here i refers to the file path
    for i in scan_dir(os.path.abspath(dir_path)):
        # 预处理
        i = pre(i)
        if rules_from_config.get(i):
            # 如果存在直接使用默认的
            new_fs[i] = rules_from_config[i]
        else:
            permission = []
            if r_new_fs.get(i):
                continue
            # 确认i不为空
            if i:
                # 搜索已定义的权限
                for pattern, pre_permission in fix_permission.items():
                    # 使用正则表达式来匹配，找到就直接使用
                    if re.search(pattern, i):
                        permission = [pre_permission]
                        break
                # 如果没有找到，此时permission依旧为空列表
                if not permission:
                    for e in rules_from_config.keys():
                        if (
                            SequenceMatcher(
                                None, (path := os.path.dirname(i)), e
                            ).quick_ratio()
                            >= 0.75
                        ):
                            if e == path:
                                continue
                            permission = rules_from_config[e]
                            break
                        else:
                            permission = permission_d
            # permission要么有默认值，要么来自rules_from_config，无需做检查
            print(f"ADD [{i} {permission}], May Not Right")
            add_new += 1
            r_new_fs[i] = permission
            new_fs[i] = permission
    return new_fs, add_new


def main(dir_path: str, fs_config) -> None:
    new_fs, add_new = context_patch(scan_context(os.path.abspath(fs_config)), dir_path)
    with open(fs_config, "w+", encoding="utf-8", newline="\n") as f:
        f.writelines(
            [i + " " + " ".join(new_fs[i]) + "\n" for i in sorted(new_fs.keys())]
        )
    print("ContextPatcher: Add %d" % add_new + " entries")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python script.py <directory_path> <fs_config>")
    else:
        main(sys.argv[1], sys.argv[2])
