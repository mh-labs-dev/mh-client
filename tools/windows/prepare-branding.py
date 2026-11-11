"""Convert the approved MH master to Windows application and tray assets."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BRAND = ROOT / 'branding'
SOURCE = ROOT


def main():
    master = Image.open(BRAND / 'mh-icon.png').convert('RGB')
    if master.width != master.height:
        raise ValueError('MH icon master must be square')
    master.resize((512, 512), Image.Resampling.LANCZOS).save(
        SOURCE / 'flutter/assets/mh-icon.png')
    icon = master.resize((256, 256), Image.Resampling.LANCZOS)
    for target in ('flutter/windows/runner/resources/app_icon.ico', 'res/mh-icon.ico'):
        icon.save(SOURCE / target, sizes=[(n, n) for n in (16, 24, 32, 48, 64, 128, 256)])
    master.resize((32, 32), Image.Resampling.LANCZOS).save(
        SOURCE / 'libs/portable/src/res/mh-label.png')
    print('Prepared MH Windows application, taskbar and tray icons.')


if __name__ == '__main__':
    main()
