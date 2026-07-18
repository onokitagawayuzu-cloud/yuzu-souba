# -*- coding: utf-8 -*-
"""東京青果(大田市場の卸最大手)の野菜相場表からゆずの建値を取得する。

データ源: https://www.tokyo-seika.co.jp/ (市況情報)
  PDF URL: 固定 https://www.tokyo-seika.co.jp/corp/wp-content/uploads/2022/11/yasaso.pdf
  毎営業日上書き・当日分のみ(過去分はどこにも残らない)ため毎日取得して蓄積する。
  ゆずの掲載は冬季(11月〜1月ごろ)のみ。価格は1.5kg箱あたり・消費税8%込みの建値。
"""
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

import pdfplumber

from common import DATA_DIR, http_get, jst_today, load_json, save_json, to_num

OUT = DATA_DIR / "ota_daily.json"
URL = "https://www.tokyo-seika.co.jp/corp/wp-content/uploads/2022/11/yasaso.pdf"

# 例: 「2025年11月14日金曜日」(西暦表記)
DATE_RE = re.compile(r"(\d{4})\s*年\s*(\d+)\s*月\s*(\d+)\s*日")


def extract(pdf_path):
    """(日付キー, ゆず行dict|None) を返す。"""
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        text = page.extract_text() or ""
        words = page.extract_words()

    # PDF内の日付
    m = DATE_RE.search(unicodedata.normalize("NFKC", text.replace(" ", "")))
    if m:
        key = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    else:
        key = jst_today().strftime("%Y-%m-%d")

    # 行グループ化(3段組みなので同一行に3品目並ぶ)
    lines = {}
    for w in words:
        lines.setdefault(round(w["top"] / 3), []).append(w)
    yuzu_tokens = None
    for _, ws in sorted(lines.items()):
        ws.sort(key=lambda w: w["x0"])
        texts = [w["text"] for w in ws]
        joined = "".join(texts)
        if "ゆず" not in joined.replace(" ", ""):
            continue
        # 「ゆず」トークンの位置以降を取る(分かち書き対応: ゆ+ず連続も探す)
        idx = None
        for i, t in enumerate(texts):
            if t.replace(" ", "") == "ゆず":
                idx = i
                break
            if t == "ゆ" and i + 1 < len(texts) and texts[i + 1] == "ず":
                idx = i + 1
                break
        if idx is None:
            continue
        yuzu_tokens = texts[idx + 1:]
        break
    if yuzu_tokens is None:
        return key, None

    # トークン列: 産地(分かち書きあり) 単位(例 １.5Ｋｇ) [等級] 高値 [中値] [安値] [市況記号]
    norm = [unicodedata.normalize("NFKC", t) for t in yuzu_tokens]
    # 単位トークン(数字+Kg)を探す
    unit_i, unit_kg = None, None
    for i, t in enumerate(norm):
        m2 = re.match(r"^([\d.]+)[KkＫ][GgＧgｇ]?$", t.replace("kg", "Kg").replace("Kg", "K"))
        m3 = re.match(r"^([\d.]+)K?g?$", t) if not m2 else m2
        m4 = re.match(r"^([\d.]+)\s*[KkＫ]", t)
        if m4:
            unit_i, unit_kg = i, float(m4.group(1))
            break
    if unit_i is None:
        return key, None
    origin = "".join(norm[:unit_i]).replace(" ", "") or "各地"
    prices = []
    trend = None
    for t in norm[unit_i + 1:]:
        v = to_num(t)
        if v is not None and v > 50:  # 等級記号(2L等)を除外
            prices.append(v)
        elif re.match(r"^[#＃↑↓→↗↘]$", t):
            trend = t
    if not prices:
        return key, None
    high = prices[0]
    mid = prices[1] if len(prices) > 1 else None
    low = prices[2] if len(prices) > 2 else None
    return key, {
        "origin": origin, "unit_kg": unit_kg,
        "high": int(high), "mid": mid, "low": low,
        "high_per_kg": round(high / unit_kg),
        "trend": trend,
    }


def main():
    data = load_json(OUT)
    b = http_get(URL)
    if b is None or not b.startswith(b"%PDF-"):
        print("大田: PDFを取得できませんでした")
        return
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(b)
    tmp.close()
    try:
        key, rec = extract(tmp.name)
    finally:
        Path(tmp.name).unlink(missing_ok=True)
    if key in data:
        print(f"大田: {key} は取得済み")
        return
    if rec is None:
        print(f"大田: {key} 相場表にゆずの掲載なし(冬季以外は正常)")
        return
    data[key] = rec
    save_json(OUT, data)
    print(f"  大田 {key}: {rec['origin']} {rec['high']}円/{rec['unit_kg']}kg (={rec['high_per_kg']}円/kg)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
