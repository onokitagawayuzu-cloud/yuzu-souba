# -*- coding: utf-8 -*-
"""全データを更新する(GitHub Actions から毎日 8時・12時に呼ばれる)。

取得先ごとの成否を data/fetch_status.json に残し、同じ取得先が
STOP_RUNS 回続けて失敗したら「止まった」とみなして GitHub Actions に伝える
(.github/workflows/update.yml の notify ジョブが失敗し、GitHub からメールが届く)。
メールは止まったときに1回だけ。取れるようになったら次に止まったときまた1回。
"""
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

import fetch_osaka_daily
import fetch_tokyo_seika
import fetch_ota
import fetch_tama
import fetch_monthly
import fetch_chusei
import build_datajs
from common import DATA_DIR, JST, load_json, save_json

# (取得先ID, 説明, モジュール) の実行リスト。1つ失敗しても他は続行する
# ※対象は東京・大阪・京都のみ(2026-07 尾野さん方針: 相場観の記録用)
# ※板橋(東京豊島青果)は2026-10-01の合併で市況PDFが無くなったため外した(2026-11-03 尾野さん)
STEPS = [
    ("osaka_daily", "大阪の日別データ", fetch_osaka_daily),
    ("tokyo_seika", "東京シティ青果(豊洲)の相場表", fetch_tokyo_seika),
    ("ota", "東京青果(大田)の相場表", fetch_ota),
    ("tama", "東京多摩青果の市況", fetch_tama),
    ("monthly", "東京・大阪・京都の月次データ", fetch_monthly),
    ("chusei", "大阪中央青果の旬別データ", fetch_chusei),
]
MONTHLY_NAMES = {"tokyo": "東京の月次データ", "osaka": "大阪の月次データ",
                 "kyoto": "京都の月次データ"}

# 朝・昼の2回×2日。1回だけのつまずき(通信の混雑)では知らせない
STOP_RUNS = 4
STATUS_FILE = DATA_DIR / "fetch_status.json"


def record_results(status, results, now):
    """results={取得先ID: (説明, エラー文 or None)} を status に反映し、
    今回はじめて「止まった」になった取得先の説明を返す。"""
    newly_stopped = []
    for key, (name, err) in results.items():
        s = status.setdefault(key, {"fail_streak": 0, "notified": False})
        s["name"] = name
        if err is None:
            s.update(fail_streak=0, notified=False, last_ok=now, last_error=None)
            continue
        s["fail_streak"] = s.get("fail_streak", 0) + 1
        s["last_error"] = err
        if s["fail_streak"] >= STOP_RUNS and not s.get("notified"):
            s["notified"] = True
            newly_stopped.append(name)
    return newly_stopped


def main():
    results = {}
    for key, name, mod in STEPS:
        print(f"=== {name}を取得中...")
        try:
            ret = mod.main()
        except Exception as e:
            print(f"  !! {name} でエラー: {e}")
            results[key] = (name, str(e))
            continue
        if key == "monthly":
            failed = ret or {}
            for city, cname in MONTHLY_NAMES.items():
                results[f"monthly_{city}"] = (cname, failed.get(city))
        else:
            results[key] = (name, None)
    print("=== 表示用データを作成中...")
    build_datajs.main()

    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    status = load_json(STATUS_FILE)
    newly_stopped = record_results(status, results, now)
    save_json(STATUS_FILE, status)

    print()
    errs = [name for name, err in results.values() if err]
    if errs:
        print(f"注意: 次のデータ源でエラーがありました: {', '.join(errs)}")
    if newly_stopped:
        print(f"止まった取得先({STOP_RUNS}回続けて失敗): {'、'.join(newly_stopped)}")
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a", encoding="utf-8") as f:
                f.write(f"stopped={'、'.join(newly_stopped)}\n")
    print("更新が終わりました。")


if __name__ == "__main__":
    main()
