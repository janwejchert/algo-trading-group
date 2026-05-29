import pandas as pd
DATA = "data"
etfs  = pd.read_csv(DATA + '/etfs_daily.csv',   index_col=0, parse_dates=True)
aaii  = pd.read_csv(DATA + '/aaii_weekly.csv',  index_col=0, parse_dates=True)

fridays = etfs.index[etfs.index.weekday == 4]
print("Intersection length:", len(aaii.index.intersection(fridays)))
print(fridays[:5])
print(aaii.index[aaii.index > '2007-01-01'][:5])
