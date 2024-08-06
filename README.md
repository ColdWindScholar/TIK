##  TIK
####  **介绍** 
***
> [!CAUTION]
> 此项目非发布在gitcode， 如果您在gitcode发现此项目，请联系我们并保留截图证据
***
> [!CAUTION]
> 免费软件， 未经允许禁止商用 | Free software, unauthorized commercial use prohibited

[Русский](../../tree/ru)

1.  【 **TIK工具箱** 】 ——一个永久开源的ROM工具箱，支持安卓全版本ROM镜像的处理，目前更新到Ver.5；

2. 已支持大多常见镜像的分解/打包，较完善支持erofs/V-AB分区等

3. 新增设置功能-调整交互习惯、打包行为

4. 测试支持Android15中...

5. 全新MKC_Boot_Kitchen解打[boot|exaid|recovery/etc].img
    
6. 支持分解全版本super.img(V-AB)支持各种类型打包（半自动识别，高效稳定）

####  **支持** 

【 **识别分解 打包支持** 】

1. 【 *.zip, *.br, *.dat, ext4/2 *.img, bootimg 等】传统镜像识别-分解-打包
2. 【 Super.img <A-onloy/AB/V-AB>, bootimg<header3>, erofs *.img,  F2FS(本工具LINUX 64BIT版本支持) 等】较新镜像识别-分解-打包
3. 【 dtbo，dtb , TWRP, ops, ofp, ozip, payload.bin, *.win000-004, *.dat.1~20等】特殊文件的解包/打包
4. 较完善适配最新 **安卓14** **Erofs** **动态分区** **V-AB分区**


【 **软件架构  同时支持** 】

1. 手机 Termux  Arm64[aarch64] 原生支持 或者 [<Linux Deploy>/Termux] Chroot Ubuntu 20.04及以上版本 Arm64[aarch64] 【推荐chroot，效率更高】

2. 虚拟机或实体机 Ubuntu 20.04及以上版本 x86_64[x64] 

3.Windows 7 and Newer[x64/x86]

Note: WSL 可能存在权限出错的问题 请自行判断测试！
#### **引用项目**
1. [ApkParse](https://github.com/zxvzxv/ApkParse/)
2. [sdat2img](https://github.com/xpirt/sdat2img)
3. [img2sdat](https://github.com/xpirt/img2sdat)
4. [make_ext4fs](https://github.com/jamflux/make_ext4fs)
5. [oppo_decrypt](https://github.com/bkerler/oppo_decrypt)
6. [lpunpack](https://github.com/unix3dgforce/lpunpack)
7. [brotli](https://github.com/google/brotli)
8. [rich](https://github.com/Textualize/rich/)
9. [context_patch](https://github.com/ColdWindScholar/context_patch)
10. [erofs-utils](https://github.com/sekaiacg/erofs-utils/)
11. [Magisk_Patch_Python](https://github.com/ColdWindScholar/Magisk_Patch_Python)
12. And More...
#### **合作伙伴**
1. Sakura
2. Affggh
3. Yeliqin666
4. [qlenlen - For F2FS REPACK](https://github.com/qlenlen)
#### **支持系统**
1. Android-(Termux) | ARM64
2. Windows(7 AND NEWER) | AMD64 X86 ARM64
3. Linux | ARM64 X86_64
4. Macos | ARM64(by sewzj) X86_64
####  **安装教程** 

    git clone https://github.com/ColdWindScholar/TIK
    cd TIK
    chmod a+x ./*
    python build.py
    sudo ./run

####  **使用说明** 

1.  Termux内所有操作尽量【 **Warning** **不要使用系统root功能** 】， PC端需要root权限(sudo，其实不需要也行) 且最好不要在【root用户登录状态下】运行此工具，以免打包后刷入手机出现权限问题 ！

2.   **关于Proot下选择文件** 
    - 请将zip文件或mpk插件等放置在【 **内置存储 工具资源目录** 】，工具会自动查找（设置中可以修改)

3.  手机端termux proot ubuntu下工具目录： 【**/data/data/com.termux/files/home/ubuntu/root/TIK** 】

4.  **请勿删除【工程目录/config文件夹】，打包时所需的文件信息都在此处，工具会自动修改大小以适配动态分区！（可自行调整）

5.  由于手机性能、proot效率、工作模式( **如打包img前自动比对fs_config，不会立刻打包** )等原因工作时可能出现卡顿，保持耐心，等待片刻即可；

6.  删除文件尽量在【Termux或proot ubuntu】执行 【rm -rf 文件、文件夹】 【 **不要使用系统root功能 ** 】

7.   **为保证工具正常运行，请保证强条件：工作路径中不得含有中文字符、空格，工程文件夹不得有空格或其他特殊符号 ，文件名不要过长！！！** 

8.   **动态分区不允许单刷其中的任何分区（除非在fastbootd下），具体请参见安卓文档** 

9. 手机上使用工具时如果使用 **系统ROOT** 对工程目录下进行了操作(如： **添加文件，修改文件** )，请记得给操作过的文件或文件夹  **777**  满权！！！

10. **关于一键生成“卡线一体包”的说明**：个别厂商对一些分区有所限制，目前更推荐在fastbootd下进行刷入以维护super信息的完整性


####  **参与维护途径**

  请发起PR，我们将会第一时间查看并处理，感谢所有为本项目提供支持的开发者/爱好者！ 


####  **交流反馈** 

  QQ群：[932388310](#交流反馈)
  开发者QQ群：777617022 

####  **免责声明** 

1.  本工具在Termux proot环境中运行，不需要root权限 【 **请在Termux中慎用系统root功能** 】 ！！！

2.  此工具不含任何【破坏系统、获取数据】等其他不法代码 ！！！

3.  **如果由于用户利用root权限对工具中的工程目录进行操作导致的数据丢失、损毁，不承担任何责任 ！！！** 
####  [TIK5.0](https://github.com/ColdWindScholar/TIK) 
#### ColdWindScholar(3590361911@qq.com).All rights reserved.
