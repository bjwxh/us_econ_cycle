#!/usr/bin/env python3
"""S&P 500 (price index, daily close) rebased to 100 at the close before each window starts:
the 21-month analog window, then the 12 months after it, with the current period overlaid."""
import numpy as np, pandas as pd, matplotlib.pyplot as plt, yfinance as yf
import research as r

CUR,ANA='#2a78d6','#eb6834'
INK,SUB,MUTED,GRID,SHADE='#0b0b0b','#52514e','#898781','#e1e0d9','#f1f0ea'
px=yf.download('^GSPC',start='1950-01-01',progress=False,auto_adjust=False)['Close'].squeeze().dropna()
last=px.index.max()

def path(start,end,extend_to=None):
    """start/end = first/last month of window. Base = last close before the window; x = months since base."""
    base_date=px.loc[:pd.Timestamp(start)-pd.Timedelta(days=1)].index[-1]
    stop=extend_to or (pd.Timestamp(end)+pd.offsets.MonthEnd(0)+pd.DateOffset(months=12))
    s=px.loc[base_date:stop]
    x=(s.index-base_date).days/30.4375
    wend=px.loc[:pd.Timestamp(end)+pd.offsets.MonthEnd(0)].index[-1]
    return x,100*s.to_numpy()/px.loc[base_date],base_date,wend,s.index[-1]

picks=pd.read_csv(r.OUT/'top5_macro_windows.csv',parse_dates=['start','end'])
keep=['1998-09','2004-11','2018-06']
picks=picks[picks.start.dt.strftime('%Y-%m').isin(keep)].sort_values('start')
cx,cy,cbase,cwend,clast=path('2025-02-01','2026-10-01',extend_to=last)
wlen=21.0   # window length in months (x ~ 21 at window end)

fig,axs=plt.subplots(1,3,figsize=(15,5.6),sharey=True,facecolor='#fcfcfb')
rows=[]
for ax,p in zip(axs,picks.itertuples()):
    x,y,base,wend,fend=path(p.start,p.end)
    xw=(wend-base).days/30.4375
    i_w=np.searchsorted(x,xw,side='right')-1
    ax.set_facecolor('#fcfcfb')
    ax.axvspan(xw,x.max(),color=SHADE,zorder=0)
    ax.axhline(100,color=GRID,lw=1,zorder=1)
    ax.plot(x,y,color=ANA,lw=2,zorder=3)
    ax.plot(cx,cy,color=CUR,lw=2.2,zorder=4)
    ax.plot([xw],[y[i_w]],'o',color=ANA,ms=7,mec='#fcfcfb',mew=2,zorder=5)
    ax.plot([x[-1]],[y[-1]],'o',color=ANA,ms=7,mec='#fcfcfb',mew=2,zorder=5)
    win,fwd=y[i_w]-100,100*(y[-1]/y[i_w]-1)
    lo=100*(y[i_w:].min()/y[i_w]-1)
    rows.append((f'{p.start:%Y/%m}–{p.end:%Y/%m}',win,fwd,lo))
    ax.set_title(f'{p.start:%Y/%m}–{p.end:%Y/%m}  then to {fend:%Y/%m}',loc='left',fontsize=11.5,color=INK,fontweight='bold',pad=36)
    ax.text(0,1.02,f'window {win:+.0f}%  ·  next 12 months {fwd:+.0f}%\nworst point in next 12 months: {lo:+.0f}% vs window end',
            transform=ax.transAxes,fontsize=9.5,color=SUB,va='bottom',linespacing=1.4)
    ax.text(xw+.4,ax.get_ylim()[0] if False else 0.02,'next 12 months',transform=ax.get_xaxis_transform(),fontsize=9,color=MUTED,va='bottom')
    ax.text(xw-.4,0.02,'21-month window',transform=ax.get_xaxis_transform(),fontsize=9,color=MUTED,va='bottom',ha='right')
    for s in ('top','right','left'):ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color(GRID);ax.grid(axis='y',color=GRID,lw=.7);ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED,labelsize=9,length=0)
    ax.set_xticks([0,6,12,18,24,30]);ax.set_xlim(0,34)
    ax.set_xlabel('Months since window start',fontsize=9.5,color=SUB)
axs[0].set_ylabel('S&P 500 price index, rebased: close before window = 100',fontsize=9.5,color=SUB)
fig.suptitle('S&P 500 in each analog window and the 12 months after, vs the current period',x=.055,y=.995,ha='left',fontsize=15,color=INK,fontweight='bold')
fig.text(.055,.895,f'Orange = analog window.  Blue = current period (2025/02 to {clast:%Y/%m/%d}; its “next 12 months” has not happened yet).\nDaily closes, price index without dividends. Dots mark the window end and the end of the following 12 months.',
         fontsize=9.5,color=SUB,ha='left',va='bottom',linespacing=1.5)
fig.subplots_adjust(left=.07,right=.985,top=.76,bottom=.12,wspace=.06)
fig.savefig(r.OUT/'sp500_analog_paths.png',dpi=150,facecolor=fig.get_facecolor())
print(pd.DataFrame(rows,columns=['window','window_return_%','next12m_%','worst_vs_window_end_%']).round(1).to_string(index=False))
print(f'current: {cy[np.searchsorted(cx,(cwend-cbase).days/30.4375,side="right")-1]-100:+.1f}% over window to {cwend:%Y-%m-%d}; latest {cy[-1]-100:+.1f}% at {clast:%Y-%m-%d}')
