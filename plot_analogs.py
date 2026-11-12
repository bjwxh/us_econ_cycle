#!/usr/bin/env python3
"""Small multiples: current 21-month window vs each top-5 analog, one panel per matching variable."""
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import research as r

CUR,ANA,GRAY='#2a78d6','#eb6834','#b9b8b0'
INK,SUB,MUTED,GRID='#0b0b0b','#52514e','#898781','#e1e0d9'
d=r.data()
d['job_3m']=d.job_pct.rolling(3).mean()           # display only; matching uses raw monthly job_pct
cols=[('job_3m','Payroll growth, %/month\n(3-mo avg · weight 40%)'),('UNRATE','Unemployment rate, %\n(weight 20%)'),
      ('inflation','CPI inflation, % YoY\n(weight 20%)'),('FEDFUNDS','Fed funds rate, %\n(weight 20%)')]
picks=pd.read_csv(r.OUT/'top5_macro_windows.csv',parse_dates=['start','end'])
cur=d.loc['2025-02-01':'2026-10-01']
win=[d.loc[p.start:p.end] for p in picks.itertuples()]
x=np.arange(1,22)

fig,axs=plt.subplots(6,4,figsize=(14,15),sharex=True,sharey='col',facecolor='#fcfcfb')
for j,(c,title) in enumerate(cols):
    for i in range(6):
        ax=axs[i,j];ax.set_facecolor('#fcfcfb')
        for s in ('top','right','left'):ax.spines[s].set_visible(False)
        ax.spines['bottom'].set_color(GRID);ax.grid(axis='y',color=GRID,lw=.7);ax.set_axisbelow(True)
        ax.tick_params(colors=MUTED,labelsize=8,length=0)
        if i==0:
            for w in win:ax.plot(x,w[c].to_numpy(),color=GRAY,lw=1.3,zorder=2)
        else:
            ax.plot(x,win[i-1][c].to_numpy(),color=ANA,lw=2,zorder=3)
            gap=np.nanmean(np.abs(win[i-1][c].to_numpy()-cur[c].to_numpy()))
            ax.set_title(f'avg gap {gap:.2f}',fontsize=8.5,color=SUB,loc='right',pad=3)
        ax.plot(x,cur[c].to_numpy(),color=CUR,lw=2.4,zorder=4)   # NaN = no data: line breaks, nothing filled
        if i==0:ax.set_title(title,fontsize=10,color=INK,loc='left',pad=8)
for i in range(6):
    if i==0:lab='All five analogs\n(grey) vs current'
    else:
        p=picks.iloc[i-1];lab=f'#{i}  {p.start:%Y/%m}–{p.end:%Y/%m}\ndistance {p.distance:.2f}'
    axs[i,0].annotate(lab,xy=(-.34,.5),xycoords='axes fraction',ha='right',va='center',fontsize=10,color=INK,fontweight='bold' if i else 'normal')
for ax in axs[-1]:
    ax.set_xticks([1,6,11,16,21]);ax.set_xlabel('Month in 21-month window',fontsize=9,color=SUB)
fig.suptitle('Do the five analog windows look like the current period?',x=.06,y=.995,ha='left',fontsize=15,color=INK,fontweight='bold')
fig.text(.06,.958,'Blue = current window (2025/02–2026/10).  Orange = one historical analog.  Same y-scale down each column; '
         '"avg gap" = mean absolute difference, in the panel\'s units.\n'
         'Breaks in the blue line = no data published (2025/10 unemployment & CPI; 2026/10 CPI) — left blank, not filled.',
         fontsize=9.5,color=SUB,ha='left',va='bottom',linespacing=1.5)
fig.subplots_adjust(left=.19,right=.98,top=.915,bottom=.045,hspace=.18,wspace=.12)
fig.savefig(r.OUT/'analog_vs_current.png',dpi=150,facecolor=fig.get_facecolor())

# per-variable gap summary (same units as the panels) for the written check
rows=[]
for p,w in zip(picks.itertuples(),win):
    rows.append({'window':f'{p.start:%Y/%m}-{p.end:%Y/%m}',**{c:np.nanmean(np.abs(w[c].to_numpy()-cur[c].to_numpy())) for c,_ in cols}})
print(pd.DataFrame(rows).round(2).to_string(index=False))
print('current-window means:',cur[[c for c,_ in cols]].mean().round(2).to_dict())
