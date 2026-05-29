import pandas as pd
DATA = "data"
etfs  = pd.read_csv(DATA + '/etfs_daily.csv',   index_col=0, parse_dates=True)
print("etfs dates:", etfs.index.min(), etfs.index.max())
print("Number of fridays:", (etfs.index.weekday == 4).sum())
print("Value counts of years for fridays:")
print(etfs.index[etfs.index.weekday == 4].year.value_counts().sort_index())
