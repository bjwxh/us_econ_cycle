"""Interactive, self-contained HTML version of analog_paths.png (no external libraries, works offline).

python -m macro_analog.interactive   (reads outputs/p0/analog_top5.csv written by macro_analog.run)
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from . import ingest
from .market import load_spx, month_end_day, outcome
from .features import build_features, load_series
from .plots import GRID, INK, INK2, MUTED, SERIES as _S5, SURFACE

SERIES = _S5 + ["#7a4fc4", "#8c6b3f", "#17a2b8", "#b5338a", "#6b7d1f"]   # 10 analog colours

PANELS = [("unrate", "Unemployment rate (%)"), ("pay_g6", "Payrolls, 6-month growth (%)"),
          ("core_ann6", "Core CPI, 6-month annualized (%)"), ("ff", "Effective fed funds (%)")]
MKT_PANELS = [("cap", "Top-10 share of S&P 500 market cap (rebased: month -{LB} = 100)", "Market structure"),
              ("eps", "Top-10 share of forward earnings (rebased: month -{LB} = 100)", None),
              ("ndx_spx", "Nasdaq 100 / S&P 500 (rebased: month -{LB} = 100)", None),
              ("cw_ew", "S&P 500 cap-weight / equal-weight (rebased: month -{LB} = 100)", None),
              ("rut_spx", "Russell 2000 / S&P 500 (rebased: month -{LB} = 100)", None),
              ("breadth", "% of S&P 500 stocks above 200-day average", None)]
LOOKBACK = 12
EXT = ingest.ROOT / "data" / "external"
NAMES = ["PAYEMS", "UNRATE", "CPIAUCSL", "CPILFESL", "FEDFUNDS"]


def _vals(s: pd.Series, m: pd.Period):
    return [None if pd.isna(v) else round(float(v), 4) for v in s.loc[m - LOOKBACK:m].values]


def market_series() -> dict:
    """Monthly Series (PeriodIndex) for the six market-structure indicators."""
    gs = pd.read_csv(EXT / "gs_top10_concentration_eotm_jun2026.csv", index_col=0)
    gs.index = pd.PeriodIndex(gs.index, freq="M")
    cap, eps = gs["top10_mktcap_pct"].copy(), gs["top10_fwd_earnings_pct"]
    br = pd.read_csv(EXT / "top10_cap_share_bridge.csv", index_col=0, parse_dates=True)["top10_cap_share_pct"]
    br_m = br.groupby(br.index.to_period("M")).mean()
    cap = cap.combine_first(br_m.loc["2026-06":])      # Goldman chart through 2026-05, Schwab bridge after
    r24 = pd.read_csv(EXT / "ind2_ind4_monthly.csv", index_col=0)
    r35 = pd.read_csv(EXT / "ind3_ind5_monthly.csv", index_col=0)
    for d in (r24, r35):
        d.index = pd.PeriodIndex(d.index, freq="M")
    return dict(cap=cap, eps=eps, ndx_spx=r24["ndx_spx"], cw_ew=r35["cw_over_ew"], rut_spx=r24["rut_spx"],
                breadth=r35["pct_above_200dma"])


REBASE = {"cap", "eps", "ndx_spx", "cw_ew", "rut_spx"}


def _mkt_vals(ms: dict, k: str, m: pd.Period):
    s = ms[k].reindex(pd.period_range(m - LOOKBACK, m, freq="M"))
    if k in REBASE:
        s = s / s.iloc[0] * 100
    return [None if pd.isna(v) else round(float(v), 4) for v in s.values]


def build_payload(as_of: str, top5_csv: Path, market: bool = False) -> dict:
    f_rev = build_features({n: load_series(ingest.latest(f"fred_{n}_revised")) for n in NAMES})
    f_asof = build_features({n: load_series(ingest.latest(f"fred_{n}_asof{as_of}")) for n in NAMES})
    target = f_asof.index.max()
    months = [pd.Period(m) for m in pd.read_csv(top5_csv)["obs_month"]]
    series = [dict(id=str(target), label=f"{target} (current, as known)", color=INK, current=True,
                   data={c: _vals(f_asof[c], target) for c, _ in PANELS})]
    for i, m in enumerate(months):
        series.append(dict(id=str(m), label=str(m), color=SERIES[i], current=False,
                           data={c: _vals(f_rev[c], m) for c, _ in PANELS}))
    panels = [dict(key=c, title=t) for c, t in PANELS]
    if market:
        ms = market_series()
        for sr in series:
            m = pd.Period(sr["id"])
            sr["data"].update({k: _mkt_vals(ms, k, m) for k, _, _ in MKT_PANELS})
        panels += [dict(key=k, title=t.replace("{LB}", str(LOOKBACK)), section=sec) for k, t, sec in MKT_PANELS]
    spx = load_spx(ingest.latest("spx_schwab"))
    fwd = dict(x=list(range(13)), data={}, ret12={}, mdd={}, signal={})
    for m in months:                      # entry = last trading day of m+1 (the signal date), then 12 month-ends
        sp = m + 1
        entry = spx[month_end_day(spx, sp)]
        fwd["data"][str(m)] = [round(float(spx[month_end_day(spx, sp + k)] / entry - 1) * 100, 2) for k in range(13)]
        o = outcome(spx, sp)
        fwd["ret12"][str(m)] = round(float(o["R_12m"]) * 100, 1); fwd["mdd"][str(m)] = round(float(o["MDD_12m"]) * 100, 1)
        fwd["signal"][str(m)] = str(o["signal_date"])[:10]
    return dict(panels=panels, x=list(range(-LOOKBACK, 1)), series=series, fwd=fwd,
                colors=dict(surface=SURFACE, ink=INK, ink2=INK2, muted=MUTED, grid=GRID))


HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Macro analog paths (interactive)</title>
<style>
body{margin:0;background:%(surface)s;color:%(ink)s;font:14px -apple-system,Helvetica,Arial,sans-serif}
main{max-width:1100px;margin:0 auto;padding:18px 20px}
h1{font-size:17px;margin:0 0 4px}
.sub{color:%(ink2)s;font-size:12.5px;margin-bottom:12px}
.bar{display:flex;gap:18px;align-items:flex-start;flex-wrap:wrap;margin-bottom:10px}
details{position:relative}
summary{list-style:none;cursor:pointer;border:1px solid %(muted)s;border-radius:6px;padding:6px 12px;background:#fff;user-select:none}
summary::after{content:" \\25BE"}
.menu{position:absolute;z-index:5;margin-top:4px;background:#fff;border:1px solid %(muted)s;border-radius:6px;padding:6px 4px;min-width:230px;box-shadow:0 4px 14px rgba(0,0,0,.12)}
.menu label{display:flex;align-items:center;gap:8px;padding:5px 10px;cursor:pointer}
.menu label:hover{background:#f1f0ec}
.menu hr{border:0;border-top:1px solid %(grid)s;margin:4px 0}
.menu button{margin:2px 10px;font:inherit;font-size:12.5px;cursor:pointer;border:0;background:none;color:%(ink2)s;text-decoration:underline}
.sw{width:18px;height:3px;border-radius:2px;display:inline-block}
#legend{display:flex;gap:16px;flex-wrap:wrap;align-items:center;color:%(ink2)s;font-size:13px;padding-top:6px}
#legend span{display:inline-flex;align-items:center;gap:6px}
#grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 18px}
.tabs{display:flex;gap:4px;border-bottom:1px solid %(grid)s;margin:4px 0 10px}
.tabs button{font:inherit;font-size:13.5px;padding:7px 14px;border:0;background:none;color:%(ink2)s;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px}
.tabs button.on{color:%(ink)s;font-weight:600;border-bottom-color:%(ink)s}
#fwd{display:none}
#fwd table{border-collapse:collapse;font-size:13px;margin-top:12px}
#fwd th,#fwd td{padding:4px 14px;text-align:right;border-bottom:1px solid %(grid)s}
#fwd th:first-child,#fwd td:first-child{text-align:left}
.panel h2{font-size:13px;font-weight:600;margin:6px 0 0}
svg{width:100%%;height:auto;display:block;overflow:visible}
#tip{position:fixed;pointer-events:none;background:#fff;border:1px solid %(muted)s;border-radius:6px;padding:7px 10px;font-size:12.5px;box-shadow:0 4px 14px rgba(0,0,0,.14);display:none;z-index:9}
#tip b{font-weight:600}
.note{color:%(ink2)s;font-size:12px;margin-top:10px}
</style></head><body><main>
<h1>Macro path in the %(lb)s months before each match</h1>
<div class="sub">Black = current state (data as known on the as-of date). Analog lines use revised history. Pick any comparison set, including none.</div>
<div class="bar">
 <details id="dd"><summary id="sumtxt">Compare with</summary><div class="menu" id="menu"></div></details>
 <div id="legend"></div>
</div>
<div class="tabs"><button id="t1" class="on">Macro &amp; market structure (past %(lb)s months)</button><button id="t2">S&amp;P 500 next 12 months</button></div>
<div id="macro">
<div id="grid"></div>
<div class="note">Gaps in the black line: October 2025 CPI (and unemployment) was never published because of the government shutdown, so the current line is blank at about -12 months and, for the 6-month CPI measures that use it as a base, at about -6 months. Nothing is interpolated in this chart.</div>
%(extra_note)s
</div>
<div id="fwd"><div class="panel"><h2>S&amp;P 500 price change after the signal date (0 = last trading day of the month after the observation month)</h2></div>
<div class="note">The current state has no line here: its next 12 months have not happened yet. Price index, dividends excluded. Same selection as the dropdown above.</div></div>
<div id="tip"></div>
</main>
<script>
const D=%(payload)s, C=D.colors, NS="http://www.w3.org/2000/svg";
const W=500,H=300,M={l:44,r:10,t:8,b:34};
const cur=D.series[0], analogs=D.series.slice(1);
const sel=new Set(analogs.map(s=>s.id));            // default: all analogs
const el=(t,a={},p)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e};
const fmt=v=>v==null?"n/a":v.toFixed(2);
const sx=i=>M.l+(W-M.l-M.r)*i/(D.x.length-1);

// y ranges are fixed over ALL series so the axes do not jump when selection changes
const ranges=D.panels.map(p=>{let a=[];D.series.forEach(s=>s.data[p.key].forEach(v=>v!=null&&a.push(v)));
  let lo=Math.min(...a),hi=Math.max(...a),pad=(hi-lo)*0.08||1;return [lo-pad,hi+pad]});
const ticks=(lo,hi)=>{const raw=(hi-lo)/4,p=Math.pow(10,Math.floor(Math.log10(raw))),n=[1,2,2.5,5,10].find(k=>k*p>=raw)*p;
  const o=[];for(let t=Math.ceil(lo/n)*n;t<=hi+1e-9;t+=n)o.push(+t.toFixed(10));return o};

const panels=D.panels.map((p,pi)=>{
  if(p.section){const h=document.createElement("h3");h.textContent=p.section;h.style.cssText="grid-column:1/-1;font-size:15px;margin:18px 0 0;padding-top:10px;border-top:1px solid "+C.grid;document.getElementById("grid").appendChild(h)}
  const wrap=document.createElement("div");wrap.className="panel";wrap.innerHTML="<h2>"+p.title+"</h2>";
  const svg=el("svg",{viewBox:`0 0 ${W} ${H}`});wrap.appendChild(svg);document.getElementById("grid").appendChild(wrap);
  const [lo,hi]=ranges[pi],sy=v=>M.t+(H-M.t-M.b)*(1-(v-lo)/(hi-lo));
  ticks(lo,hi).forEach(t=>{el("line",{x1:M.l,x2:W-M.r,y1:sy(t),y2:sy(t),stroke:C.grid,"stroke-width":1},svg);
    const tx=el("text",{x:M.l-6,y:sy(t)+4,"text-anchor":"end","font-size":11,fill:C.ink2},svg);tx.textContent=+t.toFixed(2)});
  const LB=D.x.length-1,xticks=[];for(let m=-LB;m<=0;m+=(LB>12?6:3))xticks.push(m);
  xticks.forEach(m=>{const tx=el("text",{x:sx(m+LB),y:H-M.b+16,"text-anchor":"middle","font-size":11,fill:C.ink2},svg);tx.textContent=m});
  const xl=el("text",{x:(M.l+W-M.r)/2,y:H-4,"text-anchor":"middle","font-size":11,fill:C.muted},svg);xl.textContent="Months relative to observation month";
  const g=el("g",{},svg),cross=el("line",{y1:M.t,y2:H-M.b,stroke:C.muted,"stroke-width":1,"stroke-dasharray":"3 3",visibility:"hidden"},svg);
  const hit=el("rect",{x:M.l,y:M.t,width:W-M.l-M.r,height:H-M.t-M.b,fill:"transparent"},svg);
  hit.addEventListener("mousemove",e=>{const r=svg.getBoundingClientRect(),px=(e.clientX-r.left)/r.width*W;
    const i=Math.max(0,Math.min(D.x.length-1,Math.round((px-M.l)/(W-M.l-M.r)*(D.x.length-1))));showTip(i,e)});
  hit.addEventListener("mouseleave",()=>{panels.forEach(q=>q.cross.setAttribute("visibility","hidden"));document.getElementById("tip").style.display="none"});
  return {p,g,cross,sy};
});

let tab=1;
const F=D.fwd,FW=1000,FH=1300,FM={l:50,r:16,t:10,b:36},fx=i=>FM.l+(FW-FM.l-FM.r)*i/12;
let fa=[];analogs.forEach(s=>F.data[s.id].forEach(v=>fa.push(v)));
const flo=Math.min(...fa,0)-3,fhi=Math.max(...fa)+3,fy=v=>FM.t+(FH-FM.t-FM.b)*(1-(v-flo)/(fhi-flo));
const fsvg=el("svg",{viewBox:`0 0 ${FW} ${FH}`});document.querySelector("#fwd .panel").appendChild(fsvg);
ticks(flo,fhi).forEach(t=>{el("line",{x1:FM.l,x2:FW-FM.r,y1:fy(t),y2:fy(t),stroke:t==0?C.muted:C.grid,"stroke-width":t==0?1.5:1},fsvg);
  const tx=el("text",{x:FM.l-6,y:fy(t)+4,"text-anchor":"end","font-size":12,fill:C.ink2},fsvg);tx.textContent=(t>0?"+":"")+t+"%%"});
for(let i=0;i<=12;i+=1){const tx=el("text",{x:fx(i),y:FH-FM.b+18,"text-anchor":"middle","font-size":12,fill:C.ink2},fsvg);tx.textContent=i}
const fxl=el("text",{x:(FM.l+FW-FM.r)/2,y:FH-4,"text-anchor":"middle","font-size":12,fill:C.muted},fsvg);fxl.textContent="Months after the signal date";
const fg=el("g",{},fsvg),fcross=el("line",{y1:FM.t,y2:FH-FM.b,stroke:C.muted,"stroke-width":1,"stroke-dasharray":"3 3",visibility:"hidden"},fsvg);
const fhit=el("rect",{x:FM.l,y:FM.t,width:FW-FM.l-FM.r,height:FH-FM.t-FM.b,fill:"transparent"},fsvg);
fhit.addEventListener("mousemove",e=>{const r=fsvg.getBoundingClientRect(),px=(e.clientX-r.left)/r.width*FW;
  const i=Math.max(0,Math.min(12,Math.round((px-FM.l)/(FW-FM.l-FM.r)*12)));fcross.setAttribute("x1",fx(i));fcross.setAttribute("x2",fx(i));fcross.setAttribute("visibility","visible");
  const v=analogs.filter(s=>sel.has(s.id)).sort((a,b)=>F.data[b.id][i]-F.data[a.id][i]);
  const t=document.getElementById("tip");t.innerHTML=`<div style="color:${C.ink2};margin-bottom:3px">month +${i}</div>`+v.map(s=>`<div><i class="sw" style="background:${s.color}"></i> ${s.label}: <b>${F.data[s.id][i].toFixed(1)}%%</b></div>`).join("");
  t.style.display="block";const w=t.offsetWidth;t.style.left=Math.min(e.clientX+14,innerWidth-w-8)+"px";t.style.top=(e.clientY+14)+"px"});
fhit.addEventListener("mouseleave",()=>{fcross.setAttribute("visibility","hidden");document.getElementById("tip").style.display="none"});
const ftab=document.createElement("div");document.getElementById("fwd").insertBefore(ftab,document.querySelector("#fwd .note"));
function drawFwd(){
  fg.innerHTML="";const v=analogs.filter(s=>sel.has(s.id));
  v.forEach(s=>{const d=F.data[s.id].map((y,i)=>(i?"L":"M")+fx(i).toFixed(1)+" "+fy(y).toFixed(1)).join("");
    el("path",{d,fill:"none",stroke:s.color,"stroke-width":2,"stroke-linejoin":"round"},fg);
    el("circle",{cx:fx(12),cy:fy(F.data[s.id][12]),r:4,fill:s.color,stroke:C.surface,"stroke-width":1.5},fg)});
  const r=v.map(s=>F.ret12[s.id]).sort((a,b)=>a-b),n=r.length,mean=n?r.reduce((a,b)=>a+b,0)/n:0,med=n?(n%%2?r[(n-1)/2]:(r[n/2-1]+r[n/2])/2):0;
  const f1=x=>(x>0?"+":"")+x.toFixed(1)+"%%";
  ftab.innerHTML=n?"<table><tr><th>Analog</th><th>Signal date</th><th>12-month return</th><th>Max drawdown within 12 months</th></tr>"+
    v.map(s=>`<tr><td><i class="sw" style="background:${s.color}"></i> ${s.label}</td><td>${F.signal[s.id]}</td><td>${f1(F.ret12[s.id])}</td><td>${F.mdd[s.id].toFixed(1)}%%</td></tr>`).join("")+
    `<tr><td><b>Mean / median of selected</b></td><td></td><td><b>${f1(mean)} / ${f1(med)}</b></td><td></td></tr></table>`:"";
}
function setTab(k){tab=k;document.getElementById("macro").style.display=k==1?"":"none";document.getElementById("fwd").style.display=k==2?"block":"none";
  document.getElementById("t1").className=k==1?"on":"";document.getElementById("t2").className=k==2?"on":"";draw()}
document.getElementById("t1").onclick=()=>setTab(1);document.getElementById("t2").onclick=()=>setTab(2);
function visible(){return [cur,...analogs.filter(s=>sel.has(s.id))]}
function draw(){
  panels.forEach(({p,g,sy})=>{g.innerHTML="";
    visible().slice().reverse().forEach(s=>{               // current drawn last (on top)
      const v=s.data[p.key];let d="",pen=false;
      v.forEach((y,i)=>{if(y==null){pen=false;return}d+=(pen?"L":"M")+sx(i).toFixed(1)+" "+sy(y).toFixed(1);pen=true});
      el("path",{d,fill:"none",stroke:s.color,"stroke-width":s.current?3:2,"stroke-linejoin":"round","stroke-linecap":"round"},g);
      v.forEach((y,i)=>{if(y==null)return;const iso=(i>0&&v[i-1]==null||i==0)&&(i==v.length-1||v[i+1]==null);
        if(iso)el("circle",{cx:sx(i),cy:sy(y),r:2.5,fill:s.color},g)});
    });
    // end-of-line dot on the observation month
    visible().forEach(s=>{const y=s.data[p.key][D.x.length-1];if(y!=null)el("circle",{cx:sx(D.x.length-1),cy:sy(y),r:3.5,fill:s.color,stroke:C.surface,"stroke-width":1.5},g)});
  });
  drawFwd();
  const n=sel.size;document.getElementById("sumtxt").textContent=n==0?"Compare with: none":"Compare with: "+n+" of "+analogs.length+" selected";
  document.getElementById("legend").innerHTML=(tab==2?visible().slice(1):visible()).map(s=>`<span><i class="sw" style="background:${s.color}"></i>${s.label}</span>`).join("");
}
function showTip(i,e){
  panels.forEach(({cross})=>{cross.setAttribute("x1",sx(i));cross.setAttribute("x2",sx(i));cross.setAttribute("visibility","visible")});
  const pi=panels.findIndex(q=>q.g.parentNode===e.currentTarget.parentNode),k=D.panels[pi].key;
  const rows=visible().map(s=>`<div><i class="sw" style="background:${s.color}"></i> ${s.label}: <b>${fmt(s.data[k][i])}</b></div>`).join("");
  const t=document.getElementById("tip");t.innerHTML=`<div style="color:${C.ink2};margin-bottom:3px">${D.panels[pi].title} &middot; month ${D.x[i]}</div>`+rows;
  t.style.display="block";const w=t.offsetWidth;t.style.left=Math.min(e.clientX+14,innerWidth-w-8)+"px";t.style.top=(e.clientY+14)+"px";
}
const menu=document.getElementById("menu");
analogs.forEach(s=>{const l=document.createElement("label");
  l.innerHTML=`<input type="checkbox" checked> <i class="sw" style="background:${s.color}"></i> ${s.label}`;
  l.querySelector("input").addEventListener("change",e=>{e.target.checked?sel.add(s.id):sel.delete(s.id);draw()});menu.appendChild(l)});
menu.appendChild(document.createElement("hr"));
[["Select all",true],["Clear (none)",false]].forEach(([t,all])=>{const b=document.createElement("button");b.textContent=t;
  b.onclick=()=>{analogs.forEach(s=>all?sel.add(s.id):sel.delete(s.id));menu.querySelectorAll("input").forEach(i=>i.checked=all);draw()};menu.appendChild(b)});
document.addEventListener("click",e=>{const dd=document.getElementById("dd");if(!dd.contains(e.target))dd.open=false});
draw();
</script></body></html>
"""


