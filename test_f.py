import pandas as pd
DATA = "data"
aaii  = pd.read_csv(DATA + '/aaii_weekly.csv',  index_col=0, parse_dates=True)
naaim = pd.read_csv(DATA + '/naaim_weekly.csv', index_col=0, parse_dates=True)

etfs  = pd.read_csv(DATA + '/etfs_daily.csv',   index_col=0, parse_dates=True)
fridays = etfs.index[etfs.index.weekday == 4]
def to_friday_ffill(df):
    return (df.reindex(df.index.union(fridays))
              .sort_index().ffill()
              .reindex(fridays))

aaii_w  = to_friday_ffill(aaii)
naaim_w = to_friday_ffill(naaim)

f = pd.DataFrame(index=aaii_w.index)
bbs = aaii_w['bullish'] - aaii_w['bearish']
f['aaii_bull_bear_spread'] = bbs
f['aaii_bbs_z_52w']        = (bbs - bbs.rolling(52).mean()) / bbs.rolling(52).std()
f['aaii_bbs_pct_52w']      = bbs.rolling(52).rank(pct=True)
f['aaii_bull_5w_delta']    = aaii_w['bullish'] - aaii_w['bullish'].shift(5)
f['aaii_neutral_pct']      = aaii_w['neutral']

m = naaim_w['naaim_mean']
f['naaim_mean']       = m
f['naaim_z_26w']      = (m - m.rolling(26).mean()) / m.rolling(26).std()
f['naaim_delta_4w']   = m - m.shift(4)
f['naaim_dispersion'] = naaim_w['naaim_q3'] - naaim_w['naaim_q1']

print("f before dropna:")
print(f.isna().sum())
print("f shape before dropna:", f.shape)
f_dropped = f.dropna()
print("f_dropped shape:", f_dropped.shape)
print("f_dropped dates:", f_dropped.index.min(), f_dropped.index.max())

