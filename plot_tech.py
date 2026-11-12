#!/usr/bin/env python3
"""Chart 1: Nasdaq vs S&P 500 (price indices).  Chart 2: tech's share of, and contribution to, US market returns
(Ken French 12-industry 'BusEq' group as the tech proxy; all US stocks, total return)."""
import numpy as np, pandas as pd, matplotlib.pyplot as plt, yfinance as yf
from matplotlib.ticker import FuncFormatter
import research as r, french as fr

NAS,SPX,GRAYBAR='#2a78d6','#eb6834','#b9b8b0'
INK,SUB,MUTED,GRID='#0b0b0b','#52514e','#898781','#e1e0d9'
BG='#fcfcfb'

def style(ax):
    ax.set_facecolor(BG)
    for s in ('top','right','left'):ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color(GRID);ax.grid(axis='y',color=GRID,lw=.7);ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED,labelsize=9,length=0)

# ---------------------------------------------------------------- chart 1
def dl(t):return yf.download(t,start='1989-12-01',progress=False,auto_adjust=False)['Close'].squeeze().dropna()
nas,spx=dl('^IXIC'),dl('^GSPC')
df=pd.concat([nas.rename('nas'),spx.rename('spx')],axis=1).dropna()
df=df.loc[:'2026-11-06']
base=df.loc[:'1989-12-31'].iloc[-1];df=df.loc['1990-01-01':]
reb=100*df/base;ratio=100*reb.nas/reb.spx
me=df.resample('ME').last();rel12=100*(me.nas.pct_change(12)-me.spx.pct_change(12)).dropna()

fig,axs=plt.subplots(3,1,figsize=(13,12),sharex=True,facecolor=BG,gridspec_kw={'height_ratios':[3,2.2,2]})
ax=axs[0];style(ax)
ax.plot(reb.index,reb.nas,color=NAS,lw=1.8);ax.plot(reb.index,reb.spx,color=SPX,lw=1.8)
ax.set_yscale('log');ax.set_yticks([100,200,500,1000,2000,5000]);ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_:f'{v:,.0f}'));ax.minorticks_off()
ax.set_title('Both indices, rebased (end of 1989 = 100, log scale)',loc='left',fontsize=11,color=INK,fontweight='bold')
for c,col,lab in [('nas',NAS,'Nasdaq Composite'),('spx',SPX,'S&P 500')]:
    ax.text(reb.index[-1]+pd.Timedelta(days=60),reb[c].iloc[-1],f'{lab}  {reb[c].iloc[-1]:,.0f}',color=col,fontsize=10,va='center',fontweight='bold')
