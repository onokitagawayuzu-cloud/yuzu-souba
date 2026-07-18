# -*- coding: utf-8 -*-
"""東京豊島青果(板橋市場)の市況概況PDFから柚子の価格を取得する。

データ源: http://www.toshimaseika.co.jp/pdf_file/iysikyo.pdf
  URL固定(httpのみ)・毎営業日上書きで当日分のみ掲載 → 毎日取得して貯める。
  User-Agent Mozilla/5.0 が必要(common.pyのhttp_getで対応済み)。

PDFは1ページ・2段組。extract_text()では左右段が連結されてしまうため、
extract_words(x_tolerance=1.5) の座標をヘッダー列(実測x0)に割り当てて解析する。
価格の数字は右寄せなので、中心xではなく「語のx0を隣接ヘッダーx0の中点で
区切ったゾーン」に割り当てる(実測で全列一致を確認)。

列: 商品名/産地/等階級/形態/量目kg/高値/中値/安値/前日比(△/○記号)。
価格は税抜・荷姿(量目kg)あたり → kg換算値も保存する。
柚子行は通年掲載されるが、販売の無い日は価格欄が空白 → その日は記録しない。
日付はPDF内の「YYYY年MM月DD日」を使い、読めなければ日本時間の今日。
"""
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

import pdfplumber

from common import DATA_DIR, http_get, jst_today, load_json, save_json, to_num

URL = "http://www.toshimaseika.co.jp/pdf_file/iysikyo.pdf"
OUT = DATA_DIR / "itabashi_daily.json"

# 列名と、ヘッダー語の実測x0(左段・右段)
COLS = ["name", "origin", "grade", "pkg", "unit", "high", "mid", "low", "diff"]
LEFT_X = [34.4, 92.6, 126.6, 153.3, 183.1, 221.0, 263.1, 305.3, 337.9]
RIGHT_X = [380.4, 438.6, 472.6, 499.3, 529.1, 567.0, 609.1, 651.2, 683.9]
SIDE_SPLIT = 365.0  # これより左が左段、右が右段(左段のx1最大≈354、右段のx0最小≈378)

DATE_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")


def norm(s):
    """全角英数を半角に正規化し、空白(半角・全角)を全除去する。"""
    return unicodedata.normalize("NFKC", s).replace(" ", "").replace("　", "")


def assign_columns(side_words, xs):
    """同一行・同一段の語を、x0の属する列ゾーンに割り当てて連結する。

    ゾーンの区切りは隣接ヘッダーx0の中点。価格の数字は右寄せだが、
    実測では3〜5桁の価格すべてこの方式で正しい列に入る。
    """
    bounds = [(xs[i] + xs[i + 1]) / 2 for i in range(len(xs) - 1)]
    row = {c: "" for c in COLS}
    for w in sorted(side_words, key=lambda w: w["x0"]):
        i = 0
        while i < len(bounds) and w["x0"] >= bounds[i]:
            i += 1
        row[COLS[i]] += norm(w["text"])
    # 極端に短い価格が前日比ゾーンへ食い込んだ場合の救済(前日比は△/○記号のみ)
    if row["diff"] and not row["low"] and to_num(row["diff"]) is not None:
        row["low"], row["diff"] = row["diff"], ""
    return row


def parse_pdf(pdf_path):
    """PDFから (日付キー or None, 柚子行のdictリスト) を返す。"""
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words(x_tolerance=1.5)

    # 日付: ヘッダー部(上端50pt以内)の語から「YYYY年MM月DD日」を探す
    date_key = None
    header_text = norm("".join(w["text"] for w in words if w["top"] < 50))
    m = DATE_RE.search(header_text)
    if m:
        date_key = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # top±2ptで同一行にまとめる
    words.sort(key=lambda w: (w["top"], w["x0"]))
    lines = []
    for w in words:
        if lines and abs(w["top"] - lines[-1][0]["top"]) <= 2:
            lines[-1].append(w)
        else:
            lines.append([w])

    # 各行を左段・右段に分け、商品名に「柚子」を含む行を解析
    # (文字が分かち書きされても、ゾーン内で連結するので空白除去後に判定できる)
    yuzu_rows = []
    for line in lines:
        for xs, side_words in (
            (LEFT_X, [w for w in line if w["x0"] < SIDE_SPLIT]),
            (RIGHT_X, [w for w in line if w["x0"] >= SIDE_SPLIT]),
        ):
            if not side_words:
                continue
            row = assign_columns(side_words, xs)
            if "柚子" not in row["name"]:
                continue
            unit = to_num(row["unit"])
            high = to_num(row["high"])
            mid = to_num(row["mid"])
            low = to_num(row["low"])
            yuzu_rows.append({
                "origin": row["origin"] or None,
                "grade": row["grade"] or None,
                "pkg": row["pkg"] or None,
                "unit_kg": unit,
                "high": high,
                "mid": mid,
                "low": low,
                "high_per_kg": int(round(high / unit)) if high and unit else None,
                "low_per_kg": int(round(low / unit)) if low and unit else None,
            })
    return date_key, yuzu_rows


def main():
    data = load_json(OUT)

    b = http_get(URL)
    if b is None or not b.startswith(b"%PDF-"):
        print("板橋市況: PDFを取得できず(エラーページ等)")
        return

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(b)
    tmp.close()
    try:
        date_key, rows = parse_pdf(tmp.name)
    finally:
        Path(tmp.name).unlink(missing_ok=True)

    if date_key is None:
        date_key = jst_today().strftime("%Y-%m-%d")

    if date_key in data:
        print(f"板橋市況: {date_key} は取得済み")
        return

    if not rows:
        print(f"板橋市況: {date_key} PDFに柚子行なし")
        return

    # 価格が1つも無い日(販売なし)は記録しない
    priced = [r for r in rows if r["high"] is not None or r["mid"] is not None
              or r["low"] is not None]
    if not priced:
        r = rows[0]
        print(f"板橋市況: {date_key} 柚子({r['origin']} {r['grade']} {r['pkg']} "
              f"{r['unit_kg']}kg)は価格欄が空白(販売なし)→記録しない")
        return

    if len(priced) > 1:
        print(f"板橋市況: 柚子行が{len(priced)}行あるため最初の行のみ記録")
    rec = priced[0]
    data[date_key] = rec
    print(f"  板橋 {date_key}: {rec['origin']} {rec['grade']} {rec['pkg']} "
          f"高値{rec['high']}円/{rec['unit_kg']}kg (={rec['high_per_kg']}円/kg) "
          f"安値{rec['low']}円 (={rec['low_per_kg']}円/kg)")
    save_json(OUT, data)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
