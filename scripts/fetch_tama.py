# -*- coding: utf-8 -*-
"""東京多摩青果(国立の地方卸売市場)の日次市況PDFから柚子の価格を取得する。

データ源: https://tamaseika.co.jp/
  PDF URL: /wp-content/uploads/2024/01/{YYYY}.{M}.{D}.pdf
    - 月日はゼロ埋めなし。フォルダは日付に関係なく常に /2024/01/ 固定。
    - 404なら {YYYY}.{M}.{D}-1.pdf(当日再アップ版)を試す。それも無ければ休市。
    - 404時に44KBのHTMLエラーページが返ることがあるため b'%PDF-' チェック必須。

PDFは2ページ(p1=野菜, p2=果実)で、柚子はp1に「柚 子」と分かち書きで載る。
1行に3品目分が横並びなので、空白除去後に「柚」を含む行を特定し、
NFKC正規化・「－」→「-」置換後に正規表現でトークン列を抽出する。
価格は円/箱(unit_kg入り、税込8%建値)なので kg単価に換算した値も保存する。
柚子の掲載は例年11月〜12月のみ。掲載が無い日は記録しない。
"""
import re
import sys
import tempfile
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import pdfplumber

from common import DATA_DIR, http_get, jst_today, load_json, save_json, to_num

OUT = DATA_DIR / "tama_daily.json"

# 柚 子 産地 単位kg 等級 高値 中値 安値 (中値・安値は「-」のことがある)
YUZU_RE = re.compile(
    r"柚\s*子\s+(\S+)\s+([\d.]+)\s+(\S+)\s+([\d,]+|-)\s+([\d,]+|-)\s+([\d,]+|-)"
)


def fetch_pdf(d):
    """日付dのPDFのbytesを返す。休市・未掲載はNone。"""
    base = f"https://tamaseika.co.jp/wp-content/uploads/2024/01/{d.year}.{d.month}.{d.day}"
    for url in (base + ".pdf", base + "-1.pdf"):
        b = http_get(url)
        if b is not None and b[:5] == b"%PDF-":
            return b
    return None


def parse_yuzu(pdf_bytes):
    """PDFのp1(野菜)から柚子行を抽出して dict を返す。無ければNone。"""
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(pdf_bytes)
    tmp.close()
    try:
        with pdfplumber.open(tmp.name) as pdf:
            text = pdf.pages[0].extract_text() or ""
    finally:
        Path(tmp.name).unlink(missing_ok=True)

    for raw in text.splitlines():
        # 空白全除去した文字列で柚子行かどうか判定(「柚 子」と分かち書きされるため)
        if "柚" not in raw.replace(" ", "").replace("　", ""):
            continue
        line = unicodedata.normalize("NFKC", raw).replace("－", "-")
        m = YUZU_RE.search(line)
        if not m:
            continue
        origin, unit_s, grade, high_s, mid_s, low_s = m.groups()
        unit = to_num(unit_s)
        high = to_num(high_s)
        mid = to_num(mid_s)
        low = to_num(low_s)
        return {
            "origin": origin,
            "unit_kg": unit,
            "grade": grade,
            "high": high,
            "mid": mid,
            "low": low,
            "high_per_kg": round(high / unit) if unit and high else None,
            "low_per_kg": round(low / unit) if unit and low else None,
        }
    return None


def date_range(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def target_dates():
    """取得対象の日付リスト(直近7日 + バックフィル2シーズン窓)。"""
    today = jst_today()
    dates = set(date_range(today - timedelta(days=7), today))
    dates |= set(date_range(date(2024, 10, 15), date(2025, 1, 15)))
    dates |= set(date_range(date(2025, 10, 15), date(2026, 1, 15)))
    return sorted(d for d in dates if d <= today)


def main():
    data = load_json(OUT)
    # 「柚子なし」確認済みの過去日を記録し、毎回の再ダウンロードを防ぐ
    checked = load_json(DATA_DIR / "tama_checked.json")
    today_key = jst_today().strftime("%Y-%m-%d")
    added = 0
    for d in target_dates():
        key = d.strftime("%Y-%m-%d")
        if key in data:
            continue  # 取得済みはスキップ(差分取得)
        if key in checked and key != today_key:
            continue  # 柚子なし確認済み(当日だけは再確認する)
        pdf_bytes = fetch_pdf(d)
        if pdf_bytes is None:
            checked[key] = "no-pdf"  # 休市など
            continue
        row = parse_yuzu(pdf_bytes)
        if row is None:
            checked[key] = "no-yuzu"  # 柚子の掲載なし(11〜12月以外はこれが普通)
            continue
        data[key] = row
        added += 1
        save_json(OUT, data)  # 中断に備えて逐次保存
        print(f"多摩青果 {key}: {row['origin']} {row['unit_kg']}kg {row['grade']} "
              f"高{row['high']}/中{row['mid']}/安{row['low']} "
              f"(kg換算 高{row['high_per_kg']}/安{row['low_per_kg']}円)")
    save_json(DATA_DIR / "tama_checked.json", checked)
    print(f"多摩青果: 新規{added}件 / 合計{len(data)}件")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
