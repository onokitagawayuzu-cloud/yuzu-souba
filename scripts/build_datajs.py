# -*- coding: utf-8 -*-
"""data/*.json を web/data.js にまとめる(ダブルクリックで開けるようにするため)。"""
import json
import sys
from datetime import datetime

from common import DATA_DIR, JST, WEB_DIR, load_json


def main():
    # 表示は東京・大阪・京都のみ(名古屋等の過去データは data/ に残るが画面には出さない)
    monthly = load_json(DATA_DIR / "monthly.json")
    payload = {
        "monthly": {k: monthly.get(k, {}) for k in ("tokyo", "osaka", "kyoto")},
        "osaka_daily": load_json(DATA_DIR / "osaka_daily.json"),
        "tokyo_seika_daily": load_json(DATA_DIR / "tokyo_seika_daily.json"),
        "ota_daily": load_json(DATA_DIR / "ota_daily.json"),
        "itabashi_daily": load_json(DATA_DIR / "itabashi_daily.json"),
        "tama_daily": load_json(DATA_DIR / "tama_daily.json"),
        "chusei_junbetsu": load_json(DATA_DIR / "chusei_junbetsu.json"),
        "updated": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
    }
    out = WEB_DIR / "data.js"
    out.write_text("window.YUZU_DATA = " + json.dumps(payload, ensure_ascii=False) + ";\n",
                   encoding="utf-8")
    print(f"web/data.js を更新しました ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
