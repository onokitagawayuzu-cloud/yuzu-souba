# -*- coding: utf-8 -*-
"""大阪中央青果(大阪市中央卸売市場本場の卸売会社)の柚子 旬別データを取得する。

データ源: http://www.osaka-chusei.co.jp/ydata.html (野菜データ > 木ノ実類 > 柚子)
  PDF URL: http://www.osaka-chusei.co.jp/pdf/{西暦年}_3803.pdf (柚子=品目3803)
  2018年〜現在まで年1ファイル。当年ファイルは旬(約10日)ごとに更新される。
  1ページ=3ヶ月分(p1:1-3月 … p4:10-12月)。上段=平均単価(円/kg)・下段=入荷数量(kg)。
  下段の行に「令和N年」(年次比較)または県名のラベルが付く。
  ※卸売会社1社分のデータ。市場全体(既存の大阪日次/月次)とは別系列として扱うこと。

出力: data/chusei_junbetsu.json
  {"overall": {"YYYY-MM": {"jun1": {"price","qty"}, ..., "total": {...}}},
   "prefectures": {"徳島": {...}, ...}}
"""
import re
import sys
import tempfile
from pathlib import Path

import pdfplumber

from common import DATA_DIR, http_get, jst_today, load_json, save_json, to_num

OUT = DATA_DIR / "chusei_junbetsu.json"
START_YEAR = 2018

# 旬値のx0範囲(実測・2018〜2026年で共通のレイアウト)
# 各月ブロック: [上旬, 中旬, 下旬, 月計] / その右の前年対比・占有率列は除外
BLOCKS = [
    [(100, 145), (145, 190), (190, 232), (232, 270)],   # 1ヶ月目
    [(370, 410), (410, 455), (455, 500), (500, 540)],   # 2ヶ月目
    [(640, 678), (678, 720), (720, 760), (760, 812)],   # 3ヶ月目
]
JUN_KEYS = ["jun1", "jun2", "jun3", "total"]
PREF_RE = re.compile(r"^[ぁ-ん一-龥々]+$")
YEAR_RE = re.compile(r"(令和|平成)\s*(\d+)\s*年")


def wareki_to_year(era, n):
    return (2018 if era == "令和" else 1988) + int(n)


def row_values(ws):
    """行の単語列から {(block, jun): 数値} を返す(対比・占有率・年計列は除外)。"""
    out = {}
    for w in ws:
        v = to_num(w["text"])
        if v is None:
            continue
        for bi, cols in enumerate(BLOCKS):
            for ji, (lo, hi) in enumerate(cols):
                if lo <= w["x0"] < hi:
                    out[(bi, ji)] = v
    return out


def parse_pdf(pdf_path):
    """PDF全体から (西暦年, overall{ym:…}, prefectures{県:{ym:…}}) を返す。"""
    with pdfplumber.open(pdf_path) as pdf:
        pages = []
        year = None
        for page in pdf.pages:
            words = page.extract_words()
            rows = {}
            for w in words:
                rows.setdefault(round(w["top"] / 3), []).append(w)
            if year is None:
                text = page.extract_text() or ""
                m = YEAR_RE.search(text.replace(" ", ""))
                if m:
                    year = wareki_to_year(m.group(1), m.group(2))
            pages.append(rows)
    if year is None:
        return None, {}, {}

    overall, prefectures = {}, {}
    for pi, rows in enumerate(pages):
        months = [pi * 3 + 1, pi * 3 + 2, pi * 3 + 3]
        keys = sorted(rows)
        # 各行を (ラベル, 値dict) に変換
        parsed = []
        for k in keys:
            ws = sorted(rows[k], key=lambda w: w["x0"])
            label = "".join(w["text"] for w in ws
                            if w["x0"] < 100 and (PREF_RE.match(w["text"]) or "年" in w["text"]))
            vals = row_values(ws)
            parsed.append((k, label, vals))
        for i, (k, label, vals) in enumerate(parsed):
            if not label or not vals:
                continue
            # ラベル行=数量(下段)。直前の非ラベル数値行=単価(上段)
            price_vals = {}
            for pk, plabel, pvals in reversed(parsed[:i]):
                if k - pk > 4:
                    break
                if not plabel and pvals:
                    price_vals = pvals
                    break
            name = label.replace(" ", "")
            if "年" in name:
                m = YEAR_RE.search(name)
                if not m or wareki_to_year(m.group(1), m.group(2)) != year:
                    continue  # 過去年の比較行はスキップ(その年のPDFから取る)
                dest = overall
            elif name in ("種別", "県別", "合計"):
                continue  # 表の見出し行など
            else:
                dest = prefectures.setdefault(name, {})
            for bi, mon in enumerate(months):
                ym = f"{year:04d}-{mon:02d}"
                entry = {}
                for ji, jk in enumerate(JUN_KEYS):
                    q = vals.get((bi, ji))
                    p = price_vals.get((bi, ji))
                    if q is not None or p is not None:
                        entry[jk] = {"price": round(p) if p is not None else None,
                                     "qty": int(q) if q is not None else None}
                if entry:
                    dest.setdefault(ym, {}).update(entry)
    return year, overall, prefectures


def main():
    data = load_json(OUT)
    data.setdefault("overall", {})
    data.setdefault("prefectures", {})
    fetched_years = set(data.get("_years", []))
    this_year = jst_today().year
    for y in range(START_YEAR, this_year + 1):
        if y in fetched_years and y < this_year:
            continue  # 過去年ファイルは不変
        b = http_get(f"http://www.osaka-chusei.co.jp/pdf/{y}_3803.pdf")
        if b is None or not b.startswith(b"%PDF-"):
            continue
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(b)
        tmp.close()
        try:
            year, overall, prefs = parse_pdf(tmp.name)
        finally:
            Path(tmp.name).unlink(missing_ok=True)
        if year is None:
            print(f"  大阪中央青果 {y}: 年の判定に失敗")
            continue
        for ym, entry in overall.items():
            data["overall"][ym] = entry
        for pref, months in prefs.items():
            for ym, entry in months.items():
                data["prefectures"].setdefault(pref, {})[ym] = entry
        fetched_years.add(y)
        tot = [ym for ym in overall if overall[ym].get("total")]
        print(f"  大阪中央青果 {y}: {len(tot)}ヶ月分 (県別{len(prefs)}県)")
    data["_years"] = sorted(fetched_years)
    save_json(OUT, data)
    print(f"大阪中央青果: 月計 {len(data['overall'])}ヶ月分 蓄積")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
