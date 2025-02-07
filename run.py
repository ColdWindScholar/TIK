#!/usr/bin/env python
import hashlib
import json
import platform as plat
import re
import shutil
import subprocess
import sys
import time
import zipfile
from argparse import Namespace
from configparser import ConfigParser
from io import BytesIO
from os import path as o_path
from src import banner
from src import ext4
from src.Magisk import Magisk_patch
import os

from src.dumper import Dumper

if os.name == 'nt':
    import ctypes

    ctypes.windll.kernel32.SetConsoleTitleW("TIK5_Alpha")
else:
    sys.stdout.write("\x1b]2;TIK5_Alpha\x07")
    sys.stdout.flush()
import extract_dtb
import requests
from rich.progress import track
from src import contextpatch
from src import downloader
from src import fspatch
from src import imgextractor
from src import lpunpack
from src import mkdtboimg
from src import ofp_mtk_decrypt
from src import ofp_qc_decrypt
from src import ozipdecrypt
from src import utils
from src.api import cls, dir_has, cat, dirsize, re_folder, f_remove
from src.log import LOGS, LOGE, ysuc, yecho, ywarn
from src.utils import gettype, simg2img, call
from src import opscrypto
from src import zip2mpk
from rich.table import Table
from rich.console import Console

LOCALDIR = os.getcwd()
binner = o_path.join(LOCALDIR, "bin")
setfile = o_path.join(LOCALDIR, "bin", "settings.json")
platform = plat.machine()
ostype = plat.system()
if os.getenv('PREFIX'):
    if os.getenv('PREFIX') == "/data/data/com.termux/files/usr":
        ostype = 'Android'
ebinner = o_path.join(binner, ostype, platform) + os.sep
temp = o_path.join(binner, 'temp')


class json_edit:
    def __init__(self, j_f):
        self.file = j_f

    def read(self):
        if not os.path.exists(self.file):
            return {}
        with open(self.file, 'r+', encoding='utf-8') as pf:
            try:
                return json.loads(pf.read())
            except (Exception, BaseException):
                return {}

    def write(self, data):
        with open(self.file, 'w+', encoding='utf-8') as pf:
            json.dump(data, pf, indent=4)

    def edit(self, name, value):
        data = self.read()
        data[name] = value
        self.write(data)


def rmdire(path):
    if o_path.exists(path):
        if os.name == 'nt':
            for r, d, f in os.walk(path):
                for i in d:
                    if i.endswith('.'):
                        call(['mv', str(os.path.join(r, i)), str(os.path.join(r, i[:1]))])
                for i in f:
                    if i.endswith('.'):
                        call(['mv', os.path.join(r, i), os.path.join(r, i[:1])])
        try:
            shutil.rmtree(path)
        except PermissionError:
            ywarn("无法删除文件夹，权限不足")
        else:
            ysuc("删除成功！")


def error(exception_type, exception, traceback):
    cls()
    table = Table()
    try:
        version = settings.version
    except:
        version = 'Unknown'
    table.add_column(f'[red]ERROR:{exception_type.__name__}[/]', justify="center")
    table.add_row(f'[yellow]Describe:{exception}')
    table.add_row(
        f'[yellow]Lines:{exception.__traceback__.tb_lineno}\tModule:{exception.__traceback__.tb_frame.f_globals["__name__"]}')
    table.add_section()
    table.add_row(
        f'[blue]Platform:[purple]{plat.machine()}\t[blue]System:[purple]{plat.uname().system} {plat.uname().release}')
    table.add_row(f'[blue]Python:[purple]{sys.version[:6]}\t[blue]Tool Version:[purple]{version}')
    table.add_section()
    table.add_row(f'[green]Report:https://github.com/ColdWindScholar/TIK/issues')
    Console().print(table)
    input()
    sys.exit(1)


# sys.excepthook = error


