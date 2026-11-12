(function () {
"use strict";
const D = window.DATA, M = D.meta, NS = "http://www.w3.org/2000/svg";
const KEYS = D.panels.map(p => p.key);                 // 10 charts, fixed order
const IDS = M.analogs.map(a => a.id);                  // 10 analog months, fixed order
const CUR = D.series[0], SER = {}; D.series.forEach(s => SER[s.id] = s);
const C = D.colors;
const $ = s => document.querySelector(s);
const app = $("#app");

/* ---------- text tables ---------- */
const T = {
en: {
  brand: "US Economic Cycle <b>Analogs</b>", other: "中文", explore: "Explore", how: "How it works",
  introTitle: "Which past periods look like <span class=hl>today</span>?",
  introP1: "This app charts four US macro series (unemployment rate, nonfarm payrolls, CPI and the fed funds rate) and lines today up against history. We already picked the 10 past periods closest to now. You look at the charts, drop the ones that do not look similar to you, and then see what the S&P 500 did over the following 12 months.",
  asof: d => `Data as of ${d}. Current observation month: ${M.target}.`,
  s1h: "Look", s1: "Go through 10 charts, one at a time: 4 macro and 6 market-structure.",
  s2h: "Filter", s2: "On each chart, tap a period to drop it. A dropped period disappears from every chart.",
  s3h: "See what followed", s3: "Month 0 is the last trading day of the month after the observation month (when that month's data were published). The result shows the S&P 500 over the next 12 months.",
  start: "Start exploring", howLink: "How were these 10 periods chosen?",
  aboutH: "About the data",
  about: [
    `Historical macro data are the <b>latest revised</b> values. The current (yellow) line uses data <b>as available on ${M.as_of}</b> (ALFRED vintages). This is therefore not a strict real-time backtest: investors at the time saw unrevised numbers.`,
    "The S&P 500 is a price index, dividends excluded.",
    "This is descriptive research with a small sample. It is not a forecast or investment advice.",
    "The October 2025 unemployment and CPI releases were cancelled by the government shutdown. For matching, the current series was filled with the average of neighbouring months; charts leave that month blank.",
  ],
  step: (i, n) => `Chart ${i} of ${n}`, prev: "Previous", next: "Next",
  macro: "Macro", mkt: "Market structure",
  sub: "Horizontal axis: months relative to the observation month (0 = latest). Yellow = now.",
  selected: (n, m) => `${n}/${m} selected`, nowTag: "Now", tapHint: "Tap a period to keep or drop it.",
  none: "No periods selected. Tap a period below to bring it back.", restore: "Restore all",
  barN: n => `<b>${n}</b>/10 periods kept`, seeBtn: "See S&P 500 next 12 months", keepOne: "Keep at least one period",
  gap: "Blank = no data (not zero).",
  tabs: ["Unemployment", "Payrolls", "Core CPI", "Fed funds", "Top-10 cap", "Top-10 EPS", "Nasdaq/S&P", "Cap/Equal wt", "Russell/S&P", "Breadth 200d"],
  titles: {
    unrate: "Unemployment rate (%)", pay_g6: "Nonfarm payrolls, 6-month growth (%)", core_ann6: "Core CPI, 6-month annualized (%)",
    ff: "Effective fed funds rate (%)", cap: "Top-10 share of S&P 500 market cap (month −24 = 100)",
    eps: "Top-10 share of S&P 500 earnings (month −24 = 100)", ndx_spx: "Nasdaq 100 / S&P 500 (month −24 = 100)",
    cw_ew: "S&P 500 cap-weighted / equal-weighted (month −24 = 100)", rut_spx: "Russell 2000 / S&P 500 (month −24 = 100)",
    breadth: "% of S&P 500 stocks above their 200-day average" },
  notes: {
    unrate: "Oct 2025 unemployment was never published (government shutdown), so the yellow line is blank there.",
    core_ann6: "Oct 2025 CPI was never published (government shutdown); the yellow line is blank there and six months later, where it is the base.",
    eps: "Earnings share is not available after 2026-05, so the yellow line stops early.",
    breadth: "200-day breadth data start in 2008, so earlier periods have no line.",
    pay_g6: "", ff: "", cap: "", ndx_spx: "", cw_ew: "", rut_spx: "" },
  resTitle: "S&P 500 over the <span class=hl>next 12 months</span>",
  resSub: "Month 0 = last trading day of the month after the observation month (when that month's data were published).",
  resEmpty: "No periods selected, so there is nothing to show.", back: "Back to filtering", reset: "Reset all",
  period: "Observation month", signal: "Signal date", ret: "12-mo return", mdd: "Max drawdown (12 mo)",
  avg: "Average", med: "Median", n: n => `n=${n}`, few: "few periods",
  one: "Only one period selected: average and median equal that period.",
  mddNote: "Average max drawdown is the average of each period's own worst drawdown, not the drawdown of the average path.",
  curNote: `The current state has no line here: its signal date (end of ${nextMonth(M.target)}) has not arrived yet.`,
  resFoot: "S&P 500 price index, dividends excluded. Historical macro data use latest revised values; the current line uses data as of " + M.as_of + ", so this is not a strict real-time backtest. Descriptive research, small sample, not a forecast.",
  xr: "Months after signal date", yr: "Change vs. signal-date close",
  howTitle: "How the <span class=hl>10 periods</span> are chosen",
  h: [
    ["Start with four macro series", "Unemployment rate, nonfarm payroll growth, consumer prices (CPI) and the fed funds rate, back to 1990. Source: FRED (Federal Reserve Bank of St. Louis)."],
    ["Take the current window", w => `The last 12 months of each series (${w}), described by where it started and how it moved: its direction, speed and shape.`],
    ["Cut history into 12-month windows and line them up", n => `Every month since 1990 gets its own 12-month window ending in that month, ${n} candidate windows in all. Each one is compared with the current window point by point, starting from the same zero.`],
    ["Compare all four indicators together", "Direction (up or down), speed (how fast) and shape (steady, accelerating or turning). Each series is put on a comparable scale so none dominates. The score weighs employment 40% (unemployment and payrolls), inflation 30% (headline and core CPI) and policy 30% (fed funds). Unemployment and the fed funds rate also get a small weight (15% of their group) on the level, not only the trend. Candidates where unemployment or the fed funds rate moved the opposite way from today are removed first."],
    ["Rank and keep the closest", "The lower the combined distance, the closer the match. We keep the 10 best, and no two of them may be less than 18 months apart, so one episode cannot fill several places."],
    ["The 10 periods", "Rank, observation month and match distance (lower is closer). The six market-structure charts are not used for matching; they are shown so you can judge how similar the market looks."]],
  tooltipX: v => `Month ${v}`,
},
zh: {
  brand: "美国经济周期 <b>历史类比</b>", other: "English", explore: "筛选", how: "模型说明",
  introTitle: "过去哪些时期和<span class=hl>现在</span>最像？",
  introP1: "这个 App 把美国四项宏观数据（失业率、非农就业、CPI、联邦基金利率）画成图，并与历史对齐。系统已经选出 10 个和当前最接近的历史时期。你逐张查看图表，剔除你觉得不像的时期，然后看剩下的时期之后 12 个月标普 500 的表现。",
  asof: d => `数据截止 ${d}。当前观察月：${M.target}。`,
  s1h: "查看", s1: "依次查看 10 张图，一次一张：4 张宏观，6 张市场结构。",
  s2h: "过滤", s2: "在每张图上点一下历史时期即可剔除；被剔除的时期会在所有图上一起消失。",
  s3h: "看之后的表现", s3: "第 0 个月是观察月的下一个月的最后一个交易日（该月数据公布之后）。结果页显示之后 12 个月的标普 500 走势。",
  start: "开始探索", howLink: "这 10 个时期是怎么选出来的？",
  aboutH: "关于数据",
  about: [
    `历史月份的宏观数据用的是<b>最新修订值</b>；当前（黄线）用的是<b>截至 ${M.as_of} 当时可得的数据</b>（ALFRED 版本）。因此这不是严格的实时回测：当时的投资者看到的是尚未修订的数据。`,
    "标普 500 为价格指数，不含股息。",
    "这是描述性研究，样本小，不是预测，也不是投资建议。",
    "2025 年 10 月因政府停摆没有发布失业率和 CPI。匹配时当前线用相邻月份的平均值补上，图上这个月显示为空白。",
  ],
  step: (i, n) => `第 ${i}/${n} 张`, prev: "上一张", next: "下一张",
  macro: "宏观", mkt: "市场结构",
  sub: "横轴：相对观察月的月数（0 = 最新）。黄线 = 当前。",
  selected: (n, m) => `已选 ${n}/${m}`, nowTag: "当前", tapHint: "点击时期可保留或剔除。",
  none: "没有选中任何时期。点下面的时期可以把它加回来。", restore: "全部恢复",
  barN: n => `已保留 <b>${n}</b>/10 个时期`, seeBtn: "查看未来 12 个月标普 500 表现", keepOne: "至少保留一个时期",
  gap: "空白 = 无数据（不是零）。",
  tabs: ["失业率", "非农", "核心CPI", "利率", "前10市值", "前10盈利", "纳指/标普", "市值/等权", "罗素/标普", "200日广度"],
  titles: {
    unrate: "失业率 (%)", pay_g6: "非农就业，6 个月增速 (%)", core_ann6: "核心 CPI，6 个月年化 (%)",
    ff: "有效联邦基金利率 (%)", cap: "前 10 大市值占标普 500 比例（−24 月 = 100）",
    eps: "前 10 大盈利占标普 500 比例（−24 月 = 100）", ndx_spx: "纳指 100 / 标普 500（−24 月 = 100）",
    cw_ew: "标普 500 市值加权 / 等权（−24 月 = 100）", rut_spx: "罗素 2000 / 标普 500（−24 月 = 100）",
    breadth: "200 日均线以上的标普 500 成分股比例 (%)" },
  notes: {
    unrate: "2025 年 10 月失业率因政府停摆从未发布，黄线在该处为空白。",
    core_ann6: "2025 年 10 月 CPI 因政府停摆从未发布；黄线在该处以及六个月后（以它为基期）为空白。",
    eps: "2026-05 之后没有盈利占比数据，所以黄线提前结束。",
    breadth: "200 日广度数据从 2008 年开始，更早的时期没有线。",
    pay_g6: "", ff: "", cap: "", ndx_spx: "", cw_ew: "", rut_spx: "" },
  resTitle: "之后 <span class=hl>12 个月</span>的标普 500",
  resSub: "第 0 个月 = 观察月的下一个月的最后一个交易日（该月数据公布之后）。",
  resEmpty: "没有选中任何时期，无内容可显示。", back: "返回继续筛选", reset: "全部重置",
  period: "观察月", signal: "信号日", ret: "12 个月回报", mdd: "最大回撤（12 个月）",
  avg: "平均值", med: "中位数", n: n => `样本数 n=${n}`, few: "样本很少",
  one: "只选了一个时期：平均值和中位数就等于该时期。",
  mddNote: "最大回撤的平均值是各时期各自最大回撤的平均，不是“平均路径”的回撤。",
  curNote: `当前状态在这里没有曲线：它的信号日（${nextMonth(M.target)}月底）还没有到。`,
  resFoot: "标普 500 为价格指数，不含股息。历史宏观数据用最新修订值，当前线用截至 " + M.as_of + " 的数据，因此不是严格的实时回测。描述性研究，样本小，不是预测。",
  xr: "信号日之后的月数", yr: "相对信号日收盘的涨跌幅",
  howTitle: "这 <span class=hl>10 个时期</span>是怎么选出来的",
  h: [
    ["从四项宏观数据开始", "失业率、非农就业增长、消费者物价 (CPI) 和联邦基金利率，回溯到 1990 年。数据来源：FRED（圣路易斯联储）。"],
    ["截取当前这一段", w => `每项数据最近 12 个月（${w}），用起点位置和走势来描述：方向、速度、形状。`],
    ["把历史切成 12 个月的窗口并对齐", n => `1990 年以来每个月都有一个以该月结尾的 12 个月窗口，共 ${n} 个候选窗口。每一个都从同一个零点出发，与当前窗口逐点比较。`],
    ["四项指标一起比较", "方向（上行或下行）、速度（快慢）、形状（平稳、加速或转向）。每项数据先放到可比的尺度上，避免某一项独大。得分权重：就业 40%（失业率和非农），通胀 30%（总体和核心 CPI），政策 30%（联邦基金利率）。失业率和利率还有一小部分权重（占本组 15%）放在水平值上，而不只是趋势。失业率或利率走势与当前方向相反的候选期会先被剔除。"],
    ["排序并保留最接近的", "综合距离越小，越接近。保留最好的 10 个，且任意两个相隔不少于 18 个月，避免同一段行情占多个名额。"],
    ["这 10 个时期", "排名、观察月和匹配距离（越小越接近）。六张市场结构图不参与匹配，只是让你判断市场看起来有多像。"]],
  tooltipX: v => `第 ${v} 月`,
},
};
function nextMonth(m) { let [y, mo] = m.split("-").map(Number); mo++; if (mo > 12) { mo = 1; y++; } return `${y}-${String(mo).padStart(2, "0")}`; }
function monthsBack(m, k) { let [y, mo] = m.split("-").map(Number); let n = y * 12 + mo - 1 - k; return `${Math.floor(n / 12)}-${String(n % 12 + 1).padStart(2, "0")}`; }

/* ---------- state + URL ---------- */
const S = { view: "intro", t: 1, keep: new Set(IDS), lang: "en" };
let lastT = null;
const VIEWS = ["intro", "chart", "result", "how"];
function storedLang() { try { const l = localStorage.getItem("lang"); return l === "zh" || l === "en" ? l : null; } catch (e) { return null; } }
function parse() {
  const p = {}; location.hash.replace(/^#/, "").split("&").forEach(kv => { const i = kv.indexOf("="); if (i > 0) p[kv.slice(0, i)] = decodeURIComponent(kv.slice(i + 1)); });
  S.view = VIEWS.includes(p.view) ? p.view : "intro";
  S.t = /^\d+$/.test(p.t || "") && +p.t >= 1 && +p.t <= 10 ? +p.t : 1;
  if (p.keep === undefined) S.keep = new Set(IDS);
  else if (p.keep === "none") S.keep = new Set();
  else { const v = p.keep.split(",").filter(x => IDS.includes(x)); S.keep = new Set(v.length ? v : IDS); }
  S.lang = p.lang === "en" || p.lang === "zh" ? p.lang : (storedLang() || "en");
  if (S.view === "chart") lastT = S.t;
}
function hash() {
  const a = ["view=" + S.view];
  if (S.view === "chart") a.push("t=" + S.t);
  if (S.view !== "intro") {
    if (S.keep.size === 0) a.push("keep=none");
    else if (S.keep.size < IDS.length) a.push("keep=" + IDS.filter(i => S.keep.has(i)).join(","));
  }
  a.push("lang=" + S.lang);
  return "#" + a.join("&");
}
function sync(push) {
  const h = hash();
  if (location.hash !== h) { try { (push ? history.pushState : history.replaceState).call(history, null, "", h); } catch (e) { location.hash = h; } }
  render();
}
function go(view, push, t) {
  S.view = view; if (t) S.t = t;
  if (view === "chart") lastT = S.t;
  const y = window.scrollY; sync(push); if (!push) window.scrollTo(0, y); else window.scrollTo(0, 0);
}
const tx = () => T[S.lang];

/* ---------- helpers ---------- */
const fmtPct = (v, d = 1) => (v > 0 ? "+" : "") + v.toFixed(d) + "%";
const cls = v => v >= 0 ? "up" : "down";
const mean = a => a.reduce((x, y) => x + y, 0) / a.length;
const median = a => { const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
function niceTicks(lo, hi, n = 4) {
  const raw = (hi - lo) / n, mag = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / mag;
  const step = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * mag, out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(6));
  return out;
}
const decs = k => ({ unrate: 1, pay_g6: 2, core_ann6: 1, ff: 2, breadth: 0 }[k] ?? 1);
const unit = k => ["unrate", "pay_g6", "core_ann6", "ff", "breadth"].includes(k) ? "%" : "";

/* ---------- line plot ---------- */
const tip = $("#tip");
function hideTip() { tip.hidden = true; }
window.addEventListener("scroll", hideTip, { passive: true });
function linePlot(host, o) {
  const W = Math.max(280, host.clientWidth - 8), H = Math.round(Math.max(250, Math.min(W * 0.68, 400)));
  const m = { l: o.zero ? 52 : 46, r: 12, t: 10, b: 28 }, pw = W - m.l - m.r, ph = H - m.t - m.b;
  const x0 = o.x[0], x1 = o.x[o.x.length - 1];
  const X = v => m.l + (v - x0) / (x1 - x0) * pw, Y = v => m.t + (1 - (v - o.yr[0]) / (o.yr[1] - o.yr[0])) * ph;
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${o.label}">`;
  niceTicks(o.yr[0], o.yr[1]).forEach(v => {
    s += `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(v)}" y2="${Y(v)}" stroke="${C.grid}" stroke-width="${v === 0 && o.zero ? 1.6 : 1}"/>`;
    s += `<text x="${m.l - 6}" y="${Y(v) + 4}" text-anchor="end" font-size="12" fill="${C.muted}">${o.yfmt(v)}</text>`;
  });
  o.xticks.forEach(v => {
    s += `<text x="${X(v)}" y="${H - 8}" text-anchor="middle" font-size="12" fill="${C.muted}">${v}</text>`;
    if (v === 0 && !o.zero) s += `<line x1="${X(0)}" x2="${X(0)}" y1="${m.t}" y2="${m.t + ph}" stroke="${C.grid}" stroke-dasharray="3 3"/>`;
  });
  o.lines.forEach(l => {
    let seg = [], d = "", dots = "";
    const flush = () => { if (seg.length === 1) dots += `<circle cx="${seg[0][0]}" cy="${seg[0][1]}" r="${l.w + 0.5}" fill="${l.color}"/>`; else if (seg.length) d += "M" + seg.map(p => p[0].toFixed(1) + " " + p[1].toFixed(1)).join("L"); seg = []; };
    l.vals.forEach((v, i) => { if (v == null) flush(); else seg.push([X(o.x[i]), Y(v)]); }); flush();
    s += `<path d="${d}" fill="none" stroke="${l.color}" stroke-width="${l.w}" stroke-linejoin="round" stroke-linecap="round"/>${dots}`;
  });
  s += `<line id="guide" y1="${m.t}" y2="${m.t + ph}" stroke="${C.muted}" stroke-dasharray="3 3" visibility="hidden"/>`;
  s += `<rect id="hit" x="${m.l}" y="${m.t}" width="${pw}" height="${ph}" fill="transparent"/></svg>`;
  host.innerHTML = s;
  const svg = host.firstChild, hit = svg.querySelector("#hit"), guide = svg.querySelector("#guide");
  function show(e) {
    const r = svg.getBoundingClientRect(), px = (e.clientX - r.left) * W / r.width;
    const i = Math.max(0, Math.min(o.x.length - 1, Math.round((px - m.l) / pw * (o.x.length - 1))));
    guide.setAttribute("x1", X(o.x[i])); guide.setAttribute("x2", X(o.x[i])); guide.setAttribute("visibility", "visible");
    const rows = o.lines.filter(l => l.vals[i] != null).sort((a, b) => b.vals[i] - a.vals[i]);
    tip.innerHTML = `<div class="h">${o.xlabel(o.x[i])}</div>` + (rows.map(l => `<div><span><i style="background:${l.color}"></i>${l.name}</span><b>${o.vfmt(l.vals[i])}</b></div>`).join("") || `<div>—</div>`);
    tip.hidden = false;
    const tw = tip.offsetWidth, th = tip.offsetHeight;
    let left = e.clientX + 14; if (left + tw > innerWidth - 6) left = e.clientX - tw - 14;
    tip.style.left = Math.max(6, left) + "px"; tip.style.top = Math.max(6, Math.min(innerHeight - th - 6, e.clientY - th / 2)) + "px";
  }
  hit.addEventListener("pointerdown", show); hit.addEventListener("pointermove", show);
  hit.addEventListener("pointerleave", e => { if (e.pointerType === "mouse") { hideTip(); guide.setAttribute("visibility", "hidden"); } });
}

/* ---------- views ---------- */
function allVals(k) { const v = []; D.series.forEach(s => s.data[k].forEach(x => x != null && v.push(x))); return v; }
function yRange(vals) { let lo = Math.min(...vals), hi = Math.max(...vals); const p = (hi - lo || 1) * 0.07; return [lo - p, hi + p]; }
const swatch = c => `<i style="background:${c}"></i>`;

function chip(id) {
  const a = M.analogs.find(x => x.id === id), on = S.keep.has(id);
  return `<button class="chip${on ? "" : " off"}" style="--c:${SER[id].color}" data-id="${id}" aria-pressed="${on}">${swatch(SER[id].color)}${id}</button>`;
}

function viewIntro() {
  const t = tx();
  app.innerHTML = `<section class="hero"><h1>${t.introTitle}</h1><p>${t.introP1}</p>
  <p class="fine">${t.asof(M.as_of)}</p>
  <div class="steps">${[1, 2, 3].map(i => `<div class="card step"><i>${i}</i><b>${t["s" + i + "h"]}</b><span>${t["s" + i]}</span></div>`).join("")}</div>
  <div class="chips-static">${IDS.map(i => `<span class="chip" style="--c:${SER[i].color}">${swatch(SER[i].color)}${i}</span>`).join("")}<span class="chip cur">${swatch(C.yellow)}${t.nowTag} ${M.target}</span></div>
  <div class="cta"><button class="primary" id="go">${t.start}</button><a href="#view=how&lang=${S.lang}" id="howlink">${t.howLink}</a></div>
  <details class="about card"><summary>${t.aboutH}</summary><ul>${t.about.map(x => `<li>${x}</li>`).join("")}</ul></details></section>`;
  $("#go").onclick = () => go("chart", true, lastT || 1);
}

function viewChart() {
  const t = tx(), k = KEYS[S.t - 1], kept = IDS.filter(i => S.keep.has(i));
  const tabs = t.tabs.map((n, i) => (i === 4 ? `<span class="sep"></span>` : "") + `<button data-t="${i + 1}" class="${i + 1 === S.t ? "on" : ""}">${i + 1}. ${n}</button>`).join("");
  app.innerHTML = `<div class="step-tabs" id="stabs">${tabs}</div>
  <div class="counter">${t.step(S.t, 10)} · ${S.t <= 4 ? t.macro : t.mkt} · ${t.selected(kept.length, 10)}</div>
  <h1 class="chart-title">${t.titles[k]}</h1><p class="chart-sub">${t.sub}</p>
  <div class="chips"><span class="chip cur">${swatch(C.yellow)}${t.nowTag} ${M.target}</span>${IDS.map(chip).join("")}</div>
  <p class="chip-info">${t.tapHint}</p>
  <div class="card plot" id="plot"></div>
  <div id="empty"></div>
  <div class="nav"><button class="secondary" id="prev" ${S.t === 1 ? "disabled" : ""}>← ${t.prev}</button><button class="secondary" id="next" ${S.t === 10 ? "disabled" : ""}>${t.next} →</button></div>
  <p class="note">${t.gap} ${t.notes[k] || ""}</p>`;
  const lines = kept.map(id => ({ id, name: id, color: SER[id].color, w: 2.2, vals: SER[id].data[k] }));
  lines.push({ id: "cur", name: t.nowTag + " " + M.target, color: C.yellow, w: 3.6, vals: CUR.data[k] });
  const d = decs(k), u = unit(k);
  const draw = () => linePlot($("#plot"), { x: D.x, lines, yr: yRange(allVals(k)), xticks: [-24, -18, -12, -6, 0], yfmt: v => v.toFixed(d > 1 ? 1 : d) + u, vfmt: v => v.toFixed(d) + u, xlabel: t.tooltipX, label: t.titles[k] });
  draw(); drawFn = draw;
  if (!kept.length) $("#empty").innerHTML = `<p class="empty">${t.none} <button class="link" id="restore">${t.restore}</button></p>`;
  app.querySelectorAll(".chip[data-id]").forEach(b => b.onclick = () => { const id = b.dataset.id; S.keep.has(id) ? S.keep.delete(id) : S.keep.add(id); go("chart", false); });
  app.querySelectorAll("#stabs button").forEach(b => b.onclick = () => go("chart", false, +b.dataset.t));
  $("#prev").onclick = () => { go("chart", false, S.t - 1); window.scrollTo(0, 0); };
  $("#next").onclick = () => { go("chart", false, S.t + 1); window.scrollTo(0, 0); };
  const r = $("#restore"); if (r) r.onclick = () => { IDS.forEach(i => S.keep.add(i)); go("chart", false); };
  const on = app.querySelector("#stabs .on"); if (on) on.scrollIntoView({ inline: "center", block: "nearest" });
  bar(kept.length);
}

function bar(n) {
  const t = tx();
  $("#bar").hidden = false; document.body.classList.add("has-bar");
  $("#barcount").innerHTML = t.barN(n) + (n === 0 ? `<br>${t.keepOne}` : "");
  const b = $("#barbtn"); b.textContent = t.seeBtn; b.disabled = n === 0;
  b.onclick = () => go("result", true);
}

function viewResult() {
  const t = tx(), F = D.fwd, kept = IDS.filter(i => S.keep.has(i));
  const actions = `<div class="actions"><button class="secondary" id="back">← ${t.back}</button><button class="secondary" id="reset">${t.reset}</button></div>`;
  if (!kept.length) {
    app.innerHTML = `<section class="result"><h1>${t.resTitle}</h1><p class="empty card">${t.resEmpty}</p>${actions}<p class="note">${t.resFoot}</p></section>`;
  } else {
    const rets = kept.map(i => F.ret12[i]), mdds = kept.map(i => F.mdd[i]);
    const row = i => `<tr><td class="sw">${swatch(SER[i].color)}${i}</td><td>${F.signal[i]}</td><td class="${cls(F.ret12[i])}">${fmtPct(F.ret12[i])}</td><td class="down">${fmtPct(F.mdd[i])}</td></tr>`;
    const st = (lab, f, first) => `<tr class="stat${first ? " first" : ""}"><td>${lab}</td><td></td><td class="${cls(f(rets))}">${fmtPct(f(rets))}</td><td class="down">${fmtPct(f(mdds))}</td></tr>`;
    app.innerHTML = `<section class="result"><h1>${t.resTitle}</h1><p class="chart-sub">${t.resSub}</p>
    <div class="card plot" id="plot"></div>
    <div class="card tablewrap"><table><thead><tr><th>${t.period}</th><th>${t.signal}</th><th>${t.ret}</th><th>${t.mdd}</th></tr></thead><tbody>
    ${kept.map(row).join("")}${st(t.avg, mean, true)}${st(t.med, median)}
    <tr class="stat"><td colspan="4" style="text-align:left;font-weight:400;color:var(--muted)">${t.n(kept.length)}${kept.length < 3 ? `<span class="tag">${t.few}</span>` : ""}</td></tr></tbody></table></div>
    ${kept.length === 1 ? `<p class="note">${t.one}</p>` : ""}<p class="note">${t.mddNote}</p><p class="note">${t.curNote}</p>${actions}<p class="note">${t.resFoot}</p></section>`;
    const lines = kept.map(id => ({ id, name: id, color: SER[id].color, w: 2.4, vals: F.data[id] }));
    const all = []; kept.forEach(i => F.data[i].forEach(v => all.push(v)));
    const draw = () => linePlot($("#plot"), { x: F.x, lines, yr: yRange(all.concat([0])), zero: true, xticks: [0, 2, 4, 6, 8, 10, 12], yfmt: v => v.toFixed(0) + "%", vfmt: v => fmtPct(v), xlabel: v => `${t.xr}: ${v}`, label: t.resTitle.replace(/<[^>]+>/g, "") });
    draw(); drawFn = draw;
  }
  $("#back").onclick = () => go("chart", true, lastT || 1);
  $("#reset").onclick = () => { IDS.forEach(i => S.keep.add(i)); go("chart", true, lastT || 1); };
}

function viewHow() {
  const t = tx(), n = M.n_candidates, win = `${monthsBack(M.target, 11)} – ${M.target}`;
  const dims = i => i === 6 ? [900, 508] : [900, 1600];
  const cards = t.h.map(([h, p], idx) => {
    const i = idx + 1, txt = typeof p === "function" ? p(i === 2 ? win : n) : p;
    const extra = i === 6 ? `<div class="rank-grid">${M.analogs.map(a => `<div><em>${a.rank}</em><b style="color:${SER[a.id].color}">${a.id}</b><span>${a.D.toFixed(3)}</span></div>`).join("")}</div>` : "";
    const cta = i === 6 ? `<button class="primary" id="startx">${t.start}</button>` : "";
    return `<article class="card how-card"><div class="how-img"><img src="img/explain/${S.lang}/${i}.webp" width="${dims(i)[0]}" height="${dims(i)[1]}" alt="${h}" ${i > 1 ? 'loading="lazy"' : ""}></div>
    <div class="how-txt"><h2><span>${i}</span>${h}</h2><p>${txt}</p>${extra}${cta}</div></article>`;
  }).join("");
  app.innerHTML = `<section class="how"><h1>${t.howTitle}</h1>${cards}</section>`;
  $("#startx").onclick = () => go(lastT ? "chart" : "intro", true, lastT || undefined);
}

/* ---------- main render ---------- */
let drawFn = null;
function render() {
  const t = tx();
  document.documentElement.lang = S.lang === "zh" ? "zh-CN" : "en";
  document.title = S.lang === "zh" ? "美国经济周期历史类比" : "US Economic Cycle Analogs";
  $("#brand").innerHTML = t.brand; $("#lang").textContent = t.other;
  $("#lang").setAttribute("aria-label", S.lang === "zh" ? "Switch to English" : "切换到中文");
  const on = S.view === "how" ? "how" : "explore";
  $("#maintabs").innerHTML = `<a href="#" data-m="explore" class="${on === "explore" ? "on" : ""}">${t.explore}</a><a href="#" data-m="how" class="${on === "how" ? "on" : ""}">${t.how}</a>`;
  $("#maintabs").querySelectorAll("a").forEach(a => a.onclick = e => {
    e.preventDefault();
    if (a.dataset.m === "how") go("how", true);
    else go(lastT ? "chart" : "intro", true, lastT || undefined);
  });
  $("#brand").onclick = e => { e.preventDefault(); lastT = null; S.keep = new Set(IDS); go("intro", true); };
  hideTip(); drawFn = null;
  $("#bar").hidden = true; document.body.classList.remove("has-bar");
  ({ intro: viewIntro, chart: viewChart, result: viewResult, how: viewHow })[S.view]();
}

$("#lang").onclick = () => {
  S.lang = S.lang === "zh" ? "en" : "zh";
  try { localStorage.setItem("lang", S.lang); } catch (e) {}
  const y = window.scrollY; sync(false); window.scrollTo(0, y);
};
function onNav() { parse(); render(); }
window.addEventListener("hashchange", onNav);
window.addEventListener("popstate", onNav);
let rt; window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => drawFn && drawFn(), 120); });

parse(); sync(false);
})();