MKT_NOTE = """<div class="note"><b>Market-structure panels.</b> Same selection as above; month 0 = the analog's observation month. All panels except breadth are rebased to 100 at month -{LB} so only the relative change is compared (a top-10 share of 40% and one of 20% are not comparable in level). Top-10 market-cap share: Goldman chart (extracted) through 2026-05, then a Schwab-based bridge for the current line (about +/-1.5 pp error). Forward-earnings share: the chart ends 2026-05, so the current line stops at month -5. 200-day breadth exists only from 2008 (Yardeni extraction, then a point-in-time rebuild), so analogs before 2008 have no line there. Goldman, J.P. Morgan and Yardeni derived data are licensed research: keep this file private.</div>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default="2026-11-10")
    ap.add_argument("--out", default=str(ingest.ROOT / "outputs" / "p0"))
    ap.add_argument("--top5", default="analog_top5.csv", help="analog CSV inside --out")
    ap.add_argument("--name", default="analog_paths_interactive.html")
    ap.add_argument("--market", action="store_true", help="append the six market-structure panels")
    ap.add_argument("--lookback", type=int, default=12, help="months of history shown before each observation month")
    a = ap.parse_args()
    global LOOKBACK
    LOOKBACK = a.lookback
    out = Path(a.out)
    payload = build_payload(a.as_of, out / a.top5, a.market)
    # "</" inside JSON would end the script tag; none expected, but make it safe
    page = HTML % dict(payload=json.dumps(payload).replace("</", "<\\/"), extra_note=MKT_NOTE.replace("{LB}", str(LOOKBACK)) if a.market else "", lb=LOOKBACK, **payload["colors"])
    (out / a.name).write_text(page)
    print(out / a.name)


if __name__ == "__main__":
    main()
