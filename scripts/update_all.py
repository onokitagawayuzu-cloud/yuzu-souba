# -*- coding: utf-8 -*-
"""全データを更新してダッシュボードを開く(update.batから呼ばれる)。"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import fetch_osaka_daily
import fetch_tokyo_seika
import fetch_ota
import fetch_itabashi
import fetch_tama
import fetch_monthly
import fetch_osakafu
import fetch_gifu
import fetch_mie
import fetch_chusei
import build_datajs

# (説明, モジュール) の実行リスト。1つ失敗しても他は続行する
STEPS = [
    ("大阪の日別データ", fetch_osaka_daily),
    ("東京シティ青果(豊洲)の相場表", fetch_tokyo_seika),
    ("東京青果(大田)の相場表", fetch_ota),
    ("東京豊島青果(板橋)の相場表", fetch_itabashi),
    ("東京多摩青果の市況", fetch_tama),
    ("4都市の月次データ", fetch_monthly),
    ("大阪府中央卸売市場の月報", fetch_osakafu),
    ("岐阜市場の月報", fetch_gifu),
    ("三重(松阪)市場の月報", fetch_mie),
    ("大阪中央青果の旬別データ", fetch_chusei),
]


def main():
    failed = []
    for name, mod in STEPS:
        print(f"=== {name}を取得中...")
        try:
            mod.main()
        except Exception as e:
            print(f"  !! {name} でエラー: {e}")
            failed.append(name)
    print("=== 表示用データを作成中...")
    build_datajs.main()
    print()
    if failed:
        print(f"注意: 次のデータ源でエラーがありました: {', '.join(failed)}")
    print("更新が終わりました。")
    if "--no-open" not in sys.argv:
        print("ダッシュボードを開きます。")
        index = Path(__file__).resolve().parent.parent / "web" / "index.html"
        os.startfile(index)


if __name__ == "__main__":
    main()