def sha1(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            return hashlib.sha1(f.read()).hexdigest()
    else:
        return ''


if not os.path.exists(ebinner):
    raise Exception("Binary not found\nMay Not Support Your Device?")
try:
    if os.path.basename(sys.argv[0]) == f'run_new{str() if os.name == "posix" else ".exe"}':
        os.remove(os.path.join(LOCALDIR, f'run{str() if os.name == "posix" else ".exe"}'))
        shutil.copyfile(os.path.join(LOCALDIR, f'run_new{str() if os.name == "posix" else ".exe"}'),
                        os.path.join(LOCALDIR, f'run{str() if os.name == "posix" else ".exe"}'))
    elif os.path.basename(sys.argv[0]) == f'run{str() if os.name == "posix" else ".exe"}':
        new = os.path.join(LOCALDIR, f'run_new{str() if os.name == "posix" else ".exe"}')
        if os.path.exists(new):
            if sha1(os.path.join(LOCALDIR, f'run{str() if os.name == "posix" else ".exe"}')) == sha1(new):
                os.remove(new)
            else:
                subprocess.Popen([new])
                sys.exit()
except (Exception, BaseException):
    ...


class set_utils:
    def __init__(self, path):
        self.path = path

    def load_set(self):
        with open(self.path, 'r') as ss:
            data = json.load(ss)
            [setattr(self, v, data[v]) for v in data]

    def change(self, name, value):
        with open(self.path, 'r') as ss:
            data = json.load(ss)
        with open(self.path, 'w', encoding='utf-8') as ss:
            data[name] = value
            json.dump(data, ss, ensure_ascii=False, indent=4)
        self.load_set()


settings = set_utils(setfile)
settings.load_set()


class upgrade:
    update_json = 'https://mirror.ghproxy.com/https://raw.githubusercontent.com/ColdWindScholar/Upgrade/main/TIK.json'

    def __init__(self):
        if not os.path.exists(temp):
            os.makedirs(temp)
        cls()
        with Console().status(f"[blue]正在检测新版本...[/]"):
            try:
                data = requests.get(self.update_json).json()
            except (Exception, BaseException):
                data = None
        if not data:
            input("连接服务器失败, 按任意按钮返回")
            return
        else:
            if data.get('version', settings.version) != settings.version:
                print(f'\033[31m {banner.banner1} \033[0m')
                print(
                    f"\033[0;32;40m发现版本：\033[0m\033[0;36;40m{settings.version} --> {data.get('version')}\033[0m")
                print(f"\033[0;32;40m更新日志：\n\033[0m\033[0;36;40m{data.get('log', '1.Fix Some Bugs')}\033[0m")
                input("注意，交流群与release中的构建始终为最新开发环境版本，本功能仅用于检测近期较为稳定的构建")
                try:
                    link = data['link'][plat.system()][plat.machine()]
                except (Exception, BaseException):
                    input("未发现适用于您设备的更新，请前往https://github.com/ColdWindScholar/TIK下载源代码自行更新")
                    return
                if not link:
                    input("未发现适用于您设备的更新，请前往https://github.com/ColdWindScholar/TIK下载源代码自行更新")
                    return
                if input("\033[0;33;40m是否更新?[1/0]\033[0m") == '1':
                    print("正在下载新版本...")
                    try:
                        downloader.download([link], temp)
                    except (BaseException, Exception):
                        input("下载错误，请稍后重试")
                        return
                    print("开始更新，请不要关闭工具...")
                    upgrade_pkg = os.path.join(temp, os.path.basename(link))
                    extract_path = os.path.join(temp, 'update')
                    if os.path.exists(extract_path):
                        rmdire(extract_path)
                    try:
                        zipfile.ZipFile(upgrade_pkg).extractall(extract_path)
                    except (Exception, BaseException):
                        input("更新文件损坏， 无法更新")
                        return
                    self.settings = json_edit(setfile).read()
                    json2 = json_edit(os.path.join(extract_path, 'bin', 'settings.json')).read()
                    for i in self.settings.keys():
                        json2[i] = self.settings.get(i, json2.get(i, ''))
                    json2['version'] = data.get('version', settings.version)
                    self.settings = json2
                    shutil.copytree(os.path.join(extract_path, 'bin'), os.path.join(LOCALDIR, 'bin2'),
                                    dirs_exist_ok=True)
                    shutil.move(os.path.join(extract_path, f'run{str() if os.name == "posix" else ".exe"}'),
                                os.path.join(LOCALDIR, f'run_new{str() if os.name == "posix" else ".exe"}'))
                    shutil.rmtree(os.path.join(LOCALDIR, 'bin'))
                    shutil.copytree(os.path.join(LOCALDIR, 'bin2'), os.path.join(LOCALDIR, 'bin'))
                    shutil.rmtree(os.path.join(LOCALDIR, 'bin2'))
                    json_edit(setfile).write(json2)
                    input("更新完毕, 任意按钮启动新程序...")
                    subprocess.Popen([os.path.join(LOCALDIR, f'run_new{str() if os.name == "posix" else ".exe"}')])
                    sys.exit()
            else:
                input("\033[0;32;40m你正在使用最新版本！任意按钮返回！\033[0m")
                return


class setting:
    def settings1(self):
        actions = {
            "1": lambda: settings.change('brcom', brcom if (brcom := input(
                f"  调整brotli压缩等级(整数1-9，级别越高，压缩率越大，耗时越长):")).isdigit() and 0 < int(
                brcom) < 10 else '1'),
            "2": lambda: settings.change('diysize',
                                         "1" if input("  打包Ext镜像大小[1]动态最小 [2]原大小:") == '2' else ''),
            "3": lambda: settings.change('pack_e2', '0' if input(
                "  打包方案: [1]make_ext4fs [2]mke2fs+e2fsdroid:") == '1' else '1'),
            "6": lambda: settings.change('pack_sparse', '1' if input(
                "  Img是否打包为sparse镜像(压缩体积)[1/0]\n  请输入序号:") == '1' else "0"),
            "7": lambda: settings.change('diyimgtype',
                                         '1' if input(f"  打包镜像系统[1]同解包格式 [2]可选择:") == '2' else ''),
            "8": lambda: settings.change('erofs_old_kernel',
                                         '1' if input(f"  EROFS打包是否支持旧内核[1/0]") == '1' else '0')
        }
        cls()
        print(f'''
        \033[33m  > 打包设置 \033[0m
           1> Brotli 压缩等级 \033[93m[{settings.brcom}]\033[0m\n
           ----[EXT4设置]------
           2> 大小处理 \033[93m[{settings.diysize}]\033[0m
           3> 打包方式 \033[93m[{settings.pack_e2}]\033[0m\n
           ----[EROFS设置]-----
           4> 压缩方式 \033[93m[{settings.erofslim}]\033[0m\n
           ----[IMG设置]-------
           5> UTC时间戳 \033[93m[{settings.utcstamp}]\033[0m
           6> 创建sparse \033[93m[{settings.pack_sparse}]\033[0m
           7> 文件系统 \033[93m[{settings.diyimgtype}]\033[0m
           8> 支持旧内核 \033[93m[{settings.erofs_old_kernel}]\033[0m\n
           0>返回上一级菜单
           --------------------------
        ''')
        op_pro = input("   请输入编号:")
        if op_pro == "0":
            return
        elif op_pro in actions.keys():
            actions[op_pro]()
        elif op_pro == '4':
            if input("  选择erofs压缩方式[1]是 [2]否:") == '1':
                erofslim = input(
                    "  选择erofs压缩方式：lz4/lz4hc/lzma/和压缩等级[1-9](数字越大耗时更长体积更小) 例如 lz4hc,8:")
                settings.change("erofslim", erofslim if erofslim else 'lz4hc,8')
            else:
                settings.change("erofslim", 'lz4hc,8')
        elif op_pro == '5':
            if input("  设置打包UTC时间戳[1]自动 [2]自定义:") == "2":
                utcstamp = input("  请输入: ")
                settings.change('utcstamp', utcstamp if utcstamp.isdigit() else '1717840117')
            else:
                settings.change('utcstamp', '')
        else:
            print("Input error!")
        self.settings1()

    def settings2(self):
        cls()
        actions = {
            '1': lambda: settings.change('super_group', super_group if (
                super_group := input(f"  请输入（无特殊字符）:")) else "qti_dynamic_partitions"),
            '2': lambda: settings.change('metadatasize', metadatasize if (
                metadatasize := input("  设置metadata最大保留size(默认为65536，至少512):")) else '65536'),
            '3': lambda: settings.change('BLOCKSIZE', BLOCKSIZE if (
                BLOCKSIZE := input(f"  分区打包扇区/块大小：{settings.BLOCKSIZE}\n  请输入: ")) else "4096"),
            '4': lambda: settings.change('BLOCKSIZE', SBLOCKSIZE if (
                SBLOCKSIZE := input(f"  分区打包扇区/块大小：{settings.SBLOCKSIZE}\n  请输入: ")) else "4096"),
            '5': lambda: settings.change('supername', supername if (supername := input(
                f'  当前动态分区物理分区名(默认super)：{settings.supername}\n  请输入（无特殊字符）: ')) else "super"),
            '6': lambda: settings.change('fullsuper', '' if input("  是否强制创建Super镜像？[1/0]") != '1' else '-F'),
            '7': lambda: settings.change('autoslotsuffixing',
                                         '' if input("  是否标记需要Slot后缀的分区？[1/0]") != '1' else '-x')
        }
        print(f'''
        \033[33m  > 动态分区设置 \033[0m
           1> Super簇名 \033[93m[{settings.super_group}]\033[0m\n
           ----[Metadata设置]--
           2> 最大保留Size \033[93m[{settings.metadatasize}]\033[0m\n
           ----[分区设置]------
           3> 默认扇区/块大小 \033[93m[{settings.BLOCKSIZE}]\033[0m\n
           ----[Super设置]-----
           4> 指定block大小 \033[93m[{settings.SBLOCKSIZE}]\033[0m
           5> 更改物理分区名 \033[93m[{settings.supername}]\033[0m
           6> 强制生成完整Img \033[93m[{settings.fullsuper}]\033[0m
           7> 标记分区槽后缀 \033[93m[{settings.autoslotsuffixing}]\033[0m\n
           0>返回上一级菜单
           --------------------------
        ''')
        op_pro = input("   请输入编号: ")
        if op_pro == "0":
            return
        elif op_pro in actions.keys():
            actions[op_pro]()
        else:
            ywarn("Input error!")
        self.settings2()

    def settings3(self):
        cls()
        print(f'''
    \033[33m  > 工具设置 \033[0m\n
       1>自定义首页banner \033[93m[{settings.banner}]\033[0m\n
       2>联网模式 \033[93m[{settings.online}]\033[0m\n
       3>Contexts修补 \033[93m[{settings.context}]\033[0m\n
       4>检查更新 \n
       0>返回上级\n
       --------------------------
            ''')
        op_pro = input("   请输入编号: ")
        if op_pro == "0":
            return
        elif op_pro == '1':
            print(f"  首页banner: [1]TIK5 [2]镰刀斧头 [3]TIK2 [4]原神 [5]DXY [6]None")
            banner_i = input("  请输入序号: ")
            if banner_i.isdigit():
                if 0 < int(banner_i) < 7:
                    settings.change('banner', banner_i)
        elif op_pro == '2':
            settings.change('online', 'false' if settings.online == 'true' else 'true')
        elif op_pro == '3':
            settings.change('context', 'false' if settings.context == 'true' else 'true')
        elif op_pro == '4':
            upgrade()
        self.settings3()

    @staticmethod
    def settings4():
        cls()
        print(f'\033[31m {banner.banner1} \033[0m')
        print('\033[96m 开源的安卓全版本ROM处理工具\033[0m')
        print('\033[31m---------------------------------\033[0m')
        print(f"\033[93m作者:\033[0m \033[92mColdWindScholar\033[0m")
        print(f"\033[93m开源地址:\033[0m \033[91mhttps://github.com/ColdWindScholar/TIK\033[0m")
        print(f"\033[93m软件版本:\033[0m \033[44mAlpha Edition\033[0m")
        print(f"\033[93m开源协议:\033[0m \033[68mGNU General Public License v3.0 \033[0m")
        print('\033[31m---------------------------------\033[0m')
        print(f"\033[93m特别鸣谢:\033[0m")
        print('\033[94mAffggh')
        print("Yeliqin666")
        print('YukongA')
        print("\033[0m")
        input('\033[31m---------------------------------\033[0m')

    def __init__(self):
        cls()
        print('''
    \033[33m  > 设置 \033[0m
       1>[打包]相关设置\n
       2>[动态分区]相关设置\n
       3>工具设置\n
       4>关于工具\n
       0>返回主页
       --------------------------
    ''')
        op_pro = input("   请输入编号: ")
        if op_pro == "0":
            return
        try:
            getattr(self, 'settings%s' % op_pro)()
            self.__init__()
        except AttributeError as e:
            print(f"Input error!{e}")
            self.__init__()


def plug_parse(js_on):
    class parse:
        gavs = {}

        def __init__(self, jsons):
            self.value = []
            print("""
    ------------------
    MIO-PACKAGE-PARSER
    ------------------
                  """)
            with open(jsons, 'r', encoding='UTF-8') as f:
                try:
                    data_ = json.load(f)
                except Exception as e:
                    ywarn("解析错误 %s" % e)
                    return
                plugin_title = data_['main']['info']['title']
                print("----------" + plugin_title + "----------")
                for group_name, group_data in data_['main'].items():
                    if group_name != "info":
                        for con in group_data['controls']:
                            if 'set' in con:
                                self.value.append(con['set'])
                            if con["type"] == "text":
                                if con['text'] != plugin_title:
                                    print("----------" + con['text'] + "----------")
                            elif con["type"] == "filechose":
                                file_var_name = con['set']
                                ysuc("请在下方拖入文件或输入路径")
                                self.gavs[file_var_name] = input(con['text'])
                            elif con["type"] == "radio":
                                gavs = {}
                                radio_var_name = con['set']
                                options = con['opins'].split()
                                cs = 0
                                print("-------选项---------")
                                for option in options:
                                    cs += 1
                                    text, value = option.split('|')
                                    self.gavs[radio_var_name] = value
                                    print(f"[{cs}] {text}")
                                    gavs[str(cs)] = value
                                print("---------------------------")
                                op_in = input("请输入您的选择:")
                                self.gavs[radio_var_name] = gavs[op_in] if op_in in gavs.keys() else gavs["1"]
                            elif con["type"] == 'input':
                                input_var_name = con['set']
                                if 'text' in con:
                                    print(con['text'])
                                self.gavs[input_var_name] = input("请输入一个值:")
                            elif con['type'] == 'checkbutton':
                                b_var_name = con['set']
                                text = 'M.K.C' if 'text' not in con else con['text']
                                self.gavs[b_var_name] = 1 if input(text + "[1/0]:") == '1' else 0
                            else:
                                print("不支持的解析:%s" % con['type'])

    data = parse(js_on)
    return data.gavs, data.value


class Tool:
    """
    Free Android Rom Tool
    """

    def __init__(self):
        self.pro = None

    def main(self):
        projects = {}
        pro = 0
        cls()
        if settings.banner != "6":
            print(f'\033[31m {getattr(banner, "banner%s" % settings.banner)} \033[0m')
        else:
            print("=" * 50)
        print("\033[93;44m Alpha Edition \033[0m")
        if settings.online == 'true':
            try:
                content = json.loads(requests.get('https://v1.jinrishici.com/all.json', timeout=2).content.decode())
                shiju = content['content']
                fr = content['origin']
                another = content['author']
            except (Exception, BaseException):
                print(f"\033[36m “开源，是一场无问西东的前行”\033[0m\n")
            else:
                print(f"\033[36m “{shiju}”")
                print(f"\033[36m---{another}《{fr}》\033[0m\n")
        else:
            print(f"\033[36m “开源，是一场无问西东的前行”")
        print(" >\033[33m 项目列表 \033[0m\n")
        print("\033[31m   [00]  删除项目\033[0m\n\n", "  [0]  新建项目\n")
        for pros in os.listdir(LOCALDIR):
            if pros == 'bin' or pros.startswith('.'):
                continue
            if os.path.isdir(o_path.join(LOCALDIR, pros)):
                pro += 1
                print(f"   [{pro}]  {pros}\n")
                projects[str(pro)] = pros
        print("  --------------------------------------")
        print("\033[33m  [55] 解压  [66] 退出  [77] 设置  [88] 下载ROM\033[0m\n")
        op_pro = input("  请输入序号：")
        if op_pro == '55':
            self.unpackrom()
        elif op_pro == '88':
            url = input("输入下载链接:")
            if url:
                try:
                    downloader.download([url], LOCALDIR)
                except (Exception, BaseException):
                    ...
                self.unpackrom()
        elif op_pro == '00':
            op_pro = input("  请输入你要删除的项目序号:")
            op_pro = op_pro.split() if " " in op_pro else [op_pro]
            for op in op_pro:
                if op in projects.keys():
                    if input(f"  确认删除{projects[op]}？[1/0]") == '1':
                        rmdire(o_path.join(LOCALDIR, projects[op]))
                    else:
                        ywarn("取消删除")
        elif op_pro == '0':
            projec = input("请输入项目名称(非中文)：")
            if projec:
                if os.path.exists(o_path.join(LOCALDIR, projec)):
                    projec = f'{projec}_{time.strftime("%m%d%H%M%S")}'
                    ywarn(f"项目已存在！自动命名为：{projec}")
                    time.sleep(1)
                os.makedirs(o_path.join(LOCALDIR, projec, "config"))
                self.pro = projec
                self.project()
            else:
                ywarn("  Input error!")
                input("任意按钮继续")
        elif op_pro == '66':
            cls()
            ysuc("\n感谢使用TI-KITCHEN5,再见！")
            sys.exit(0)
        elif op_pro == '77':
            setting()
        elif op_pro.isdigit():
            if op_pro in projects.keys():
                self.pro = projects[op_pro]
                self.project()
            else:
                ywarn("  Input error!")
                input("任意按钮继续")
        else:
            ywarn("  Input error!")
            input("任意按钮继续")
        self.main()

    @staticmethod
    def dis_avb(fstab):
        print(f"正在处理: {fstab}")
        if not os.path.exists(fstab):
            return
        with open(fstab, "r") as sf:
            details = sf.read()
        if not re.search(",avb=vbmeta_system", details):
            # it may be "system /system erofs ro avb=vbmeta_system,..."
            details = re.sub("avb=vbmeta_system,", "", details)
        else:
            details = re.sub(",avb=vbmeta_system", ",", details)
        if not re.search(",avb", details):
            # it may be "product /product ext4 ro avb,..."
            details = re.sub("avb,", "", details)
        else:
            details = re.sub(",avb", "", details)
        details = re.sub(",avb_keys=.*avbpubkey", "", details)
        details = re.sub(",avb=vbmeta_vendor", "", details)
        details = re.sub(",avb=vbmeta", "", details)
        with open(fstab, "w") as tf:
            tf.write(details)

    @staticmethod
    def dis_data_encryption(fstab):
        print(f"正在处理: {fstab}")
        if not os.path.exists(fstab):
            return
        with open(fstab, "r") as sf:
            details = re.sub(",fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized+wrappedkey_v0", "",
                             sf.read())
        details = re.sub(",fileencryption=aes-256-xts:aes-256-cts:v2+emmc_optimized+wrappedkey_v0", ",", details)
        details = re.sub(",fileencryption=aes-256-xts:aes-256-cts:v2", "", details)
        details = re.sub(",metadata_encryption=aes-256-xts:wrappedkey_v0", "", details)
        details = re.sub(",fileencryption=aes-256-xts:wrappedkey_v0", "", details)
        details = re.sub(",metadata_encryption=aes-256-xts", "", details)
        details = re.sub(",fileencryption=aes-256-xts", "", details)
        details = re.sub(",fileencryption=ice", "", details)
        details = re.sub('fileencryption', 'encryptable', details)
        with open(fstab, "w") as tf:
            tf.write(details)

    def project(self):
        project_dir = LOCALDIR + os.sep + self.pro
        cls()
        os.chdir(project_dir)
        print(" \n\033[31m>项目菜单 \033[0m\n")
        print(f"  项目：{self.pro}\033[91m(不完整)\033[0m\n") if not os.path.exists(
            os.path.abspath('config')) else print(
            f"  项目：{self.pro}\n")
        if not os.path.exists(project_dir + os.sep + 'TI_out'):
            os.makedirs(project_dir + os.sep + 'TI_out')
        print('\033[33m    0> 回到主页     2> 解包菜单\033[0m\n')
        print('\033[36m    3> 打包菜单     4> 插件菜单\033[0m\n')
        print('\033[32m    5> 一键封装     6> 定制功能\033[0m\n')
        op_menu = input("    请输入编号: ")
        if op_menu == '0':
            os.chdir(LOCALDIR)
            return
        elif op_menu == '2':
            unpack_choo(project_dir)
        elif op_menu == '3':
            packChoo(project_dir)
        elif op_menu == '4':
            subbed(project_dir)
        elif op_menu == '5':
            self.hczip()
        elif op_menu == '6':
            self.custom_rom()
        else:
            ywarn('   Input error!')
            input("任意按钮继续")
        self.project()

    def custom_rom(self):
        cls()
        print(" \033[31m>定制菜单 \033[0m\n")
        print(f"  项目：{self.pro}\n")
        print('\033[33m    0> 返回上级  1> 面具修补\033[0m\n')
        print('\033[33m    2> 去除avb   3> 去除data加密\033[0m\n')
        op_menu = input("    请输入编号: ")
        if op_menu == '0':
            return
        elif op_menu == '1':
            self.magisk_patch()
        elif op_menu == '2':
            for root, dirs, files in os.walk(LOCALDIR + os.sep + self.pro):
                for file in files:
                    if file.startswith("fstab."):
                        self.dis_avb(os.path.join(root, file))
        elif op_menu == '3':
            for root, dirs, files in os.walk(LOCALDIR + os.sep + self.pro):
                for file in files:
                    if file.startswith("fstab."):
                        self.dis_data_encryption(os.path.join(root, file))
        else:
            ywarn('   Input error!')
        input("任意按钮继续")
        self.custom_rom()

    def magisk_patch(self):
        cls()
        cs = 0
        project = LOCALDIR + os.sep + self.pro
        os.chdir(LOCALDIR)
        print(" \n\033[31m>面具修补 \033[0m\n")
        print(f"  项目：{self.pro}\n")
        print(f"  请将要修补的镜像放入{project}")
        boots = {}
        for i in os.listdir(project):
            if os.path.isdir(os.path.join(project, i)):
                continue
            if gettype(os.path.join(project, i)) in ['boot', 'vendor_boot']:
                cs += 1
                boots[str(cs)] = os.path.join(project, i)
                print(f'  [{cs}]--{i}')
        print("\033[33m-------------------------------\033[0m")
        print("\033[33m    [00] 返回\033[0m\n")
        op_menu = input("    请输入编号: ")
        if op_menu in boots.keys():
            mapk = input("    请输入Magisk.apk路径:")
            if not os.path.isfile(mapk):
                ywarn('Input Error!')
            else:
                patch = Magisk_patch(boots[op_menu], '', MAGISAPK=mapk)
                patch.auto_patch()
                if os.path.exists(os.path.join(LOCALDIR, 'new-boot.img')):
                    out = os.path.join(project, "boot_patched.img")
                    shutil.move(os.path.join(LOCALDIR, 'new-boot.img'), out)
                    LOGS(f"Moved to:{out}")
                    LOGS("修补完成")
                else:
                    LOGE("修补失败")
        elif op_menu == '00':
            os.chdir(project)
            return
        else:
            ywarn('Input Error!')
        input("任意按钮继续")
        self.magisk_patch()

    def hczip(self):
        cls()
        project = LOCALDIR + os.sep + self.pro
        print(" \033[31m>打包ROM \033[0m\n")
        print(f"  项目：{os.path.basename(project)}\n")
        print('\033[33m    1> 直接打包     2> 卡线一体 \n    3> 返回\033[0m\n')
        chose = input("    请输入编号: ")
        if chose == '1':
            print("正在准备打包...")
            for v in ['firmware-update', 'META-INF', 'exaid.img', 'dynamic_partitions_op_list']:
                if os.path.isdir(os.path.join(project, v)):
                    if not os.path.isdir(os.path.join(project, 'TI_out' + os.sep + v)):
                        shutil.copytree(os.path.join(project, v), os.path.join(project, 'TI_out' + os.sep + v))
                elif os.path.isfile(os.path.join(project, v)):
                    if not os.path.isfile(os.path.join(project, 'TI_out' + os.sep + v)):
                        shutil.copy(os.path.join(project, v), os.path.join(project, 'TI_out'))
            for root, dirs, files in os.walk(project):
                for f in files:
                    if f.endswith('.br') or f.endswith('.dat') or f.endswith('.list'):
                        if not os.path.isfile(os.path.join(project, 'TI_out' + os.sep + f)) and os.access(
                                os.path.join(project, f), os.F_OK):
                            shutil.copy(os.path.join(project, str(f)), os.path.join(project, 'TI_out'))
        elif chose == '2':
            utils.dbkxyt(os.path.join(project, 'TI_out') + os.sep, input("打包卡线一体限制机型代号:"),
                         binner + os.sep + 'extra_flash.zip')
        else:
            return
        zip_file(os.path.basename(project) + ".zip", project + os.sep + 'TI_out', project + os.sep, LOCALDIR + os.sep)

    def unpackrom(self):
        cls()
        zipn = 0
        zips = {}
        print(" \033[31m >ROM列表 \033[0m\n")
        ywarn(f"   请将ROM置于{LOCALDIR}下！\n")
        if dir_has(LOCALDIR, '.zip'):
            for zip0 in os.listdir(LOCALDIR):
                if zip0.endswith('.zip'):
                    if os.path.isfile(os.path.abspath(zip0)):
                        if os.path.getsize(os.path.abspath(zip0)):
                            zipn += 1
                            print(f"   [{zipn}]- {zip0}\n")
                            zips[zipn] = zip0
        else:
            ywarn("	没有ROM文件！")
        print("--------------------------------------------------\n")
        zipd = input("请输入对应序列号：")
        if zipd.isdigit():
            if int(zipd) in zips.keys():
                projec = input("请输入项目名称(可留空)：")
                project = "TI_%s" % projec if projec else "TI_%s" % os.path.basename(zips[int(zipd)]).replace('.zip',
                                                                                                              '')
                if os.path.exists(LOCALDIR + os.sep + project):
                    project = project + time.strftime("%m%d%H%M%S")
                    ywarn(f"项目已存在！自动命名为：{project}")
                os.makedirs(LOCALDIR + os.sep + project)
                print(f"创建{project}成功！")
                with Console().status("[yellow]解压刷机包中...[/]"):
                    zipfile.ZipFile(os.path.abspath(zips[int(zipd)])).extractall(LOCALDIR + os.sep + project)
                yecho("分解ROM中...")
                autounpack(LOCALDIR + os.sep + project)
                self.pro = project
                self.project()
            else:
                ywarn("Input Error")
                input("任意按钮继续")
        else:
            ywarn("Input error!")
            input("任意按钮继续")


def get_all_file_paths(directory) -> Ellipsis:
    # 初始化文件路径列表
    for root, directories, files in os.walk(directory):
        for filename in files:
            yield os.path.join(root, filename)


class zip_file:
    def __init__(self, file, dst_dir, local, path=None):
        if not path:
            path = LOCALDIR + os.sep
        os.chdir(dst_dir)
        relpath = str(path + file)
        if os.path.exists(relpath):
            ywarn(f"存在同名文件：{file}，已自动重命名为{(relpath := path + utils.v_code() + file)}")
        with zipfile.ZipFile(relpath, 'w', compression=zipfile.ZIP_DEFLATED,
                             allowZip64=True) as zip_:
            # 遍历写入文件
            for file in get_all_file_paths('.'):
                print(f"正在写入:%s" % file)
                try:
                    zip_.write(file)
                except Exception as e:
                    print("写入{}时错误{}".format(file, e))
        if os.path.exists(relpath):
            print(f'打包完成:{relpath}')
        os.chdir(local)


def subbed(project):
    if not os.path.exists(binner + os.sep + "subs"):
        os.makedirs(binner + os.sep + "subs")
    cls()
    subn = 0
    mysubs = {}
    names = {}
    print(" >\033[31m插件列表 \033[0m\n")
    for sub in os.listdir(binner + os.sep + "subs"):
        if os.path.isfile(binner + os.sep + "subs" + os.sep + sub + os.sep + "info.json"):
            with open(binner + os.sep + "subs" + os.sep + sub + os.sep + "info.json") as l_info:
                name = json.load(l_info)['name']
            subn += 1
            print(f"   [{subn}]- {name}\n")
            mysubs[subn] = sub
            names[subn] = name
    print("----------------------------------------------\n")
    print("\033[33m> [66]-安装 [77]-删除 [0]-返回\033[0m")
    op_pro = input("请输入序号：")
    if op_pro == '66':
        path = input("请输入插件路径或[拖入]:")
        if os.path.exists(path) and not path.endswith('.zip2'):
            installmpk(path)
        elif path.endswith('.zip2'):
            installmpk(zip2mpk.main(path, os.getcwd()))
        else:
            ywarn(f"{path}不存在！")
        input("任意按钮继续")
    elif op_pro == '77':
        chose = input("输入插件序号:")
        unmpk(mysubs[int(chose)], names[int(chose)], binner + os.sep + "subs") if int(
            chose) in mysubs.keys() else ywarn("序号错误")
    elif op_pro == '0':
        return
    elif op_pro.isdigit():
        if int(op_pro) in mysubs.keys():
            plugin_path = os.path.join(binner, 'subs', mysubs[int(op_pro)])
            if os.path.exists(plugin_path + os.sep + "main.sh"):
                if os.path.exists(plugin_path + os.sep + "main.json"):
                    gavs, value = plug_parse(
                        os.path.join(plugin_path, "main.json"))
                    gen = gen_sh_engine(project, gavs, value)
                else:
                    gen = gen_sh_engine(project)
                call(
                    f'busybox ash {gen} {os.path.join(plugin_path, "main.sh").replace(os.sep, "/")}')
                f_remove(gen)
            else:
                ywarn(f"{mysubs[int(op_pro)]}为环境插件，不可运行！")
            input("任意按钮返回")
    subbed(project)


def gen_sh_engine(project, gavs=None, value=None):
    if not os.path.exists(temp):
        os.makedirs(temp)
    engine = temp + os.sep + utils.v_code()
    with open(engine, 'w', encoding='utf-8', newline='\n') as en:
        en.write(f"export project={project.replace(os.sep, '/')}\n")
        en.write(f'export tool_bin={ebinner.replace(os.sep, "/")}\n')
        if gavs or value:
            for i in value:
                en.write(f"export {i}='{gavs[i]}'\n")
        en.write(f'source $1\n')
    return engine.replace(os.sep, '/')


class installmpk:
    def __init__(self, mpk):
        super().__init__()
        self.mconf = ConfigParser()
        if not mpk:
            ywarn("插件不存在")
            return
        if not zipfile.is_zipfile(mpk):
            ywarn("非插件！")
            input("任意按钮返回")
        with zipfile.ZipFile(mpk, 'r') as myfile:
            with myfile.open('info') as info_file:
                self.mconf.read_string(info_file.read().decode('utf-8'))
            with myfile.open(self.mconf.get('module', 'resource'), 'r') as inner_file:
                self.inner_zipdata = inner_file.read()
                self.inner_filenames = zipfile.ZipFile(BytesIO(self.inner_zipdata)).namelist()
        print('''
         \033[36m
        ----------------
           安装新插件
        ----------------
        ''')
        print("插件名称：" + self.mconf.get('module', 'name'))
        print("版本:%s\n作者：%s" % (self.mconf.get('module', 'version'), (self.mconf.get('module', 'author'))))
        print("介绍:")
        print(self.mconf.get('module', 'describe'))
        print("\033[0m\n")
        if input("要安装吗? [1/0]") == '1':
            self.install()
        else:
            yecho("取消安装")
            input("任意按钮返回")

    def install(self):
        try:
            supports = self.mconf.get('module', 'supports').split()
        except (Exception, BaseException):
            supports = [sys.platform]
        if sys.platform not in supports:
            ywarn(f"[!]安装失败:不支持的系统{sys.platform}")
            input("任意按钮返回")
            return False
        for dep in self.mconf.get('module', 'depend').split():
            if not os.path.isdir(binner + os.sep + "subs" + os.sep + dep):
                ywarn(f"[!]安装失败:不满足依赖{dep}")
                input("任意按钮返回")
                return False
        if os.path.exists(binner + os.sep + "subs" + os.sep + self.mconf.get('module', 'identifier')):
            shutil.rmtree(binner + os.sep + "subs" + os.sep + self.mconf.get('module', 'identifier'))
        fz = zipfile.ZipFile(BytesIO(self.inner_zipdata), 'r')
        for file in track(self.inner_filenames, description="正在安装..."):
            try:
                file = str(file).encode('cp437').decode('gbk')
            except (Exception, BaseException):
                file = str(file).encode('utf-8').decode('utf-8')
            fz.extract(file, binner + os.sep + "subs" + os.sep + self.mconf.get('module', 'identifier'))
        try:
            depends = self.mconf.get('module', 'depend')
        except (Exception, BaseException):
            depends = ''
        minfo = {"name": self.mconf.get('module', 'name'),
                 "author": self.mconf.get('module', 'author'),
                 "version": self.mconf.get('module', 'version'),
                 "identifier": self.mconf.get('module', 'identifier'),
                 "describe": self.mconf.get('module', 'describe'),
                 "depend": depends}
        with open(binner + os.sep + "subs" + os.sep + self.mconf.get('module', 'identifier') + os.sep + "info.json",
                  'w') as f:
            json.dump(minfo, f, indent=2)


class unmpk:
    def __init__(self, plug, name, moduledir):
        self.arr = []
        self.arr2 = []
        if plug:
            self.value = plug
            self.value2 = name
            self.moddir = moduledir
            self.lfdep()
            self.ask()
        else:
            ywarn("请选择插件！")
            input("任意按钮继续")

    def ask(self):
        cls()
        print(f"\033[31m >删除{self.value2} \033[0m\n")
        if self.arr2:
            print("\033[36m将会同时卸载以下插件")
            print("\n".join(self.arr2))
            print("\033[0m\n")
        self.unloop() if input("确定卸载吗 [1/0]") == '1' else ysuc("取消")
        input("任意按钮继续")

    def lfdep(self, name=None):
        if not name:
            name = self.value
        for i in [i for i in os.listdir(self.moddir) if os.path.isdir(self.moddir + os.sep + i)]:
            with open(self.moddir + os.sep + i + os.sep + "info.json", 'r', encoding='UTF-8') as f:
                data = json.load(f)
                for n in data['depend'].split():
                    if name == n:
                        self.arr.append(i)
                        self.arr2.append(data['name'])
                        self.lfdep(i)
                        break
                self.arr = sorted(set(self.arr), key=self.arr.index)
                self.arr2 = sorted(set(self.arr2), key=self.arr2.index)

    def unloop(self):
        for i in track(self.arr):
            self.umpk(i)
        self.umpk(self.value)

    def umpk(self, name=None) -> None:
        if name:
            print(f"正在卸载:{name}")
            if os.path.exists(self.moddir + os.sep + name):
                shutil.rmtree(self.moddir + os.sep + name)
            ywarn(f"卸载{name}失败！") if os.path.exists(self.moddir + os.sep + name) else yecho(f"卸载{name}成功！")


def unpack_choo(project):
    cls()
    os.chdir(project)
    print(" \033[31m >分解 \033[0m\n")
    filen = 0
    files = {}
    infos = {}
    ywarn(f"  请将文件放于{project}根目录下！\n")
    print(" [0]- 分解所有文件\n")
    if dir_has(project, '.br'):
        print("\033[33m [Br]文件\033[0m\n")
        for br0 in os.listdir(project):
            if br0.endswith('.br'):
                if os.path.isfile(os.path.abspath(br0)):
                    filen += 1
                    print(f"   [{filen}]- {br0}\n")
                    files[filen] = br0
                    infos[filen] = 'br'
    if dir_has(project, '.new.dat'):
        print("\033[33m [Dat]文件\033[0m\n")
        for dat0 in os.listdir(project):
            if dat0.endswith('.new.dat'):
                if os.path.isfile(os.path.abspath(dat0)):
                    filen += 1
                    print(f"   [{filen}]- {dat0}\n")
                    files[filen] = dat0
                    infos[filen] = 'dat'
    if dir_has(project, '.new.dat.1'):
        for dat10 in os.listdir(project):
            if dat10.endswith('.dat.1'):
                if os.path.isfile(os.path.abspath(dat10)):
                    filen += 1
                    print(f"   [{filen}]- {dat10} <分段DAT>\n")
                    files[filen] = dat10
                    infos[filen] = 'dat.1'
    if dir_has(project, '.img'):
        print("\033[33m [Img]文件\033[0m\n")
        for img0 in os.listdir(project):
            if img0.endswith('.img'):
                if os.path.isfile(os.path.abspath(img0)):
                    filen += 1
                    info = gettype(os.path.abspath(img0))
                    ywarn(f"   [{filen}]- {img0} <UNKNOWN>\n") if info == "unknow" else print(
                        f'   [{filen}]- {img0} <{info.upper()}>\n')
                    files[filen] = img0
                    infos[filen] = 'img' if info != 'sparse' else 'sparse'
    if dir_has(project, '.bin'):
        for bin0 in os.listdir(project):
            if bin0.endswith('.bin'):
                if os.path.isfile(os.path.abspath(bin0)) and gettype(os.path.abspath(bin0)) == 'payload':
                    filen += 1
                    print(f"   [{filen}]- {bin0} <BIN>\n")
                    files[filen] = bin0
                    infos[filen] = 'payload'
    if dir_has(project, '.ozip'):
        print("\033[33m [Ozip]文件\033[0m\n")
        for ozip0 in os.listdir(project):
            if ozip0.endswith('.ozip'):
                if os.path.isfile(os.path.abspath(ozip0)) and gettype(os.path.abspath(ozip0)) == 'ozip':
                    filen += 1
                    print(f"   [{filen}]- {ozip0}\n")
                    files[filen] = ozip0
                    infos[filen] = 'ozip'
    if dir_has(project, '.ofp'):
        print("\033[33m [Ofp]文件\033[0m\n")
        for ofp0 in os.listdir(project):
            if ofp0.endswith('.ofp'):
                if os.path.isfile(os.path.abspath(ofp0)):
                    filen += 1
                    print(f"   [{filen}]- {ofp0}\n")
                    files[filen] = ofp0
                    infos[filen] = 'ofp'
    if dir_has(project, '.ops'):
        print("\033[33m [Ops]文件\033[0m\n")
        for ops0 in os.listdir(project):
            if ops0.endswith('.ops'):
                if os.path.isfile(os.path.abspath(ops0)):
                    filen += 1
                    print(f'   [{filen}]- {ops0}\n')
                    files[filen] = ops0
                    infos[filen] = 'ops'
    if dir_has(project, '.win'):
        print("\033[33m [Win]文件\033[0m\n")
        for win0 in os.listdir(project):
            if win0.endswith('.win'):
                if os.path.isfile(os.path.abspath(win0)):
                    filen += 1
                    print(f"   [{filen}]- {win0} <WIN> \n")
                    files[filen] = win0
                    infos[filen] = 'win'
    if dir_has(project, '.win000'):
        for win0000 in os.listdir(project):
            if win0000.endswith('.win000'):
                if os.path.isfile(os.path.abspath(win0000)):
                    filen += 1
                    print(f"   [{filen}]- {win0000} <分段WIN> \n")
                    files[filen] = win0000
                    infos[filen] = 'win000'
    if dir_has(project, '.dtb'):
        print("\033[33m [Dtb]文件\033[0m\n")
        for dtb0 in os.listdir(project):
            if dtb0.endswith('.dtb'):
                if os.path.isfile(os.path.abspath(dtb0)) and gettype(os.path.abspath(dtb0)) == 'dtb':
                    filen += 1
                    print(f'   [{filen}]- {dtb0}\n')
                    files[filen] = dtb0
                    infos[filen] = 'dtb'
    print("\n\033[33m  [00] 返回  [77] 循环解包  \033[0m")
    print("  --------------------------------------")
    filed = input("  请输入对应序号：")
    if filed == '0':
        for v in files.keys():
            unpack(files[v], infos[v], project)
    elif filed == '77':
        imgcheck = 0
        upacall = input("  是否解包所有文件？ [1/0]")
        for v in files.keys():
            if upacall != '1':
                imgcheck = input(f"  是否解包{files[v]}?[1/0]")
            if upacall == "1" or imgcheck != "0":
                unpack(files[v], infos[v], project)
    elif filed == '00':
        return
    elif filed.isdigit():
        unpack(files[int(filed)], infos[int(filed)], project) if int(filed) in files.keys() else ywarn("Input error!")
    else:
        ywarn("Input error!")
    input("任意按钮继续")
    unpack_choo(project)


def packChoo(project):
    cls()
    print(" \033[31m >打包 \033[0m\n")
    partn = 0
    parts = {}
    types = {}
    json_ = json_edit(project + os.sep + "config" + os.sep + 'parts_info').read()
    if not os.path.exists(project + os.sep + "config"):
        os.makedirs(project + os.sep + "config")
    if project:
        print("   [0]- 打包所有镜像\n")
        for packs in os.listdir(project):
            if os.path.isdir(project + os.sep + packs):
                if os.path.exists(project + os.sep + "config" + os.sep + packs + "_fs_config"):
                    partn += 1
                    parts[partn] = packs
                    if packs in json_.keys():
                        typeo = json_[packs]
                    else:
                        typeo = 'ext'
                    types[partn] = typeo
                    print(f"   [{partn}]- {packs} <{typeo}>\n")
                elif os.path.exists(project + os.sep + packs + os.sep + "comp"):
                    partn += 1
                    parts[partn] = packs
                    types[partn] = 'bootimg'
                    print(f"   [{partn}]- {packs} <bootimg>\n")
                elif os.path.exists(project + os.sep + "config" + os.sep + "dtbinfo_" + packs):
                    partn += 1
                    parts[partn] = packs
                    types[partn] = 'dtb'
                    print(f"   [{partn}]- {packs} <dtb>\n")
                elif os.path.exists(project + os.sep + "config" + os.sep + "dtboinfo_" + packs):
                    partn += 1
                    parts[partn] = packs
                    types[partn] = 'dtbo'
                    print(f"   [{partn}]- {packs} <dtbo>\n")
        print("\n\033[33m [55] 循环打包 [66] 打包Super [77] 打包Payload [00]返回\033[0m")
        print("  --------------------------------------")
        filed = input("  请输入对应序号：")
        if filed == '0':
            op_menu = input("  输出文件格式[1]br [2]dat [3]img:")
            if op_menu == '1':
                form = 'br'
            elif op_menu == '2':
                form = 'dat'
            else:
                form = 'img'
            if settings.diyimgtype == '1':
                imgtype = input("手动打包所有分区格式为：[1]ext4 [2]erofs [3]f2fs:")
                if imgtype == '1':
                    imgtype = 'ext'
                elif imgtype == '2':
                    imgtype = "erofs"
                else:
                    imgtype = 'f2fs'
            else:
                imgtype = 'ext'
            for f in track(parts.keys()):
                yecho(f"打包{parts[f]}...")
                if types[f] == 'bootimg':
                    dboot(project + os.sep + parts[f], project + os.sep + parts[f] + ".img")
                elif types[f] == 'dtb':
                    makedtb(parts[f], project)
                elif types[f] == 'dtbo':
                    makedtbo(parts[f], project)
                else:
                    inpacker(parts[f], project, form, imgtype)
        elif filed == '55':
            op_menu = input("  输出所有文件格式[1]br [2]dat [3]img:")
            if op_menu == '1':
                form = 'br'
            elif op_menu == '2':
                form = 'dat'
            else:
                form = 'img'
            if settings.diyimgtype == '1':
                imgtype = input("手动打包所有分区格式为：[1]ext4 [2]erofs [3]f2fs:")
                if imgtype == '1':
                    imgtype = 'ext'
                elif imgtype == '2':
                    imgtype = "erofs"
                else:
                    imgtype = 'f2fs'
            else:
                imgtype = 'ext'
            for f in parts.keys():
                imgcheck = input(f"  是否打包{parts[f]}?[1/0]	") if input(
                    "  是否打包所有镜像？ [1/0]	") != '1' else '1'
                if not imgcheck == '1':
                    continue
                yecho(f"打包{parts[f]}...")
                if types[f] == 'bootimg':
                    dboot(project + os.sep + parts[f], project + os.sep + parts[f] + ".img")
                elif types[f] == 'dtb':
                    makedtb(parts[f], project)
                elif types[f] == 'dtbo':
                    makedtbo(parts[f], project)
                else:
                    inpacker(parts[f], project, form, imgtype, json_)
        elif filed == '66':
            packsuper(project)
        elif filed == '77':
            packpayload(project)
        elif filed == '00':
            return
        elif filed.isdigit():
            if int(filed) in parts.keys():
                if settings.diyimgtype == '1' and types[int(filed)] not in ['bootimg', 'dtb', 'dtbo']:
                    imgtype = input("手动打包所有分区格式为：[1]ext4 [2]erofs [3]f2fs:")
                    if imgtype == '1':
                        imgtype = 'ext'
                    elif imgtype == '2':
                        imgtype = "erofs"
                    else:
                        imgtype = 'f2fs'
                else:
                    imgtype = 'ext'
                if settings.diyimgtype == '1' and types[int(filed)] not in ['bootimg', 'dtb', 'dtbo']:
                    op_menu = input("  输出所有文件格式[1]br [2]dat [3]img:")
                    if op_menu == '1':
                        form = 'br'
                    elif op_menu == '2':
                        form = "dat"
                    else:
                        form = 'img'
                else:
                    form = 'img'
                yecho(f"打包{parts[int(filed)]}")
                if types[int(filed)] == 'bootimg':
                    dboot(project + os.sep + parts[int(filed)], project + os.sep + parts[int(filed)] + ".img")
                elif types[int(filed)] == 'dtb':
                    makedtb(parts[int(filed)], project)
                elif types[int(filed)] == 'dtbo':
                    makedtbo(parts[int(filed)], project)
                else:
                    inpacker(parts[int(filed)], project, form, imgtype, json_)
            else:
                ywarn("Input error!")
        else:
            ywarn("Input error!")
        input("任意按钮继续")
        packChoo(project)


def dboot(infile, orig):
    flag = ''
    if not os.path.exists(infile):
        print(f"Cannot Find {infile}...")
        return
    if os.path.isdir(infile + os.sep + "ramdisk"):
        try:
            os.chdir(infile + os.sep + "ramdisk")
        except Exception as e:
            print("Ramdisk Not Found.. %s" % e)
            return
        cpio = utils.findfile("cpio.exe" if os.name != 'posix' else 'cpio',
                              ebinner).replace(
            '\\', "/")
        call(['busybox', 'ash', '-c', f'find | sed 1d | {cpio} -H newc -R 0:0 -o -F ../ramdisk-new.cpio'])
        os.chdir(infile)
        with open("comp", "r", encoding='utf-8') as compf:
            comp = compf.read()
        print("Compressing:%s" % comp)
        if comp != "unknow":
            if call(["magiskboot", f"compress={comp}", "ramdisk-new.cpio"]) != 0:
                print("Pack Ramdisk Fail...")
                os.remove("ramdisk-new.cpio")
                return
            else:
                print("Pack Ramdisk Successful..")
                try:
                    os.remove("ramdisk.cpio")
                except (Exception, BaseException):
                    ...
                os.rename("ramdisk-new.cpio.%s" % comp.split('_')[0], "ramdisk.cpio")
        else:
            print("Pack Ramdisk Successful..")
            os.remove("ramdisk.cpio")
            os.rename("ramdisk-new.cpio", "ramdisk.cpio")
        if comp == "cpio":
            flag = "-n"
    else:
        os.chdir(infile)
    if call(["magiskboot", "repack", flag, orig]) != 0:
        print("Pack boot Fail...")
        return
    else:
        os.remove(orig)
        os.rename(infile + os.sep + "new-boot.img", orig)
        os.chdir(LOCALDIR)
        try:
            rmdire(infile)
        except (Exception, BaseException):
            print("删除错误...")
        print("Pack Successful...")


def unpackboot(file, project):
    name = os.path.basename(file).replace('.img', '')
    rmdire(project + os.sep + name)
    os.makedirs(project + os.sep + name)
    os.chdir(project + os.sep + name)
    if call(["magiskboot", "unpack", "-h", file]) != 0:
        print("Unpack %s Fail..." % file)
        os.chdir(LOCALDIR)
        shutil.rmtree(project + os.sep + name)
        return
    if os.access(project + os.sep + name + os.sep + "ramdisk.cpio", os.F_OK):
        comp = gettype(project + os.sep + name + os.sep + "ramdisk.cpio")
        print(f"Ramdisk is {comp}")
        with open(project + os.sep + name + os.sep + "comp", "w") as f:
            f.write(comp)
        if comp != "unknow":
            os.rename(project + os.sep + name + os.sep + "ramdisk.cpio",
                      project + os.sep + name + os.sep + "ramdisk.cpio.comp")
            if call(["magiskboot", "decompress", f"{project}/{name}/ramdisk.cpio.comp", f"{project}/{name}/ramdisk.cpio"]) != 0:
                print("Decompress Ramdisk Fail...")
                return
        if not os.path.exists(project + os.sep + name + os.sep + "ramdisk"):
            os.mkdir(project + os.sep + name + os.sep + "ramdisk")
        os.chdir(project + os.sep + name + os.sep)
        print("Unpacking Ramdisk...")
        call(['cpio', '-i', '-d', '-F', 'ramdisk.cpio', '-D', 'ramdisk'])
        os.chdir(LOCALDIR)
    else:
        print("Unpack Done!")
    os.chdir(LOCALDIR)


def undtb(project, infile):
    dtbdir = project + os.sep + os.path.basename(infile).split(".")[0]
    rmdire(dtbdir)
    if not os.path.exists(dtbdir):
        os.makedirs(dtbdir)
    extract_dtb.extract_dtb.split(Namespace(filename=infile, output_dir=dtbdir + os.sep + "dtb_files", extract=1))
    yecho("正在反编译dtb...")
    for i in track(os.listdir(dtbdir + os.sep + "dtb_files")):
        if i.endswith('.dtb'):
            name = i.split('.')[0]
            dtb = os.path.join(dtbdir, 'dtb_files', name + ".dtb")
            dts = os.path.join(dtbdir, 'dtb_files', name + ".dts")
            call(
                ['dtc', '-@', '-I', 'dtb', '-O', 'dts', str(dtb), '-o', str(dts)],
                out=1)
    open(project + os.sep + os.sep + "config" + os.sep + "dtbinfo_" + os.path.basename(infile).split(".")[0],
         'w').close()
    ysuc("反编译完成!")
    time.sleep(1)


def makedtb(sf, project):
    dtbdir = project + os.sep + sf
    rmdire(dtbdir + os.sep + "new_dtb_files")
    os.makedirs(dtbdir + os.sep + "new_dtb_files")
    for dts_files in os.listdir(dtbdir + os.sep + "dtb_files"):
        new_dtb_files = dts_files.split('.')[0]
        yecho(f"正在回编译{dts_files}为{new_dtb_files}.dtb")
        dtb_ = dtbdir + "/dtb_files/" + dts_files
        if call(['dtc', '-@', '-I', 'dts', '-O', 'dtb', dtb_, '-o', f'{dtbdir}/new_dtb_files/{new_dtb_files}.dtb'],
                out=1) != 0:
            ywarn("回编译dtb失败")
    with open(project + os.sep + "TI_out" + os.sep + sf, 'wb') as sff:
        for dtb in os.listdir(dtbdir + os.sep + "new_dtb_files"):
            if dtb.endswith('.dtb'):
                with open(os.path.abspath(dtb), 'rb') as f:
                    sff.write(f.read())
    ysuc("回编译完成！")


def undtbo(project, infile):
    dtbodir = project + os.sep + os.path.basename(infile).split('.')[0]
    open(project + os.sep + "config" + os.sep + "dtboinfo_" + os.path.basename(infile).split('.')[0], 'w').close()
    rmdire(dtbodir)
    if not os.path.exists(dtbodir + os.sep + "dtbo_files"):
        os.makedirs(dtbodir + os.sep + "dtbo_files")
        try:
            os.makedirs(dtbodir + os.sep + "dts_files")
        except (Exception, BaseException):
            ...
    yecho("正在解压dtbo.img")
    mkdtboimg.dump_dtbo(infile, dtbodir + os.sep + "dtbo_files" + os.sep + "dtbo")
    for dtbo_files in os.listdir(dtbodir + os.sep + "dtbo_files"):
        if dtbo_files.startswith('dtbo.'):
            dts_files = dtbo_files.replace("dtbo", 'dts')
            yecho(f"正在反编译{dtbo_files}为{dts_files}")
            dtbofiles = dtbodir + os.sep + "dtbo_files" + os.sep + dtbo_files
            if call(f'dtc -@ -I "dtb" -O "dts" {dtbofiles} -o "{dtbodir + os.sep + "dts_files" + os.sep + dts_files}"',
                    out=1) != 0:
                ywarn(f"反编译{dtbo_files}失败！")
    ysuc("完成！")
    time.sleep(1)


def makedtbo(sf, project):
    dtbodir = project + os.sep + os.path.basename(sf).split('.')[0]
    rmdire(dtbodir + os.sep + 'new_dtbo_files')
    if os.path.exists(project + os.sep + os.path.basename(sf).split('.')[0] + '.img'):
        os.remove(project + os.sep + os.path.basename(sf).split('.')[0] + '.img')
    os.makedirs(dtbodir + os.sep + 'new_dtbo_files')
    for dts_files in os.listdir(dtbodir + os.sep + 'dts_files'):
        new_dtbo_files = dts_files.replace('dts', 'dtbo')
        yecho(f"正在回编译{dts_files}为{new_dtbo_files}")
        dtb_ = dtbodir + os.sep + "dts_files" + os.sep + dts_files
        call(
            f'dtc -@ -I "dts" -O "dtb" {dtb_} -o {dtbodir + os.sep + "new_dtbo_files" + os.sep + new_dtbo_files}',
            out=1)
    yecho("正在生成dtbo.img...")
    list_ = []
    for b in os.listdir(dtbodir + os.sep + "new_dtbo_files"):
        if b.startswith('dtbo.'):
            list_.append(dtbodir + os.sep + "new_dtbo_files" + os.sep + b)
    list_ = sorted(list_, key=lambda x: int(float(x.rsplit('.', 1)[1])))
    try:
        mkdtboimg.create_dtbo(project + os.sep + os.path.basename(sf).split('.')[0] + '.img', list_, 4096)
    except (Exception, BaseException):
        ywarn(f"{os.path.basename(sf).split('.')[0]}.img生成失败!")
    else:
        ysuc(f"{os.path.basename(sf).split('.')[0]}.img生成完毕!")


def inpacker(name, project, form, ftype, json_=None):
    if json_ is None:
        json_ = {}

    def rdi(name_):
        try:
            dir_path = os.path.join(project, "TI_out")
            os.remove(dir_path + os.sep + name_ + ".new.dat")
            os.remove(dir_path + os.sep + name_ + ".patch.dat")
            os.remove(dir_path + os.sep + name_ + ".transfer.list")
        except (Exception, BaseException):
            ...

    file_contexts = project + os.sep + "config" + os.sep + name + "_file_contexts"
    fs_config = project + os.sep + "config" + os.sep + name + "_fs_config"
    utc = int(time.time()) if not settings.utcstamp else settings.utcstamp
    out_img = project + os.sep + "TI_out" + os.sep + name + ".img"
    in_files = project + os.sep + name + os.sep
    img_size0 = int(cat(project + os.sep + "config" + os.sep + name + "_size.txt")) if os.path.exists(
        project + os.sep + "config" + os.sep + name + "_size.txt") else 0
    img_size1 = dirsize(in_files, 1, 1).rsize_v
    if settings.diysize == '' and img_size0 < img_size1:
        ywarn("您设置的size过小,将动态调整size!")
        img_size0 = dirsize(in_files, 1, 3, project + os.sep + "dynamic_partitions_op_list").rsize_v
    elif settings.diysize == '':
        img_size0 = dirsize(in_files, 1, 3, project + os.sep + "dynamic_partitions_op_list").rsize_v
    fspatch.main(in_files, fs_config)
    if settings.context == 'true' and os.path.exists(file_contexts):
        contextpatch.main(in_files, file_contexts)
    if os.path.exists(file_contexts):
        utils.qc(file_contexts)
    utils.qc(fs_config)
    size = img_size0 / int(settings.BLOCKSIZE)
    size = int(size)
    if ftype == 'erofs':
        other_ = '-E legacy-compress' if settings.erofs_old_kernel == '1' else ''
        call(
            f'mkfs.erofs {other_} -z{settings.erofslim}  -T {utc} --mount-point=/{name} --fs-config-file={fs_config} --product-out={os.path.dirname(out_img)} --file-contexts={file_contexts} {out_img} {in_files}')
    elif ftype == 'f2fs':
        size_f2fs = (54 * 1024 * 1024) + img_size1
        size_f2fs = int(size_f2fs*1.15)+1
        with open(out_img, 'wb') as f:
            f.truncate(size_f2fs)
        call(f'mkfs.f2fs {out_img} -O extra_attr -O inode_checksum -O sb_checksum -O compression -f')
        call(f'sload.f2fs -f {in_files} -C {fs_config} -s {file_contexts} -t /{name} {out_img} -c')
    else:
        if os.path.exists(file_contexts):
            if settings.pack_e2 == '0':
                call(
                    f'make_ext4fs -J -T {utc} -S {file_contexts} -l {img_size0} -C {fs_config} -L {name} -a {name} {out_img} {in_files}')
            else:
                call(
                    f'mke2fs -O ^has_journal -L {name} -I 256 -M /{name} -m 0 -t ext4 -b {settings.BLOCKSIZE} {out_img} {size}')
                call(
                    f"e2fsdroid -e -T {utc} -S {file_contexts} -C {fs_config} -a /{name} -f {in_files} {out_img}")
        else:
            call(
                f'make_ext4fs -J -T {utc} -l {img_size0} -C {fs_config} -L {name} -a {name} {out_img} {in_files}')
    if settings.pack_sparse == '1' or form in ['dat', 'br']:
        call(f"img2simg {out_img} {out_img}.s")
        os.remove(out_img)
        os.rename(out_img + ".s", out_img)
    if form in ['br', 'dat']:
        rdi(name)
    if form in ['dat', 'br']:
        yecho(f"打包[DAT]:{name}")
        rdi(name)
        try:
            os.remove(project + os.sep + "TI_out" + os.sep + name + ".patch.dat")
        except (Exception, BaseException):
            ...
        utils.img2sdat(out_img, project + os.sep + "TI_out", int(json_.get('dat_ver', '4')), name)
        try:
            os.remove(out_img)
        except (Exception, BaseException):
            ...
    if form == 'br':
        yecho(f"打包[BR]:{name}")
        call(
            f'brotli -q {settings.brcom} -j -w 24 {project + os.sep + "TI_out" + os.sep + name + ".new.dat"} -o {project + os.sep + "TI_out" + os.sep + name + ".new.dat.br"}')


def versize(size):
    size_ = size
    diff_size = size_
    for i_ in range(20):
        if not i_:
            continue
        i_ = i_ - 0.5
        t = 1024 * 1024 * 1024 * i_ - size_
        if t < 0:
            continue
        if t < diff_size:
            diff_size = t
        else:
            return int(i_ * 1024 * 1024 * 1024)


def packsuper(project):
    if os.path.exists(project + os.sep + "TI_out" + os.sep + "super.img"):
        os.remove(project + os.sep + "TI_out" + os.sep + "super.img")
    if not os.path.exists(project + os.sep + "super"):
        os.makedirs(project + os.sep + "super")
    cls()
    ywarn(f"请将需要打包的分区镜像放置于{project}{os.sep}super中！")
    supertype = input("请输入Super类型：[1]A_only [2]AB [3]V-AB-->")
    if supertype == '3':
        supertype = 'VAB'
    elif supertype == '2':
        supertype = 'AB'
    else:
        supertype = 'A_only'
    isreadonly = input("是否设置为只读分区？[1/0]")
    ifsparse = input("是否打包为sparse镜像？[1/0]")
    if not os.listdir(project + os.sep + 'super'):
        print("您似乎没有要打包的分区，要移动下列分区打包吗：")
        move_list = []
        for i in os.listdir(project + os.sep + 'TI_out'):
            if os.path.isfile(os.path.join(project + os.sep + 'TI_out', i)):
                if gettype(os.path.join(project + os.sep + 'TI_out', i)) in ['ext', 'erofs']:
                    if i.startswith('dsp'):
                        continue
                    move_list.append(i)
        print("\n".join(move_list))
        if input('确定操作吗[Y/N]') in ['Y', 'y', '1']:
            for i in move_list:
                shutil.move(os.path.join(project + os.sep + 'TI_out', i), os.path.join(project + os.sep + 'super', i))
    tool_auto_size = sum(
        [os.path.getsize(os.path.join(project + os.sep + 'super', p)) for p in os.listdir(project + os.sep + 'super') if
         os.path.isfile(os.path.join(project + os.sep + 'super', p))]) + 409600
    tool_auto_size = versize(tool_auto_size)
    checkssize = input(
        f"请设置Super.img大小:[1]9126805504 [2]10200547328 [3]16106127360 [4]工具推荐：{tool_auto_size} [5]自定义")
    if checkssize == '1':
        supersize = 9126805504
    elif checkssize == '2':
        supersize = 10200547328
    elif checkssize == '3':
        supersize = 16106127360
    elif checkssize == '4':
        supersize = tool_auto_size
    else:
        supersize = input("请输入super分区大小（字节数）:")
    yecho("打包到TI_out/super.img...")
    insuper(project + os.sep + 'super', project + os.sep + 'TI_out' + os.sep + "super.img", supersize, supertype,
            ifsparse, isreadonly)


def insuper(Imgdir, outputimg, ssize, stype, sparsev, isreadonly):
    attr = "readonly" if isreadonly == '1' else "none"
    group_size_a = 0
    group_size_b = 0
    for root, dirs, files in os.walk(Imgdir):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.isfile(file_path) and os.path.getsize(file_path) == 0:
                os.remove(file_path)
    superpa = f"--metadata-size {settings.metadatasize} --super-name {settings.supername} "
    if sparsev == '1':
        superpa += "--sparse "
    if stype == 'VAB':
        superpa += "--virtual-ab "
    superpa += f"-block-size={settings.SBLOCKSIZE} "
    for imag in os.listdir(Imgdir):
        if imag.endswith('.img'):
            image = imag.replace("_a.img", "").replace("_b.img", "").replace(".img", "")
            if f'partition {image}:{attr}' not in superpa and f'partition {image}_a:{attr}' not in superpa:
                if stype in ['VAB', 'AB']:
                    if os.path.isfile(Imgdir + os.sep + image + "_a.img") and os.path.isfile(
                            Imgdir + os.sep + image + "_b.img"):
                        img_sizea = os.path.getsize(Imgdir + os.sep + image + "_a.img")
                        img_sizeb = os.path.getsize(Imgdir + os.sep + image + "_b.img")
                        group_size_a += img_sizea
                        group_size_b += img_sizeb
                        superpa += f"--partition {image}_a:{attr}:{img_sizea}:{settings.super_group}_a --image {image}_a={Imgdir}{os.sep}{image}_a.img --partition {image}_b:{attr}:{img_sizeb}:{settings.super_group}_b --image {image}_b={Imgdir}{os.sep}{image}_b.img "
                    else:
                        if not os.path.exists(Imgdir + os.sep + image + ".img") and os.path.exists(
                                Imgdir + os.sep + image + "_a.img"):
                            os.rename(Imgdir + os.sep + image + "_a.img", Imgdir + os.sep + image + ".img")

                        img_size = os.path.getsize(Imgdir + os.sep + image + ".img")
                        group_size_a += img_size
                        group_size_b += img_size
                        superpa += f"--partition {image}_a:{attr}:{img_size}:{settings.super_group}_a --image {image}_a={Imgdir}{os.sep}{image}.img --partition {image}_b:{attr}:0:{settings.super_group}_b "
                else:
                    if not os.path.exists(Imgdir + os.sep + image + ".img") and os.path.exists(
                            Imgdir + os.sep + image + "_a.img"):
                        os.rename(Imgdir + os.sep + image + "_a.img", Imgdir + os.sep + image + ".img")

                    img_size = os.path.getsize(Imgdir + os.sep + image + ".img")
                    superpa += f"--partition {image}:{attr}:{img_size}:{settings.super_group} --image {image}={Imgdir}{os.sep}{image}.img "
                    group_size_a += img_size
                print(f"已添加分区:{image}")
    supersize = ssize
    if not supersize:
        supersize = group_size_a + 4096000
    superpa += f"--device super:{supersize} "
    if stype in ['VAB', 'AB']:
        superpa += "--metadata-slots 3 "
        superpa += f" --group {settings.super_group}_a:{supersize} "
        superpa += f" --group {settings.super_group}_b:{supersize} "
    else:
        superpa += "--metadata-slots 2 "
        superpa += f" --group {settings.super_group}:{supersize} "
    superpa += f"{settings.fullsuper} {settings.autoslotsuffixing} --output {outputimg}"
    ywarn("创建super.img失败！") if call(f'lpmake {superpa}') != 0 else ysuc("成功创建super.img!")


def packpayload(project):
    if ostype != 'Linux':
        print(f"不支持当前系统:{ostype},目前只支持:Linux(aarch64&x86)")
        input("任意按钮继续")
        return
    if os.path.exists(project + os.sep + 'payload'):
        if input('发现之前打包Payload残留，清空吗[1/0]') == '1':
            re_folder(project + os.sep + 'payload')
            re_folder(project + os.sep + 'TI_out' + os.sep + "payload")
            f_remove(project + os.sep + 'TI_out' + os.sep + "payload" + os.sep + 'dynamic_partitions_info.txt')
    else:
        os.makedirs(project + os.sep + 'payload')
    ywarn(f"请将所有分区镜像放置于{project + os.sep}payload中！")
    yecho("这项功能很耗时、很费CPU、很费内存，若无官方签名则意义不大，请考虑后使用")
    if not os.listdir(project + os.sep + 'payload'):
        print("您似乎没有要打包的分区，要移动下列分区打包吗：")
        move_list = []
        for i in os.listdir(project + os.sep + 'TI_out'):
            if os.path.isfile(os.path.join(project + os.sep + 'TI_out', i)):
                if i.endswith('.img'):
                    move_list.append(i)
        print("\n".join(move_list))
        if input('确定操作吗[Y/N]') in ['Y', 'y', '1']:
            for i in move_list:
                shutil.move(os.path.join(project + os.sep + 'TI_out', i), os.path.join(project + os.sep + 'payload', i))
    tool_auto_size = sum(
        [os.path.getsize(os.path.join(project + os.sep + 'payload', p)) for p in
         os.listdir(project + os.sep + 'payload') if
         os.path.isfile(os.path.join(project + os.sep + 'payload', p))]) + 409600
    tool_auto_size = versize(tool_auto_size)
    checkssize = input(f"请设置构建Super.img大小:[1]9126805504 [2]10200547328 [3]工具推荐：{tool_auto_size} [5]自定义")
    if checkssize == '1':
        supersize = 9126805504
    elif checkssize == '2':
        supersize = 10200547328
    elif checkssize == '3':
        supersize = tool_auto_size
    else:
        supersize = input("请输入super分区大小（字节数）： ")
    yecho(f"打包到{project}/TI_out/payload...")
    inpayload(supersize, project)


def inpayload(supersize, project):
    yecho("将打包至：TI_out/payload，payload.bin & payload_properties.txt")
    partname = []
    super_list = []
    pimages = []
    out = project + os.sep + 'TI_out' + os.sep + 'payload' + os.sep + 'payload.bin'
    for sf in os.listdir(project + os.sep + 'payload'):
        if sf.endswith('.img'):
            partname.append(sf.replace('.img', ''))
            if gettype(project + os.sep + 'payload' + os.sep + sf) in ['ext', 'erofs']:
                super_list.append(sf.replace('.img', ''))
            pimages.append(f"{project}{os.sep}payload{os.sep}{sf}")
            yecho(f"预打包:{sf}")
    inparts = f"--partition_names={':'.join(partname)} --new_partitions={':'.join(pimages)}"
    yecho(f"当前Super逻辑分区表：{super_list}")
    with open(project + os.sep + "payload" + os.sep + "parts_info.txt", 'w', encoding='utf-8',
              newline='\n') as txt:
        txt.write(f"super_partition_groups={settings.super_group}\n")
        txt.write(f"qti_dynamic_partitions_size={supersize}\n")
        txt.write(f"qti_dynamic_partitions_partition_list={' '.join(super_list)}\n")
    os.system(
        f"{ebinner}delta_generator --out_file={out} {inparts} --dynamic_partition_info_file={os.path.join(project, 'payload', 'parts_info.txt')}")
    if not os.path.exists(out):
        input("错误 ，未写入文件")
    else:
        LOGS("成功创建payload!") if call(
            f"delta_generator --in_file={out} --properties_file={project + os.sep + 'config' + os.sep}payload_properties.txt") == 0 else LOGE(
            "创建payload失败！")


def unpack(file, info, project):
    if not os.path.exists(file):
        file = os.path.join(project, file)
    json_ = json_edit(os.path.join(project, 'config', 'parts_info'))
    parts = json_.read()
    if not os.path.exists(project + os.sep + 'config'):
        os.makedirs(project + os.sep + 'config')
    yecho(f"[{info}]解包{os.path.basename(file)}中...")
    if info == 'sparse':
        simg2img(os.path.join(project, file))
        unpack(file, gettype(file), project)
    elif info == 'dtbo':
        undtbo(project, os.path.abspath(file))
    elif info == 'br':
        call(f'brotli -dj {file}')
        partname = str(os.path.basename(file).replace('.new.dat.br', ''))
        filepath = str(os.path.dirname(file))
        unpack(os.path.join(filepath, partname + ".new.dat"), 'dat', project)
    elif info == 'dtb':
        undtb(project, os.path.abspath(file))
    elif info == 'dat':
        partname = str(os.path.basename(file).replace('.new.dat', ''))
        filepath = str(os.path.dirname(file))
        version = utils.sdat2img(os.path.join(filepath, partname + '.transfer.list'),
                                 os.path.join(filepath, partname + ".new.dat"),
                                 os.path.join(filepath, partname + ".img")).version
        parts['dat_ver'] = version
        try:
            os.remove(os.path.join(filepath, partname + ".new.dat"))
            os.remove(os.path.join(filepath, partname + '.transfer.list'))
            os.remove(os.path.join(filepath, partname + '.patch.dat'))
        except (Exception, BaseException):
            ...
        unpack(os.path.join(filepath, partname + ".img"), gettype(os.path.join(filepath, partname + ".img")), project)
    elif info == 'img':
        parts[os.path.basename(file).split('.')[0]] = gettype(file)
        unpack(file, gettype(file), project)
    elif info == 'ofp':
        ofpm = input(" ROM机型处理器为？[1]高通 [2]MTK	")
        if ofpm == '1':
            ofp_qc_decrypt.main(file, project)
        elif ofpm == '2':
            ofp_mtk_decrypt.main(file, project)
    elif info == 'ozip':
        ozipdecrypt.main(file)
        try:
            os.remove(file)
        except Exception as e:
            print(f"错误！{e}")
        zipfile.ZipFile(file.replace('.ozip', '.zip')).extractall(project)
    elif info == 'ops':
        args = {"decrypt": True,
                '<filename>': file,
                'outdir': os.path.join(project, os.path.dirname(file).split('.')[0])}
        opscrypto.main(args)
    elif info == 'payload':
        yecho(f"{os.path.basename(file)}所含分区列表：")
        with open(file, 'rb') as pay:
            print(f'{(parts_ := [i.partition_name for i in utils.payload_reader(pay).partitions])}')
        extp = input("请输入需要解压的分区名(空格隔开)/all[全部]	")
        if extp == 'all':
            Dumper(
                file,
                project,
                diff=False,
                old='old',
                images=parts_
            ).run()
        else:
            Dumper(
                file,
                project,
                diff=False,
                old='old',
                images=[p for p in extp.split()]
            ).run()
    elif info == 'win000':
        for fd in [f for f in os.listdir(project) if re.search(r'\.win\d+', f)]:
            with open(project + os.path.basename(fd).rsplit('.', 1)[0], 'ab') as ofd:
                for fd1 in sorted(
                        [f for f in os.listdir(project) if f.startswith(os.path.basename(fd).rsplit('.', 1)[0] + ".")],
                        key=lambda x: int(x.rsplit('.')[3])):
                    print("合并%s到%s" % (fd1, os.path.basename(fd).rsplit('.', 1)[0]))
                    with open(project + os.sep + fd1, 'rb') as nfd:
                        ofd.write(nfd.read())
                    os.remove(project + os.sep + fd1)
        filepath = os.path.dirname(file)
        unpack(os.path.join(filepath, file), gettype(os.path.join(filepath, file)), project)
    elif info == 'win':
        filepath = os.path.dirname(file)
        unpack(os.path.join(filepath, file), gettype(os.path.join(filepath, file)), project)
    elif info == 'ext':
        with open(file, 'rb+') as e:
            mount = ext4.Volume(e).get_mount_point
            if mount[:1] == '/':
                mount = mount[1:]
            if '/' in mount:
                mount = mount.split('/')
                mount = mount[len(mount) - 1]
            if mount and os.path.basename(file).split('.')[0] != 'mi_ext':
                parts[mount] = 'ext'
        with Console().status(f"[yellow]正在提取{os.path.basename(file)}[/]"):
            imgextractor.Extractor().main(file, project + os.sep + os.path.basename(file).split('.')[0], project)
        try:
            os.remove(file)
        except (Exception, BaseException):
            ...
    elif info == 'dat.1':
        for fd in [f for f in os.listdir(project) if re.search(r'\.new\.dat\.\d+', f)]:
            with open(project + os.sep + os.path.basename(fd).rsplit('.', 1)[0], 'ab') as ofd:
                for fd1 in sorted(
                        [f for f in os.listdir(project) if f.startswith(os.path.basename(fd).rsplit('.', 1)[0] + ".")],
                        key=lambda x: int(x.rsplit('.')[3])):
                    print("合并%s到%s" % (fd1, os.path.basename(fd).rsplit('.', 1)[0]))
                    with open(project + os.sep + fd1, 'rb') as nfd:
                        ofd.write(nfd.read())
                    os.remove(project + os.sep + fd1)
        partname = str(os.path.basename(file).replace('.new.dat.1', ''))
        filepath = str(os.path.dirname(file))
        utils.sdat2img(os.path.join(filepath, partname + '.transfer.list'),
                       os.path.join(filepath, partname + ".new.dat"), os.path.join(filepath, partname + ".img"))
        unpack(os.path.join(filepath, partname + ".img"), gettype(os.path.join(filepath, partname + ".img")), project)
    elif info == 'erofs':
        call(f'extract.erofs -i {os.path.abspath(file)} -o {project} -x')
    elif info == 'f2fs' and os.name == 'posix':
        call(f'extract.f2fs -o {project} {os.path.abspath(file)}')
    elif info == 'super':
        lpunpack.unpack(os.path.abspath(file), project)
        for v in os.listdir(project):
            if os.path.isfile(project + os.sep + v):
                if os.path.getsize(project + os.sep + v) == 0:
                    os.remove(project + os.sep + v)
                else:
                    if os.path.exists(project + os.sep + v.replace('_a', '')) or os.path.exists(
                            project + os.sep + v.replace('_b', '')):
                        continue
                    if v.endswith('_a.img'):
                        shutil.move(project + os.sep + v, project + os.sep + v.replace('_a', ''))
                    elif v.endswith('_b.img'):
                        shutil.move(project + os.sep + v, project + os.sep + v.replace('_b', ''))
    elif info in ['boot', 'vendor_boot']:
        unpackboot(os.path.abspath(file), project)
    else:
        ywarn("未知格式！")
    json_.write(parts)


def autounpack(project):
    yecho("自动解包开始！")
    os.chdir(project)
    if os.path.exists(project + os.sep + "payload.bin"):
        yecho('解包 payload.bin...')
        unpack(project + os.sep + 'payload.bin', 'payload', project)
        yecho("解包完成！")
        wastes = ['care_map.pb', 'apex_info.pb']
        if input("你要删除payload吗[1/0]") == '1':
            wastes.append('payload.bin')
        for waste in wastes:
            if os.path.exists(project + os.sep + waste):
                try:
                    os.remove(project + os.sep + waste)
                except (Exception, BaseException):
                    ...
        if not os.path.isdir(project + os.sep + "config"):
            os.makedirs(project + os.sep + "config")
        shutil.move(project + os.sep + "payload_properties.txt", project + os.sep + "config")
        shutil.move(project + os.sep + "META-INF" + os.sep + "com" + os.sep + "android" + os.sep + "metadata",
                    project + os.sep + "config")
    ask_ = input("解包所有文件？[1/0]")
    for infile in os.listdir(project):
        os.chdir(project)
        if os.path.isdir(os.path.abspath(infile)):
            continue
        elif not os.path.exists(os.path.abspath(infile)):
            continue
        elif os.path.getsize(os.path.abspath(infile)) == 0:
            continue
        elif os.path.abspath(infile).endswith('.list') or os.path.abspath(infile).endswith('.patch.dat'):
            continue
        if ask_ != '1':
            if not input(f"要分解{infile}吗 [1/0]") == '1':
                continue
        if infile.endswith('.new.dat.br'):
            unpack(os.path.abspath(infile), 'br', project)
        elif infile.endswith('.dat.1'):
            unpack(os.path.abspath(infile), 'dat.1', project)
        elif infile.endswith('.new.dat'):
            unpack(os.path.abspath(infile), 'dat', project)
        elif infile.endswith('.img'):
            unpack(os.path.abspath(infile), 'img', project)


if __name__ == '__main__':
    Tool().main()
