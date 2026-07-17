# -*- coding: utf-8 -*-
"""data/*.json を web/data.js にまとめる(ダブルクリックで開けるようにするため)。"""
import json
import sys
from datetime import datetime

from common import DATA_DIR, JST, WEB_DIR, load_json


def main():
    monthly = load_json(DATA_DIR / "monthly.json")
    daily = load_json(DATA_DIR / "osaka_daily.json")
    seika = load_json(DATA_DIR / "tokyo_seika_daily.json")
    payload = {
        "monthly": monthly,
        "osaka_daily": daily,
        "tokyo_seika_daily": seika,
        "updated": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
    }
    out = WEB_DIR / "data.js"
    out.write_text("window.YUZU_DATA = " + json.dumps(payload, ensure_ascii=False) + ";\n",
                   encoding="utf-8")
    print(f"web/data.js を更新しました ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
