import pandas as pd
DATA = "data"
etfs  = pd.read_csv(DATA + '/etfs_daily.csv',   index_col=0, parse_dates=True)
aaii  = pd.read_csv(DATA + '/aaii_weekly.csv',  index_col=0, parse_dates=True)

print("etfs.index[0]:", repr(etfs.index[0]))
print("aaii.index[0]:", repr(aaii.index[0]))

try:
    fridays = etfs.index[etfs.index.weekday == 4]
    union = aaii.index.union(fridays)
    print("union sorted?", union.is_monotonic_increasing)
    print("first 5 of union:")
    print(union[:5])
    print("last 5 of union:")
    print(union[-5:])
except Exception as e:
    print("Exception:", e)
