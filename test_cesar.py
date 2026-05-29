import pandas as pd
import numpy as np
import xgboost as xgb
from itertools import product
import warnings; warnings.filterwarnings('ignore')

DATA = "data"
ETFS         = ['ACWI', 'AGG', 'GLD', 'BSV']
CLASS_OF     = {t: i for i, t in enumerate(ETFS)}    # ACWI=0, AGG=1, GLD=2, BSV=3
TRAIN_END    = pd.Timestamp('2024-12-31')
VAL_END      = pd.Timestamp('2025-12-31')

etfs  = pd.read_csv(DATA + '/etfs_daily.csv',   index_col=0, parse_dates=True)[ETFS]
aaii  = pd.read_csv(DATA + '/aaii_weekly.csv',  index_col=0, parse_dates=True)
naaim = pd.read_csv(DATA + '/naaim_weekly.csv', index_col=0, parse_dates=True)

fridays = etfs.index[etfs.index.weekday == 4]
def to_friday_ffill(df):
    return (df.reindex(df.index.union(fridays))
              .sort_index().ffill()
              .reindex(fridays))

etf_w   = etfs.reindex(fridays).ffill()
aaii_w  = to_friday_ffill(aaii)
naaim_w = to_friday_ffill(naaim)

def build_features(aaii_df, naaim_df):
    f = pd.DataFrame(index=aaii_df.index)
    bbs = aaii_df['bullish'] - aaii_df['bearish']
    f['aaii_bull_bear_spread'] = bbs
    f['aaii_bbs_z_52w']        = (bbs - bbs.rolling(52).mean()) / bbs.rolling(52).std()
    f['aaii_bbs_pct_52w']      = bbs.rolling(52).rank(pct=True)
    f['aaii_bull_5w_delta']    = aaii_df['bullish'] - aaii_df['bullish'].shift(5)
    f['aaii_neutral_pct']      = aaii_df['neutral']

    m = naaim_df['naaim_mean']
    f['naaim_mean']       = m
    f['naaim_z_26w']      = (m - m.rolling(26).mean()) / m.rolling(26).std()
    f['naaim_delta_4w']   = m - m.shift(4)
    f['naaim_dispersion'] = naaim_df['naaim_q3'] - naaim_df['naaim_q1']
    return f.dropna()

feats = build_features(aaii_w, naaim_w)
rets   = etf_w.pct_change().shift(-1)
labels = (rets.dropna().idxmax(axis=1).map(CLASS_OF).rename('y'))

common  = feats.index.intersection(labels.index)
X_all   = feats.loc[common]
y_all   = labels.loc[common].astype(int)
mask_tr = X_all.index <= TRAIN_END
mask_te = (X_all.index > TRAIN_END) & (X_all.index <= VAL_END)

print("Unique labels in train:", y_all[mask_tr].unique())
yr = 2010
tr = X_all[mask_tr].index.year < yr
print("yr=2010, num unique classes in y[tr]:", len(set(y_all[mask_tr][tr].unique())))
print("Unique classes in y[tr]:", y_all[mask_tr][tr].unique())
if len(set(y_all[mask_tr][tr].unique())) >= 4:
    try:
        model = xgb.XGBClassifier(objective='multi:softprob')
        model.fit(X_all[mask_tr][tr], y_all[mask_tr][tr])
        print("XGB fit OK!")
    except Exception as e:
        print("XGB fit failed!", e)
else:
    print("Skipped yr=2010")
