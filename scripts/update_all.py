# -*- coding: utf-8 -*-
"""全データを更新してダッシュボードを開く(update.batから呼ばれる)。"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import fetch_osaka_daily
import fetch_tokyo_seika
import fetch_monthly
import build_datajs


def main():
    print("=== 大阪の日別データを取得中...")
    fetch_osaka_daily.main()
    print("=== 東京シティ青果(豊洲)の相場表を取得中...")
    fetch_tokyo_seika.main()
    print("=== 4都市の月次データを取得中...")
    fetch_monthly.main()
    print("=== 表示用データを作成中...")
    build_datajs.main()
    print()
    print("更新が終わりました。")
    if "--no-open" not in sys.argv:
        print("ダッシュボードを開きます。")
        index = Path(__file__).resolve().parent.parent / "web" / "index.html"
        os.startfile(index)


if __name__ == "__main__":
    main()
