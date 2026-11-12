"""Ken French data library loaders (in memory, nothing written to disk)."""
import io, zipfile, urllib.request, pandas as pd
BASE='https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/'

def _read(name):
    b=urllib.request.urlopen(urllib.request.Request(BASE+name,headers={'User-Agent':'research-script'}),timeout=60).read()
    z=zipfile.ZipFile(io.BytesIO(b));return z.read(z.namelist()[0]).decode().splitlines()

def section(lines,title):
    """Table that follows the header line containing `title`; monthly rows only (yyyymm)."""
    i=next(k for k,l in enumerate(lines) if title in l)
    cols=lines[i+1].split(',');cols=[c.strip() for c in cols[1:]]
    rows=[]
    for l in lines[i+2:]:
        if not l.strip():break
        p=[x.strip() for x in l.split(',')];rows.append([int(p[0])]+[float(x) for x in p[1:]])
    df=pd.DataFrame(rows,columns=['ym']+cols)
    df.index=pd.to_datetime(df.ym.astype(str)+'01',format='%Y%m%d');return df.drop(columns='ym')

def industries12():
    L=_read('12_Industry_Portfolios_CSV.zip')
    ret=section(L,'Average Value Weighted Returns -- Monthly')/100
    n=section(L,'Number of Firms in Portfolios');size=section(L,'Average Firm Size')
    return ret,n*size    # monthly return (decimal), industry market cap ($ millions)

def market():
    """Total US market return (Mkt-RF + RF), monthly, decimal."""
    L=_read('F-F_Research_Data_Factors_CSV.zip')
    i=next(k for k,l in enumerate(L) if l.startswith(',Mkt-RF'))
    rows=[]
    for l in L[i+1:]:
        if not l.strip():break
        p=[x.strip() for x in l.split(',')];rows.append((pd.to_datetime(p[0]+'01',format='%Y%m%d'),float(p[1])+float(p[4])))
    return pd.Series(dict(rows))/100
