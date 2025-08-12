import os
import sys
import shutil


def ensure_dir(path: str) -> None:
    try:
        if path:
            os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def try_copy(src: str, dst: str) -> bool:
    try:
        if not src or not os.path.exists(src):
            return False
        dst_dir = os.path.dirname(dst)
        ensure_dir(dst_dir)
        if not os.path.exists(dst):
            shutil.copyfile(src, dst)
        return True
    except Exception:
        return False


def get_appdata_dir() -> str:
    if os.name == 'nt':
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    else:
        base = os.path.join(os.path.expanduser('~'), '.local', 'share')
    target = os.path.join(base, 'NewsScraper')
    ensure_dir(target)
    return target


def main():
    meipass = getattr(sys, '_MEIPASS', '')
    src = os.path.join(meipass, 'lp_list.json') if meipass else ''

    # 1) Try current working directory (matches app's open('lp_list.json'))
    cwd_dst = os.path.join(os.getcwd(), 'lp_list.json')
    if try_copy(src, cwd_dst):
        return

    # 2) Fallback to APPDATA and chdir there so app can use relative paths
    appdata = get_appdata_dir()
    appdata_dst = os.path.join(appdata, 'lp_list.json')
    if try_copy(src, appdata_dst):
        try:
            os.chdir(appdata)
        except Exception:
            pass


main()