ax=axs[1];style(ax)
ax.plot(ratio.index,ratio,color=INK,lw=1.8);ax.axhline(100,color=GRID,lw=1)
pk=ratio.loc[:'2003-01-01'].idxmax()
ax.plot([pk],[ratio[pk]],'o',color=INK,ms=7,mec=BG,mew=2)
ax.annotate(f'{pk:%b %Y} peak: {ratio[pk]:.0f}',(pk,ratio[pk]),xytext=(8,6),textcoords='offset points',fontsize=9.5,color=SUB)
ax.plot([ratio.index[-1]],[ratio.iloc[-1]],'o',color=INK,ms=7,mec=BG,mew=2)
pass
ax.set_ylim(75,310)
ax.set_title(f'Relative performance: Nasdaq ÷ S&P 500 (rising = Nasdaq ahead).  Now {ratio.iloc[-1]:.0f}; Mar 2000 peak {ratio[pk]:.0f}',loc='left',fontsize=11,color=INK,fontweight='bold')
ax=axs[2];style(ax)
ax.fill_between(rel12.index,0,rel12.clip(lower=0),color=NAS,lw=0,step='mid');ax.fill_between(rel12.index,0,rel12.clip(upper=0),color=SPX,lw=0,step='mid')
ax.axhline(0,color=MUTED,lw=.9)
ax.set_title('Rolling 12-month return gap, Nasdaq minus S&P 500 (percentage points)',loc='left',fontsize=11,color=INK,fontweight='bold')
ax.text(.005,.93,'Nasdaq ahead',transform=ax.transAxes,color=NAS,fontsize=9.5,fontweight='bold',va='top')
ax.text(.005,.06,'S&P 500 ahead',transform=ax.transAxes,color=SPX,fontsize=9.5,fontweight='bold',va='bottom')
ax.set_xlim(df.index[0],df.index[-1]+pd.Timedelta(days=900))
fig.suptitle('Has the Nasdaq kept beating the S&P 500?',x=.045,y=.995,ha='left',fontsize=15,color=INK,fontweight='bold')
fig.text(.045,.945,f'Price indices (dividends excluded), daily closes, 1990 to {df.index[-1]:%Y/%m/%d}. Nasdaq Composite includes non-tech stocks.',fontsize=9.5,color=SUB)
fig.subplots_adjust(left=.07,right=.87,top=.91,bottom=.04,hspace=.28)
fig.savefig(r.OUT/'nasdaq_vs_sp500.png',dpi=150,facecolor=BG);plt.close(fig)
print('Ratio now %.0f vs %s peak %.0f (1989-12 = 100)'%(ratio.iloc[-1],f'{pk:%Y-%m}',ratio[pk]))
dec=(rel12>0).groupby((rel12.index.year//10)*10).mean().mul(100).round(0)
print('Share of months with Nasdaq ahead of S&P over trailing 12m, by decade (%):',dec.to_dict(),'| all:',round(100*(rel12>0).mean()))

# ---------------------------------------------------------------- chart 2
ret,cap=fr.industries12();mkt=fr.market()
w=cap.div(cap.sum(axis=1),axis=0)            # beginning-of-month weights (validated against market return)
contrib=w*ret;c_tot=contrib.sum(axis=1)       # month-t contribution to the market return, decimal
sel=slice('1990-01-01',None)
resid=(c_tot-mkt).loc[sel]
print(f'Weights x returns vs reported market return: mean abs gap {100*resid.abs().mean():.3f} pp/month, max {100*resid.abs().max():.2f} pp')
c_tot,w,contrib=c_tot.loc['1989-12-01':],w.loc['1989-12-01':],contrib.loc['1989-12-01':]
M=(1+c_tot).cumprod();Mprev=M.shift(1).fillna(1.0)   # market wealth index built from the same weights (exact additivity)
tech_pts=(Mprev*contrib.BusEq);rest_pts=(Mprev*(c_tot-contrib.BusEq))
yr=pd.DataFrame({'tech_pp':tech_pts,'rest_pp':rest_pts}).loc['1990-01-01':]
Mstart=M.shift(1).loc['1990-01-01':]
g=yr.groupby(yr.index.year)
start_level=Mstart.groupby(Mstart.index.year).first()
res=(g.sum().div(start_level,axis=0))*100
res['total_pp']=res.tech_pp+res.rest_pp
res['tech_share_pct']=np.where(res.total_pp>=5,100*res.tech_pp/res.total_pp.where(res.total_pp>=5),np.nan)   # share is unstable when the market gain is tiny
res['tech_weight_start_pct']=100*w.BusEq.loc['1990-01-01':].groupby(lambda d:d.year).first()
res.round(2).to_csv(r.OUT/'tech_contribution_by_year.csv')
M0=M.loc['1989-12-01']
cum_tech=tech_pts.loc['1990-01-01':].cumsum();cum_gain=M.loc['1990-01-01':]-M0
cum_share=(100*cum_tech/cum_gain).where(cum_gain>=0.2)    # shown once cumulative gain is at least 20%
cum_share.rename('cum_tech_share_pct').round(2).to_csv(r.OUT/'tech_cumulative_share.csv')
last_year=res.index.max();last_month=ret.index.max()

fig,axs=plt.subplots(3,1,figsize=(13,13.5),facecolor=BG,gridspec_kw={'height_ratios':[2,2.4,2.4]})
ax=axs[0];style(ax);wt=100*w.BusEq.loc['1990-01-01':]
ax.plot(wt.index,wt,color=NAS,lw=2)
ax.set_title('Tech (business equipment) share of total US stock market value, %',loc='left',fontsize=11,color=INK,fontweight='bold')
pk=wt.loc[:'2005-01-01'].idxmax()
for d_,txt,dx in [(pk,f'{pk:%b %Y}: {wt[pk]:.0f}%',8),(wt.index[-1],f'{wt.index[-1]:%b %Y}: {wt.iloc[-1]:.0f}%',-8)]:
    ax.plot([d_],[wt[d_]],'o',color=NAS,ms=7,mec=BG,mew=2);ax.annotate(txt,(d_,wt[d_]),xytext=(dx,6),textcoords='offset points',fontsize=9.5,color=SUB,ha='left' if dx>0 else 'right')
ax.set_ylim(0,50)
x=np.arange(len(res));wd=.38
ax=axs[1];style(ax)
ax.bar(x-wd/2-.02,res.tech_pp,wd,color=NAS,label='Tech',zorder=3);ax.bar(x+wd/2+.02,res.rest_pp,wd,color=GRAYBAR,label='Everything else',zorder=3)
ax.plot(x,res.total_pp,'_',color=INK,ms=14,mew=2,label='Total market return',zorder=4)
ax.axhline(0,color=MUTED,lw=.9)
ax.set_title('Calendar-year contribution to total US market return (percentage points; tech + everything else = total)',loc='left',fontsize=11,color=INK,fontweight='bold')
ax.set_ylim(-40,52);ax.legend(frameon=False,loc='upper left',fontsize=9.5,ncol=3,labelcolor=SUB)
ax=axs[2];style(ax)
cs=cum_share.dropna()
ax.plot(cs.index,cs,color=NAS,lw=2)
ax.set_title('Tech share of cumulative US market gains since 1990, % (running total; shown once cumulative gain exceeds 20%)',loc='left',fontsize=11,color=INK,fontweight='bold')
for d_,dx in [(cs.loc[:'2003-01-01'].idxmax(),8),(cs.index[-1],-8)]:
    ax.plot([d_],[cs[d_]],'o',color=NAS,ms=7,mec=BG,mew=2)
    ax.annotate(f'{d_:%b %Y}: {cs[d_]:.0f}%',(d_,cs[d_]),xytext=(dx,8),textcoords='offset points',fontsize=9.5,color=SUB,ha='left' if dx>0 else 'right')
ax.set_ylim(-3,max(60,cs.max()*1.15))
ax.set_xlim(wt.index[0],wt.index[-1]+pd.Timedelta(days=700))
axs[1].set_xticks(x);axs[1].set_xticklabels([str(y)[2:] if y<last_year else f"{str(y)[2:]}*" for y in res.index],fontsize=8.5)
axs[1].set_xlim(-.7,len(x)-.3)
axs[0].set_xlim(wt.index[0],wt.index[-1]+pd.Timedelta(days=700))
fig.suptitle('How much of US stock market gains came from tech?',x=.045,y=.995,ha='left',fontsize=15,color=INK,fontweight='bold')
fig.text(.045,.952,f'Proxy: Ken French “business equipment” industry group (computers, software, electronics), value-weighted, all US stocks, total return, through {last_month:%Y/%m}. '
         f'* = {last_year} year-to-date.\nNot the exact S&P 500 tech sector. Contribution = weight × return, summed within each year and scaled so tech + everything else = total.',fontsize=9.5,color=SUB,va='bottom',linespacing=1.5)
fig.subplots_adjust(left=.07,right=.97,top=.915,bottom=.04,hspace=.3)
fig.savefig(r.OUT/'tech_contribution.png',dpi=150,facecolor=BG);plt.close(fig)
print('Cumulative tech share since 1990: '+', '.join(f'{k}: {cum_share.loc[k].iloc[0]:.0f}%' for k in ['1999-12','2002-12','2010-12','2020-12']) + f', latest: {cs.iloc[-1]:.0f}%')
print(res.loc[[2023,2024,2025,last_year]].round(1).to_string() if {2023,2024,2025}<=set(res.index) else res.tail(4).round(1).to_string())
