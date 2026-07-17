# -*- coding: utf-8 -*-
"""共通ユーティリティ: HTTP取得(文字コード対応)・JSON読み書き"""
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))


def jst_today():
    """日本時間での今日(GitHub Actionsなど海外サーバーで動かしてもズレない)。"""
    return datetime.now(JST).date()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
WEB_DIR = Path(__file__).resolve().parent.parent / "web"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) yuzu-souba/1.0 (personal use)"


def http_get(url, retries=2, sleep=0.4):
    """URLを取得してbytesを返す。404はNone。"""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as res:
                data = res.read()
            time.sleep(sleep)  # 相手サーバーに負荷をかけない
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt < retries:
                time.sleep(2)
                continue
            raise
        except Exception:
            if attempt < retries:
                time.sleep(2)
                continue
            raise


def http_get_text(url, encoding="cp932", **kw):
    b = http_get(url, **kw)
    if b is None:
        return None
    return b.decode(encoding, errors="replace")


def load_json(path):
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def save_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True),
                 encoding="utf-8")


def to_num(s):
    """' 1,137' → 1137。空やハイフンはNone。"""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return s
    s = s.replace(",", "").replace("　", "").strip()
    if not s or s in ("-", "―", "…", "***"):
        return None
    try:
        return float(s) if "." in s else int(s)
    except ValueError:
        return None
