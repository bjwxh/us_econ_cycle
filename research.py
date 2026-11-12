#!/usr/bin/env python3
"""US labor/macroeconomy political affiliation study. Run with internet access.
Outputs are descriptive associations and OOS forecasts, NOT causal claims.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import yfinance as yf

OUT=Path(__file__).resolve().parent / 'outputs'
OUT.mkdir(exist_ok=True)
SERIES=['PAYEMS','UNRATE','CPIAUCSL','FEDFUNDS','DCOILWTICO']

def get_series(s):
    url='https://fred.stlouisfed.org/graph/fredgraph.csv?id='+s
    d=pd.read_csv(url)
    d.columns=['date',s]
    d['date']=pd.to_datetime(d['date'])
    d[s]=pd.to_numeric(d[s],errors='coerce')
    return d.set_index('date')[s]

def get_sp500():
    # S&P 500 PRICE index (no dividends), month-end close, indexed by month start.
    px=yf.download('^GSPC',start='1950-01-01',progress=False,auto_adjust=False)['Close'].squeeze()
    return px.resample('ME').last().to_period('M').to_timestamp()

def data():
    raw=pd.concat([get_series(s) for s in SERIES],axis=1)
    # WTIC oil prices are daily; use end-of-month monthly mean, consistently.
    oil=raw['DCOILWTICO'].resample('MS').mean()
    d=raw.drop(columns='DCOILWTICO').resample('MS').last()
    d['oil']=oil
    d['job_pct']=100*d.PAYEMS.pct_change(fill_method=None)
    d['jobs_yoy']=100*d.PAYEMS.pct_change(12,fill_method=None)
    d['inflation']=100*d.CPIAUCSL.pct_change(12,fill_method=None)
    d['inflation_3m']=400*(np.log(d.CPIAUCSL)-np.log(d.CPIAUCSL.shift(3)))/3
    d['oil_yoy']=100*np.log(d.oil/d.oil.shift(12))
    d['rate_change']=d.FEDFUNDS.diff(3)
    d=d.loc[:'2026-10-01']
    d['sp500']=get_sp500().reindex(d.index)
    # Target for month t: S&P 500 return from end of t+1 to end of t+13. Starting one month
    # late means all month-t releases (payrolls, CPI) were public before the position opens.
    # Nothing is filled: months with no data stay NaN.
    d['sp_fwd12']=100*(d.sp500.shift(-13)/d.sp500.shift(-1)-1)
    return d

# Chamber majorities at the START of each Congress, 1947 onward.
# For notable within-Congress changes, override below. D/R describe caucus control.
CONGRESS={1947:('R','R'),1949:('D','D'),1951:('D','D'),1953:('R','R'),
 1955:('D','D'),1957:('D','D'),1959:('D','D'),1961:('D','D'),
 1963:('D','D'),1965:('D','D'),1967:('D','D'),1969:('D','D'),
 1971:('D','D'),1973:('D','D'),1975:('D','D'),1977:('D','D'),
 1979:('D','D'),1981:('D','R'),1983:('D','R'),1985:('D','R'),
 1987:('D','D'),1989:('D','D'),1991:('D','D'),1993:('D','D'),
 1995:('R','R'),1997:('R','R'),1999:('R','R'),2001:('R','R'),
 2003:('R','R'),2005:('R','R'),2007:('D','D'),2009:('D','D'),
 2011:('R','D'),2013:('R','D'),2015:('R','R'),2017:('R','R'),
 2019:('D','R'),2021:('D','D'),2023:('R','D'),2025:('R','R')}
PRES=[('1945-04-12','D'),('1953-01-20','R'),('1961-01-20','D'),
 ('1969-01-20','R'),('1977-01-20','D'),('1981-01-20','R'),
 ('1993-01-20','D'),('2001-01-20','R'),('2009-01-20','D'),
 ('2017-01-20','R'),('2021-01-20','D'),('2025-01-20','R')]

def politics(d):
    p=[]
    for date in d.index:
        # Month-end political status; post-election switches only on swearing-in.
        day=date+pd.offsets.MonthEnd(0)
        year=day.year
        cstart=year if year%2 else year-1
        # pre-1973 Congresses began on January 3 as well.
        chamber=CONGRESS.get(cstart,('',''))
        # In 2001 Jeffords left Republicans on June 6: Democrats organize Senate.
        if day>=pd.Timestamp('2001-06-06') and day<pd.Timestamp('2003-01-03'):
            chamber=('R','D')
        # Jan 2021 Senate caucus changed control Jan 20 (Democratic VP tie).
        if day>=pd.Timestamp('2021-01-01') and day<pd.Timestamp('2021-01-20'):
            chamber=('D','R')
        pres=next((party for dt,party in reversed(PRES) if day>=pd.Timestamp(dt)),None)
        house,senate=chamber
        p.append((int(pres=='D'),int(house=='D'),int(senate=='D'),int(pres!=house or pres!=senate)))
    return pd.DataFrame(p,index=d.index,columns=['pres_dem','house_dem','senate_dem','divided'])



VARS=['job_pct','UNRATE','inflation','FEDFUNDS']
WEIGHTS=np.array([.40,.20,.20,.20])   # fixed in advance

def window_distance(val,ref,scales,mode):
    """Weighted RMS distance between two 21-month windows. NaN = no data, never filled.
    masked    : per month, compare only variables observed on both sides and rescale the
                weights of those variables to sum to 1.
    drop_month: a month with any missing variable is left out; weights stay 40/20/20/20."""
    sq=WEIGHTS*((val-ref)/scales)**2
    obs=np.isfinite(sq)
    if mode=='drop_month':
        month=np.where(obs.all(axis=1),np.where(obs,sq,0).sum(axis=1),np.nan)
    else:
        wsum=(WEIGHTS*obs).sum(axis=1)
        month=np.where(wsum>0,np.where(obs,sq,0).sum(axis=1)/np.where(wsum>0,wsum,1),np.nan)
    n=int(np.isfinite(month).sum())
    return (np.sqrt(np.nanmean(month)) if n else np.nan),n

def rank_windows(d,current,mode):
    ref=current[VARS].values
    scales=d.loc['1960-01-01':'2024-12-01',VARS].std().values
    rows=[]
    for i in range(len(d)-20):
        w=d.iloc[i:i+21]
        if w.index[0]<pd.Timestamp('1960-01-01') or w.index[-1]>=pd.Timestamp('2025-01-01'):continue
        dist,n=window_distance(w[VARS].values,ref,scales,mode)
        if np.isfinite(dist):rows.append((w.index[0],w.index[-1],dist,n))
    ranking=pd.DataFrame(rows,columns=['start','end','distance','months_used']).sort_values('distance')
    picks=[]
    for r in ranking.itertuples(index=False):   # non-overlapping, best first
        if all(r.end<o.start or r.start>o.end for o in picks):picks.append(r)
        if len(picks)==5:break
    return pd.DataFrame([x._asdict() for x in picks])

def matches(d):
    current=d.loc['2025-02-01':'2026-10-01']
    assert len(current)==21,'Need 21-month current period'
    cell=current[VARS].notna()
    print(f'Current window coverage: {int(cell.values.sum())}/{cell.size} cells observed, '
          f'{int(cell.all(axis=1).sum())}/21 months complete.')
    print('Blank (not filled):',{m.strftime('%Y-%m'):list(cell.columns[~cell.loc[m]]) for m in cell.index[~cell.all(axis=1)]})
    out=rank_windows(d,current,'masked')
    alt=rank_windows(d,current,'drop_month')
    out.to_csv(OUT/'top5_macro_windows.csv',index=False)
    alt.to_csv(OUT/'top5_sensitivity_drop_month.csv',index=False)
    same=set(out.start)&set(alt.start)
    print(f'Sensitivity: {len(same)}/5 windows identical under drop-whole-month.')
    print('\nDrop-whole-month ranking:');print(alt.to_string(index=False))
    # Comparison uses cumulative % of original payroll employment, not raw job counts.
    plt.figure(figsize=(11,6))
    all_windows=[('Current 2025/02–2026/10',current)]
    for x in out.itertuples(index=False):
        all_windows.append((f'{x.start:%Y/%m}–{x.end:%Y/%m}',d.loc[x.start:x.end]))
    for label,w in all_windows:
        initial=d.PAYEMS.loc[w.index[0]-pd.DateOffset(months=1)]
        plt.plot(np.arange(1,22),100*(w.PAYEMS.to_numpy()/initial-1),linewidth=3 if label.startswith('Current') else 1.6,label=label)
    plt.xlabel('Month in window (1–21)');plt.ylabel('Cumulative change in nonfarm payrolls (%)')
    plt.title('Top five historical 21-month macro matches vs current')
    plt.axhline(0,color='grey',linewidth=.8);plt.legend();plt.grid(alpha=.2)
    plt.tight_layout();plt.savefig(OUT/'top5_cumulative_payroll.png',dpi=180);plt.close()
    return out

def analog_outcomes(d,picks):
    """S&P 500 return over the 12 months after each analog window (same definition as the backtest target)."""
    t=picks.assign(sp_fwd12_after_window=[d.sp_fwd12.get(e) for e in picks.end])
    allv=d.sp_fwd12.loc['1960-01-01':'2024-12-01'].dropna()
    t.to_csv(OUT/'analog_sp500_forward.csv',index=False)
    print('\nS&P 500 12m price return after each analog window (%):');print(t.to_string(index=False))
    print(f'Unconditional 1960–2024: mean {allv.mean():.1f}, median {allv.median():.1f}, '
          f'sd {allv.std():.1f}, share>0 {100*(allv>0).mean():.0f}%.  Five windows = anecdotes, not a test.')

def block_boot(diff,L=13,B=5000,seed=0):
    """Moving-block bootstrap CI for the mean of a loss-differential series (blocks cover the 13-month label overlap)."""
    diff=np.asarray(diff);n=len(diff);rng=np.random.default_rng(seed)
    k=int(np.ceil(n/L));starts=rng.integers(0,n-L+1,size=(B,k))
    means=np.array([np.concatenate([diff[s:s+L] for s in row])[:n].mean() for row in starts])
    return diff.mean(),np.percentile(means,5),np.percentile(means,95)

def backtest(d):
    # Predict S&P 500 12m forward price return from data public at month t.
    # Chronological, expanding window, monthly refit; training rows are only those whose
    # 13-month-ahead label was already known at the test date. Alpha is fixed, NOT tuned.
    x=d[['jobs_yoy','UNRATE','inflation','FEDFUNDS','rate_change','oil_yoy']].copy()
    x['jobs_3m']=d.job_pct.rolling(3).mean()
    x['unemp_3m_change']=d.UNRATE.diff(3)
    x=x.join(politics(d))
    common=pd.concat([x,d.sp_fwd12.rename('target')],axis=1).dropna()   # blanks stay blank: rows dropped
    basecols=['jobs_yoy','UNRATE','inflation','FEDFUNDS','rate_change','oil_yoy','jobs_3m','unemp_3m_change']
    polcols=['pres_dem','house_dem','senate_dem','divided']
    models=[('macro_only',basecols),('macro_plus_politics',basecols+polcols)]
    results=[]
    for testdate in common.loc['2010-01-01':].index:
        train=common.loc[:testdate-pd.DateOffset(months=13)]
        if len(train)<180:continue
        actual=float(common.loc[testdate,'target'])
        results.append((testdate,'hist_mean',actual,float(train.target.mean())))
        for name,cols in models:
            sc=StandardScaler().fit(train[cols])
            est=Ridge(alpha=100).fit(sc.transform(train[cols]),train.target)
            results.append((testdate,name,actual,float(est.predict(sc.transform(common.loc[[testdate],cols]))[0])))
    o=pd.DataFrame(results,columns=['date','model','actual','forecast'])
    o['error']=o.actual-o.forecast
    o.to_csv(OUT/'oos_forecasts.csv',index=False)
    def score(frame):
        g=frame.groupby('model');sse=g.error.apply(lambda z:(z**2).sum())
        return pd.DataFrame({'n':g.error.count(),'mae':g.error.apply(lambda z:z.abs().mean()),
            'rmse':g.error.apply(lambda z:np.sqrt((z**2).mean())),'oos_r2_vs_hist_mean':1-sse/sse['hist_mean']})
    full=score(o);ex=score(o[o.date.dt.year!=2020])
    summary=pd.concat({'full':full,'ex_2020':ex});summary.to_csv(OUT/'oos_scores.csv')
    # Does each addition reduce squared error? improvement>0 favours the richer model.
    rows=[]
    for label,frame in [('full',o),('ex_2020',o[o.date.dt.year!=2020])]:
        sq=frame.assign(se=frame.error**2).pivot(index='date',columns='model',values='se')
        for base,new in [('hist_mean','macro_only'),('macro_only','macro_plus_politics')]:
            m,lo,hi=block_boot((sq[base]-sq[new]).values)
            rows.append((label,f'{new} vs {base}',m,lo,hi))
    boot=pd.DataFrame(rows,columns=['sample','comparison','mean_sq_err_improvement','ci90_low','ci90_high'])
    boot.to_csv(OUT/'oos_bootstrap.csv',index=False)
    # Live forecast from the latest month with complete inputs (CPI for 2026-10 does not exist yet).
    last=x.dropna().index.max();live=[]
    for name,cols in models:
        sc=StandardScaler().fit(common[cols]);est=Ridge(alpha=100).fit(sc.transform(common[cols]),common.target)
        live.append((name,float(est.predict(sc.transform(x.loc[[last],cols]))[0])))
    live.append(('hist_mean',float(common.target.mean())))
    live=pd.DataFrame(live,columns=['model','forecast_sp500_12m_pct']).assign(as_of=last)
    live.to_csv(OUT/'live_forecast.csv',index=False)
    print(f'\nTest months {o.date.min():%Y-%m}–{o.date.max():%Y-%m}; Ridge alpha fixed at 100.')
    return summary,boot,live

if __name__=='__main__':
    df=data()
    print('Source coverage:',df.index.min(),df.index.max())
    picks=matches(df)
    print('\nTop five 21-month windows (masked distance):');print(picks.to_string(index=False))
    analog_outcomes(df,picks)
    summary,boot,live=backtest(df)
    print('\nOOS scores, S&P 500 12m forward price return (%):');print(summary.round(3).to_string())
    print('\nBlock-bootstrap, improvement in squared error (>0 = richer model better):');print(boot.round(2).to_string(index=False))
    print('\nLive forecast:');print(live.round(2).to_string(index=False))
    print('\nFiles saved to:',OUT)
