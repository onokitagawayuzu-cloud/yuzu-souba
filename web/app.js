/* 柚子 市場単価ダッシュボード */
(function () {
  "use strict";
  const D = window.YUZU_DATA || {};
  document.getElementById("updated").textContent =
    D.updated ? "(データ更新: " + D.updated + ")" : "";

  const css = (name) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  const CITIES = [
    { key: "tokyo", label: "東京", varName: "--s-tokyo" },
    { key: "osaka", label: "大阪", varName: "--s-osaka" },
    { key: "kyoto", label: "京都", varName: "--s-kyoto" },
    { key: "nagoya", label: "名古屋", varName: "--s-nagoya" },
  ];
  const OSAKA_MKTS = [
    { key: "honjo", label: "本場", varName: "--s-honjo" },
    { key: "tobu", label: "東部", varName: "--s-tobu" },
  ];

  /* ---------- タブ ---------- */
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    });
  });

  const fmt = (n) => (n == null ? "-" : Math.round(n).toLocaleString("ja-JP"));

  /* ---------- 汎用折れ線チャート (SVG) ---------- */
  function lineChart(el, series, xLabels, opts) {
    opts = opts || {};
    const W = 900, H = 320, padL = 56, padR = 16, padT = 14, padB = 34;
    const iw = W - padL - padR, ih = H - padT - padB;
    const all = series.flatMap((s) => s.values.filter((v) => v != null));
    if (!all.length) { el.textContent = "データがありません(まだ蓄積中です)"; return; }
    const ymax = Math.max(...all) * 1.08;
    const ymin = 0;
    const n = xLabels.length;
    const X = (i) => padL + (n <= 1 ? iw / 2 : (i * iw) / (n - 1));
    const Y = (v) => padT + ih - ((v - ymin) / (ymax - ymin)) * ih;

    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);

    // 横グリッド+目盛り
    const ticks = 4;
    for (let t = 0; t <= ticks; t++) {
      const v = ymin + ((ymax - ymin) * t) / ticks;
      const y = Y(v);
      const line = document.createElementNS(ns, "line");
      line.setAttribute("x1", padL); line.setAttribute("x2", W - padR);
      line.setAttribute("y1", y); line.setAttribute("y2", y);
      line.setAttribute("stroke", t === 0 ? css("--axis") : css("--grid"));
      line.setAttribute("stroke-width", "1");
      svg.appendChild(line);
      const txt = document.createElementNS(ns, "text");
      txt.setAttribute("x", padL - 8); txt.setAttribute("y", y + 4);
      txt.setAttribute("text-anchor", "end");
      txt.setAttribute("font-size", "11"); txt.setAttribute("fill", css("--muted"));
      txt.textContent = fmt(v);
      svg.appendChild(txt);
    }
    // X軸ラベル(間引き)
    const step = Math.max(1, Math.ceil(n / 12));
    for (let i = 0; i < n; i += step) {
      const txt = document.createElementNS(ns, "text");
      txt.setAttribute("x", X(i)); txt.setAttribute("y", H - 10);
      txt.setAttribute("text-anchor", "middle");
      txt.setAttribute("font-size", "11"); txt.setAttribute("fill", css("--muted"));
      txt.textContent = xLabels[i];
      svg.appendChild(txt);
    }
    // 折れ線
    series.forEach((s) => {
      const color = css(s.varName);
      let d = "", pen = false;
      s.values.forEach((v, i) => {
        if (v == null) { pen = false; return; }
        d += (pen ? "L" : "M") + X(i).toFixed(1) + " " + Y(v).toFixed(1) + " ";
        pen = true;
      });
      const path = document.createElementNS(ns, "path");
      path.setAttribute("d", d.trim());
      path.setAttribute("fill", "none");
      path.setAttribute("stroke", color);
      path.setAttribute("stroke-width", "2");
      path.setAttribute("stroke-linejoin", "round");
      svg.appendChild(path);
      // 点(データが飛び飛びでも見えるように)
      s.values.forEach((v, i) => {
        if (v == null) return;
        const c = document.createElementNS(ns, "circle");
        c.setAttribute("cx", X(i)); c.setAttribute("cy", Y(v));
        c.setAttribute("r", n > 120 ? "1.5" : "3");
        c.setAttribute("fill", color);
        c.setAttribute("stroke", css("--surface"));
        c.setAttribute("stroke-width", n > 120 ? "0.5" : "1.5");
        svg.appendChild(c);
      });
    });

    // ホバー: 縦線+ツールチップ
    const cross = document.createElementNS(ns, "line");
    cross.setAttribute("y1", padT); cross.setAttribute("y2", padT + ih);
    cross.setAttribute("stroke", css("--axis"));
    cross.setAttribute("stroke-width", "1");
    cross.setAttribute("visibility", "hidden");
    svg.appendChild(cross);

    const tip = document.createElement("div");
    tip.className = "tooltip";
    el.appendChild(svg);
    el.appendChild(tip);

    svg.addEventListener("mousemove", (ev) => {
      const rect = svg.getBoundingClientRect();
      const sx = ((ev.clientX - rect.left) / rect.width) * W;
      let idx = Math.round(((sx - padL) / iw) * (n - 1));
      idx = Math.max(0, Math.min(n - 1, idx));
      cross.setAttribute("x1", X(idx)); cross.setAttribute("x2", X(idx));
      cross.setAttribute("visibility", "visible");
      let html = `<div class="tt-title">${opts.tipTitle ? opts.tipTitle(idx) : xLabels[idx]}</div>`;
      series.forEach((s) => {
        const v = s.values[idx];
        if (v == null) return;
        html += `<div class="tt-row"><span class="swatch" style="background:${css(s.varName)}"></span>${s.label}: <b>${fmt(v)}</b>${opts.unit || ""}</div>`;
      });
      tip.innerHTML = html;
      tip.style.display = "block";
      const px = (X(idx) / W) * rect.width;
      tip.style.left = Math.min(px + 12, rect.width - tip.offsetWidth - 4) + "px";
      tip.style.top = "10px";
    });
    svg.addEventListener("mouseleave", () => {
      tip.style.display = "none";
      cross.setAttribute("visibility", "hidden");
    });
  }

  function renderLegend(el, series) {
    el.innerHTML = series
      .map((s) => `<span class="key"><span class="swatch" style="background:${css(s.varName)}"></span>${s.label}</span>`)
      .join("");
  }

  /* ---------- 日次タブ: 大阪(実勢) ---------- */
  (function dailyOsaka() {
    const daily = D.osaka_daily || {};
    const dates = Object.keys(daily).sort();
    if (!dates.length) return;

    const wavg = (m) => {
      if (!m) return null;
      let q = 0, a = 0;
      m.origins.forEach((o) => {
        if (o.qty != null && o.avg != null) { q += o.qty; a += o.qty * o.avg; }
      });
      return q ? a / q : null;
    };

    const series = OSAKA_MKTS.map((mk) => ({
      label: mk.label, varName: mk.varName,
      values: dates.map((d) => wavg(daily[d][mk.key])),
    }));
    const labels = dates.map((d) => d.slice(5).replace("-", "/"));
    lineChart(document.getElementById("chart-daily"), series, labels, {
      unit: "円/kg",
      tipTitle: (i) => dates[i],
    });
    renderLegend(document.getElementById("legend-daily"), series);

    // 直近テーブル(新しい順に15日分)
    const rows = [];
    dates.slice(-15).reverse().forEach((d) => {
      OSAKA_MKTS.forEach((mk) => {
        const m = daily[d][mk.key];
        if (!m) return;
        m.origins.forEach((o, i) => {
          rows.push(
            `<tr><td>${i === 0 ? d + " " + mk.label : ""}</td>` +
            `<td>${o.name}</td><td>${fmt(o.qty)} kg</td>` +
            `<td>${fmt(o.seri && o.seri.high)}</td><td>${fmt(o.aitai && o.aitai.high)}</td>` +
            `<td><b>${fmt(o.avg)}</b></td></tr>`
          );
        });
      });
    });
    document.getElementById("table-daily").innerHTML =
      `<tr><th>日付・市場</th><th>産地</th><th>数量</th><th>せり高値</th><th>相対高値</th><th>平均(円/kg)</th></tr>` +
      rows.join("");
  })();

  /* ---------- 日次タブ: 東京4社の相場表(建値) ---------- */
  (function dailyTatene() {
    const seika = D.tokyo_seika_daily || {};
    const ota = D.ota_daily || {};
    const itabashi = D.itabashi_daily || {};
    const tama = D.tama_daily || {};

    // 豊洲: 複数行があれば price_per_kg の最小値を代表に
    const seikaVal = (d) => {
      const rows = seika[d];
      if (!rows || !rows.length) return null;
      const vals = rows.map((r) => r.price_per_kg).filter((v) => v != null);
      return vals.length ? Math.min(...vals) : null;
    };

    const SOURCES = [
      { label: "豊洲(シティ青果)", varName: "--s-toyosu", data: seika, val: seikaVal },
      { label: "大田(東京青果)", varName: "--s-ota", data: ota, val: (d) => ota[d] && ota[d].high_per_kg },
      { label: "板橋(豊島青果)", varName: "--s-itabashi", data: itabashi, val: (d) => itabashi[d] && itabashi[d].high_per_kg },
      { label: "多摩(多摩青果)", varName: "--s-tama", data: tama, val: (d) => tama[d] && tama[d].high_per_kg },
    ];
    const dates = [...new Set(SOURCES.flatMap((s) => Object.keys(s.data)))].sort();
    if (!dates.length) return;

    const series = SOURCES.map((s) => ({
      label: s.label, varName: s.varName,
      values: dates.map((d) => s.val(d) || null),
    }));
    // シーズンをまたぐので年入りラベル(例: 25/12/26)
    const labels = dates.map((d) => d.slice(2).replace(/-/g, "/"));
    lineChart(document.getElementById("chart-tatene"), series, labels, {
      unit: "円/kg", tipTitle: (i) => dates[i],
    });
    renderLegend(document.getElementById("legend-tatene"), series);

    // 相場表テーブル(新しい順に10日分)
    const rows = [];
    dates.slice(-10).reverse().forEach((d) => {
      (seika[d] || []).forEach((r) => {
        rows.push(`<tr><td>${d} 豊洲</td><td>${r.origin} ${r.spec || ""}</td>` +
          `<td>${r.unit_kg}kg入</td><td>${fmt(r.price)}</td><td><b>${fmt(r.price_per_kg)}</b></td></tr>`);
      });
      if (ota[d]) {
        const r = ota[d];
        rows.push(`<tr><td>${d} 大田</td><td>${r.origin}</td>` +
          `<td>${r.unit_kg}kg入</td><td>${fmt(r.high)}</td><td><b>${fmt(r.high_per_kg)}</b></td></tr>`);
      }
      if (itabashi[d]) {
        const r = itabashi[d];
        rows.push(`<tr><td>${d} 板橋</td><td>${r.origin} ${r.grade || ""}${r.pkg || ""}</td>` +
          `<td>${r.unit_kg}kg入</td><td>${fmt(r.high)}</td><td><b>${fmt(r.high_per_kg)}</b></td></tr>`);
      }
      if (tama[d]) {
        const r = tama[d];
        rows.push(`<tr><td>${d} 多摩</td><td>${r.origin} ${r.grade || ""}</td>` +
          `<td>${r.unit_kg}kg入</td><td>${fmt(r.high)}</td><td><b>${fmt(r.high_per_kg)}</b></td></tr>`);
      }
    });
    document.getElementById("table-tatene").innerHTML =
      `<tr><th>日付・市場</th><th>産地・規格</th><th>荷姿</th><th>建値(円/箱)</th><th>kg換算(円/kg)</th></tr>` +
      rows.join("");
  })();

  /* ---------- 月次タブ: 4都市 ---------- */
  (function monthly() {
    const M = D.monthly || {};
    const months = [...new Set(CITIES.flatMap((c) => Object.keys(M[c.key] || {})))].sort();
    if (!months.length) return;
    const labels = months.map((m) => (m.endsWith("-01") ? m : m.slice(5)));

    const priceSeries = CITIES.map((c) => ({
      label: c.label, varName: c.varName,
      values: months.map((m) => (M[c.key] && M[c.key][m] ? M[c.key][m].price : null)),
    }));
    lineChart(document.getElementById("chart-monthly"), priceSeries, labels, {
      unit: "円/kg", tipTitle: (i) => months[i],
    });
    renderLegend(document.getElementById("legend-monthly"), priceSeries);

    const qtySeries = CITIES.map((c) => ({
      label: c.label, varName: c.varName,
      values: months.map((m) => (M[c.key] && M[c.key][m] ? M[c.key][m].qty : null)),
    }));
    lineChart(document.getElementById("chart-qty"), qtySeries, labels, {
      unit: "kg", tipTitle: (i) => months[i],
    });
    renderLegend(document.getElementById("legend-qty"), qtySeries);
  })();

  /* ---------- 月次タブ: 周辺市場 (大阪府・岐阜・三重) ---------- */
  (function nearby() {
    const NEARBY = [
      { key: "osakafu_monthly", label: "大阪府(茨木)", varName: "--s-osakafu" },
      { key: "gifu_monthly", label: "岐阜", varName: "--s-gifu" },
      { key: "mie_monthly", label: "三重(松阪)", varName: "--s-mie" },
    ];
    const months = [...new Set(NEARBY.flatMap((s) => Object.keys(D[s.key] || {})))].sort();
    const el = document.getElementById("chart-nearby");
    if (!months.length) { el.textContent = "データがありません(まだ蓄積中です)"; return; }
    const labels = months.map((m) => (m.endsWith("-01") ? m : m.slice(5)));
    const series = NEARBY.map((s) => ({
      label: s.label, varName: s.varName,
      values: months.map((m) => {
        const rec = (D[s.key] || {})[m];
        return rec ? rec.price : null;
      }),
    }));
    lineChart(el, series, labels, { unit: "円/kg", tipTitle: (i) => months[i] });
    renderLegend(document.getElementById("legend-nearby"), series);
  })();

  /* ---------- 月次タブ: 大阪中央青果 産地別 (2018〜) ---------- */
  (function chusei() {
    const C = D.chusei_junbetsu || {};
    const overall = C.overall || {};
    const prefs = C.prefectures || {};
    const el = document.getElementById("chart-chusei");
    const months = [...new Set([
      ...Object.keys(overall),
      ...Object.keys(prefs).flatMap((p) => Object.keys(prefs[p] || {})),
    ])].sort();
    if (!months.length) { el.textContent = "データがありません(まだ蓄積中です)"; return; }
    const labels = months.slice();  // 長期系列なので常に YYYY-MM 表記

    const total = (rec) => (rec && rec.total ? rec.total.price : null);
    const series = [
      { label: "全体平均", varName: "--s-ch-all",
        values: months.map((m) => total(overall[m])) },
      { label: "徳島産", varName: "--s-ch-tokushima",
        values: months.map((m) => total((prefs["徳島"] || {})[m])) },
      { label: "高知産", varName: "--s-ch-kochi",
        values: months.map((m) => total((prefs["高知"] || {})[m])) },
      { label: "和歌山産", varName: "--s-ch-wakayama",
        values: months.map((m) => total((prefs["和歌山"] || {})[m])) },
    ];
    lineChart(el, series, labels, { unit: "円/kg", tipTitle: (i) => months[i] });
    renderLegend(document.getElementById("legend-chusei"), series);
  })();

  /* ---------- 月次タブ: 最新月テーブル (7市場) ---------- */
  (function latestTable() {
    const M = D.monthly || {};
    const ROWS = [
      { label: "東京(11市場計)", data: M.tokyo },
      { label: "大阪市(本場+東部)", data: M.osaka },
      { label: "京都(第一市場)", data: M.kyoto },
      { label: "名古屋(本場+北部)", data: M.nagoya },
      { label: "大阪府(茨木)", data: D.osakafu_monthly },
      { label: "岐阜", data: D.gifu_monthly },
      { label: "三重(松阪)", data: D.mie_monthly },
    ];
    const rows = ROWS.map((r) => {
      const cm = r.data || {};
      const ms = Object.keys(cm).sort();
      if (!ms.length) return "";
      const last = ms[ms.length - 1];
      const cur = cm[last];
      const prevYm = (parseInt(last.slice(0, 4)) - 1) + last.slice(4);
      let prevPrice = cm[prevYm] && cm[prevYm].price;
      if (prevPrice == null && cur.prev_year) prevPrice = cur.prev_year.price;
      let yoy = "-";
      if (prevPrice) {
        const pct = ((cur.price - prevPrice) / prevPrice) * 100;
        const cls = pct >= 0 ? "up" : "down";
        yoy = `<span class="${cls}">${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%</span>`;
      }
      return `<tr><td>${r.label}</td><td>${last}</td><td>${fmt(cur.qty)} kg</td>` +
             `<td><b>${fmt(cur.price)}</b> 円/kg</td><td>${yoy}</td></tr>`;
    });
    document.getElementById("table-monthly").innerHTML =
      `<tr><th>市場</th><th>最新月</th><th>取扱数量</th><th>平均単価</th><th>単価 前年同月比</th></tr>` +
      rows.join("");
  })();
})();
