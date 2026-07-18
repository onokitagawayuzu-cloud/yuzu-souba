# 柚子 市場単価ダッシュボード (yuzu-souba)

東京・大阪・京都・名古屋の中央卸売市場で売買される**ゆずの単価**を集めて、
ブラウザで見比べられるようにするアプリです。

## 見る (スマホ・パソコン共通)

**https://onokitagawayuzu-cloud.github.io/yuzu-souba/**

データは GitHub Actions が**毎日 朝8時と昼12時(日本時間)** に自動取得して
更新します。パソコンの電源が入っていなくても動きます。
(12時の回があるのは、東京シティ青果の相場表PDFが朝10時ごろ公開で、
当日分しかサイトに残らないため)

## 手動で更新したいとき (パソコン)

`update.bat` をダブルクリック → 最新データを取ってローカルの `web\index.html` が開きます。
取得済みの日・月は飛ばすのですぐ終わります。

## 画面の見方

- **日々の単価(大阪・豊洲)** … 大阪市場(本場・東部)の日別平均単価と、
  東京・豊洲市場(東京シティ青果)の相場表のkg換算単価。
  豊洲は秀品パックの建値なので大阪の平均より高く出ます。
- **月ごとの比較(4都市)** … 4市場の月平均単価と取扱数量の推移、
  最新月の前年同月比。公式の確定統計なので正確ですが、公表まで
  1.5〜2ヶ月かかります(柚子の出荷代金の精算書が後から届くのと同じ)。

## データの出所

| 市場 | 元データ | 更新頻度 |
|---|---|---|
| 大阪市中央卸売市場(本場・東部) | 市況情報 日報・月報CSV | 日次+月次 |
| 東京シティ青果(豊洲市場の卸売会社) | 野菜相場表PDF ※当日分のみ掲載 | 日次 |
| 東京青果(大田市場の卸売会社) | 野菜相場表PDF ※当日分のみ・冬季にゆず掲載 | 日次 |
| 東京豊島青果(板橋市場の卸売会社) | 市況概況PDF ※当日分のみ | 日次 |
| 東京多摩青果(国立の地方卸売市場) | 市況情報PDF ※過去分も残存(2季遡及済み) | 日次(ゆずは11〜12月) |
| 東京都中央卸売市場(大田・豊洲など全11市場) | 市場統計情報明細データ(Excel) | 月次 |
| 京都市中央卸売市場第一市場 | 月報青果部 品目別(Excel) | 月次 |
| 名古屋市中央卸売市場(本場・北部) | 月別取扱高 品目別(Excel) | 月次 |
| 大阪府中央卸売市場(茨木) | 市場月報 品目別・産地別CSV | 月次 |
| 大阪中央青果(大阪本場の卸売会社) | 柚子 品目別データPDF(2018年〜) | 旬別(約10日) |
| 岐阜市中央卸売市場 | 市場月報PDF(産地別・前年同月つき) | 月次 |
| 三重県地方卸売市場(松阪) | 品目別取扱高PDF | 月次 |

- 卸売会社の「相場表」は建値(卸の掲示価格)で、実勢の取引平均より高めに出ます
- 大田・板橋・豊洲の相場表は当日分しかサイトに残らないため、毎日の自動取得で蓄積しています

- 単価はすべて**卸売価格(円/kg)**。小売価格ではありません
- 東京・大阪は産地別の内訳あり。名古屋は「ゆず類」としての集計
- 名古屋の単価が他都市より安く出るのは、加工向けなど品質構成の違いによるもの
  と考えられます(データ上の誤りではありません)

## しくみ

```
update.bat / GitHub Actions (毎日8時・12時 JST)
 ├─ scripts/fetch_osaka_daily.py  … 大阪の日報CSV → data/osaka_daily.json
 ├─ scripts/fetch_tokyo_seika.py  … 豊洲シティ青果PDF → data/tokyo_seika_daily.json
 ├─ scripts/fetch_ota.py          … 大田・東京青果PDF → data/ota_daily.json
 ├─ scripts/fetch_itabashi.py     … 板橋・豊島青果PDF → data/itabashi_daily.json
 ├─ scripts/fetch_tama.py         … 多摩青果PDF → data/tama_daily.json
 ├─ scripts/fetch_monthly.py      … 4都市の月次統計 → data/monthly.json
 ├─ scripts/fetch_osakafu.py      … 大阪府市場月報CSV → data/osakafu_monthly.json
 ├─ scripts/fetch_gifu.py         … 岐阜市場月報PDF → data/gifu_monthly.json
 ├─ scripts/fetch_mie.py          … 三重松阪市場月報PDF → data/mie_monthly.json
 ├─ scripts/fetch_chusei.py       … 大阪中央青果 旬別PDF → data/chusei_junbetsu.json
 └─ scripts/build_datajs.py       … JSONを web/data.js にまとめる
web/index.html + app.js           … data.js を読んでグラフ・表を表示 (GitHub Pagesで公開)
```

- 必要なもの: Python 3 と openpyxl (`pip install openpyxl`)
- 一度取得したデータは JSON に残るため、市場サイト側で古いデータが
  消えても手元には蓄積され続けます
