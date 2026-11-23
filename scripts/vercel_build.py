"""
Vercel のビルド時に static/ を public/static/ へコピーし、CDN から配信させる
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    target = ROOT / "public" / "static"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(ROOT / "static", target)
    print(f"static/ を {target.relative_to(ROOT)} にコピーしました")


if __name__ == "__main__":
    main()
