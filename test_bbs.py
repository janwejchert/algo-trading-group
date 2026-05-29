import pandas as pd
DATA = "data"
aaii  = pd.read_csv(DATA + '/aaii_weekly.csv',  index_col=0, parse_dates=True)
etfs  = pd.read_csv(DATA + '/etfs_daily.csv',   index_col=0, parse_dates=True)
fridays = etfs.index[etfs.index.weekday == 4]
def to_friday_ffill(df):
    return (df.reindex(df.index.union(fridays))
              .sort_index().ffill()
              .reindex(fridays))

aaii_w  = to_friday_ffill(aaii)
bbs = aaii_w['bullish'] - aaii_w['bearish']
print("Value counts for bbs:")
print(bbs.value_counts().head(10))

print("\nValue counts for aaii_w['bullish']:")
print(aaii_w['bullish'].value_counts().head(10))

print("\nUnique values in aaii_w['bullish']:", aaii_w['bullish'].nunique())
