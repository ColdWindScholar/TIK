from time import strftime


def LOGE(info):
    print('[%s] \033[91m[ERROR]\033[0m%s\n' % (strftime('%H:%M:%S'), info))


def LOGS(info):
    print('[%s] \033[92m[SUCCESS]\033[0m%s\n' % (strftime('%H:%M:%S'), info))


def ysuc(info): print(f"\033[32m[{strftime('%H:%M:%S')}]{info}\033[0m")


def yecho(info): print(f"\033[36m[{strftime('%H:%M:%S')}]{info}\033[0m")


def ywarn(info): print(f"\033[31m{info}\033[0m")
