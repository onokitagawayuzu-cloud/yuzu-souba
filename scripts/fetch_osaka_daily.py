# -*- coding: utf-8 -*-
"""大阪市中央卸売市場(本場・東部)のゆず日別取扱データを取得する。

データ源: https://www.shijou.city.osaka.jp/sikyo/nippou/hinmoku.html
CSVのURLは規則的:
  /data/webroot/nippou/hinmoku/YYYYMM/YYYYMMDD-{ichiba}1-1-39300000.csv
  ichiba: 1=本場, 2=東部  /  39300000 = ゆず(品目コード13930)
"""
import csv
import io
import sys
from datetime import timedelta

from common import DATA_DIR, http_get, jst_today, load_json, save_json, to_num

BASE = "https://www.shijou.city.osaka.jp/data/webroot/nippou/hinmoku"
MARKETS = {"1": "honjo", "2": "tobu"}
OUT = DATA_DIR / "osaka_daily.json"

# 何日前まで遡って取得するか(過去分は市場サイト側で順次消える可能性があるため
# 一度取れた分はJSONに残し続ける)
BACKFILL_DAYS = 60


def parse_daily_csv(text):
    """日報CSVから {total_kg, origins:[{name,qty,seri,aitai,avg}]} を返す。"""
    rows = list(csv.reader(io.StringIO(text)))
    origins = []
    total = None
    in_table = False
    for r in rows:
        if not r or not r[0].strip():
            continue
        c0 = r[0].strip()
        if c0.startswith("（総取扱量"):
            total = to_num(c0.split("kg")[0].replace("（総取扱量", ""))
            continue
        if c0.startswith("産"):
            in_table = True
            continue
        if in_table:
            if c0.startswith(("※", "◇", "【", "★")):
                break
            vals = [to_num(x) for x in r[1:]]
            if len(r) >= 11 and to_num(r[1]) is not None:
                origins.append({
                    "name": c0,
                    "qty": to_num(r[1]),
                    "seri": {"high": to_num(r[4]), "mid": to_num(r[5]), "low": to_num(r[6])},
                    "aitai": {"high": to_num(r[7]), "mid": to_num(r[8]), "low": to_num(r[9])},
                    "avg": to_num(r[10]),
                })
    if not origins:
        return None
    return {"total_kg": total, "origins": origins}


def main():
    data = load_json(OUT)
    today = jst_today()
    added = 0
    for delta in range(BACKFILL_DAYS + 1):
        d = today - timedelta(days=delta)
        key = d.strftime("%Y-%m-%d")
        for icode, mname in MARKETS.items():
            if data.get(key, {}).get(mname):
                continue  # 取得済み
            url = f"{BASE}/{d:%Y%m}/{d:%Y%m%d}-{icode}1-1-39300000.csv"
            b = http_get(url)
            if b is None:
                continue  # データなし(休市・入荷なし)
            parsed = parse_daily_csv(b.decode("cp932", errors="replace"))
            if parsed:
                data.setdefault(key, {})[mname] = parsed
                added += 1
                print(f"  {key} {mname}: {parsed['total_kg']}kg")
    save_json(OUT, data)
    print(f"大阪日次: {added}件 追加 (合計 {len(data)}日分)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
