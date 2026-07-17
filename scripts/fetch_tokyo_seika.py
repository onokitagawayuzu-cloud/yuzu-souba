# -*- coding: utf-8 -*-
"""東京シティ青果(豊洲市場)の野菜相場表PDFからゆずの価格を取得する。

データ源: https://www.city-seika.com/today/
  PDF URL: /wp-content/uploads/YYYY/MM/yYYYYMMDD.pdf (野菜相場表)
  掲載は当日分のみ(過去分は消える)ため、毎日取得して貯める。

PDFは3段組み。pdfplumberの単語座標で列に振り分けてから
「ゆず」行(と続く〃行)を抽出する。
価格は荷姿単位(例: 0.2kg PK)なので kg単価に換算した値も保存する。
"""
import re
import sys
import tempfile
from pathlib import Path

import pdfplumber

from common import DATA_DIR, http_get, jst_today, load_json, save_json, to_num

OUT = DATA_DIR / "tokyo_seika_daily.json"
ARROWS = {"↗": "up", "↘": "down", "→": "flat", "↑": "up", "↓": "down"}


def normalize(s):
    return s.replace(" ", "").replace("　", "")


def extract_rows(pdf_path):
    """PDFから [(品名, 産地, 単位kg, 荷姿, 等階級, 市況, 価格), ...] を返す。"""
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        width = page.width
        words = page.extract_words(extra_attrs=["x0", "x1", "top"])
        # 3段組み: x位置で列0/1/2に分ける
        cols = [[], [], []]
        for w in words:
            band = min(2, int(w["x0"] / (width / 3)))
            cols[band].append(w)
        lines = []  # 列ごとに行を再構成(上から順)
        for band in cols:
            band.sort(key=lambda w: (round(w["top"] / 4), w["x0"]))
            cur_top, cur = None, []
            for w in band:
                key = round(w["top"] / 4)
                if cur_top is None or key == cur_top:
                    cur.append(w["text"])
                else:
                    lines.append(" ".join(cur))
                    cur = [w["text"]]
                cur_top = key
            if cur:
                lines.append(" ".join(cur))
    return lines


BODY_RE = re.compile(
    # 品名を除いた残り: 産地(数字が出るまで) 単位kg 荷姿等階級 価格
    r"^(?P<origin>[^\d]+?)(?P<unit>\d+(?:\.\d+)?)(?P<mid>.*?)(?P<price>\d[\d,]*)$"
)


def parse_yuzu(lines):
    """行リストからゆず行(+続きの〃行)を抜き出す。

    PDFの文字は1文字ずつに分解されるため、空白を全て除去してから
    「ゆず」で始まる行(と直後の〃行)だけを解析する。
    """
    out = []
    prev_was_yuzu = False
    for raw in lines:
        line = normalize(raw.strip())
        if line.startswith("ゆず"):
            body = line[2:]
            prev_was_yuzu = True
        elif line[:1] in ("〃", "”") and prev_was_yuzu:
            body = line[1:]
        else:
            prev_was_yuzu = False
            continue
        m = BODY_RE.match(body)
        if not m:
            continue
        unit = to_num(m.group("unit"))
        price = to_num(m.group("price"))
        mid = m.group("mid")
        trend = None
        for a, t in ARROWS.items():
            if a in mid:
                trend = t
                mid = mid.replace(a, "")
        out.append({
            "origin": m.group("origin"),
            "unit_kg": unit,
            "spec": mid,  # 荷姿+等階級 (例: PKA2L)
            "trend": trend,
            "price": price,
            "price_per_kg": round(price / unit) if unit and price else None,
        })
    return out


def fetch_for(d):
    url = f"https://www.city-seika.com/wp-content/uploads/{d:%Y}/{d:%m}/y{d:%Y%m%d}.pdf"
    b = http_get(url)
    if b is None:
        return None
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(b)
    tmp.close()
    try:
        lines = extract_rows(tmp.name)
    finally:
        Path(tmp.name).unlink(missing_ok=True)
    return parse_yuzu(lines)


def main():
    data = load_json(OUT)
    today = jst_today()
    key = today.strftime("%Y-%m-%d")
    if key in data:
        print(f"シティ青果: {key} は取得済み")
        return
    rows = fetch_for(today)
    if rows is None:
        print(f"シティ青果: {key} のPDFなし(休市など)")
        return
    if not rows:
        print(f"シティ青果: {key} PDFにゆずの掲載なし")
        data[key] = []
    else:
        data[key] = rows
        for r in rows:
            print(f"  シティ青果 {key}: {r['origin']} {r['spec']} "
                  f"{r['price']}円/{r['unit_kg']}kg (={r['price_per_kg']}円/kg)")
    save_json(OUT, data)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
