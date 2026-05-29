import pandas as pd
DATA = "data"
aaii  = pd.read_csv(DATA + '/aaii_weekly.csv',  index_col=0, parse_dates=True)
etfs  = pd.read_csv(DATA + '/etfs_daily.csv',   index_col=0, parse_dates=True)
fridays = etfs.index[etfs.index.weekday == 4]
def to_friday_ffill(df):
    return (df.reindex(df.index.union(fridays))
              .sort_index().ffill()
              .reindex(fridays))

print("aaii head:")
print(aaii.head())
aaii_w  = to_friday_ffill(aaii)
print("aaii_w head:")
print(aaii_w.head())
