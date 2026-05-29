import pandas as pd
import numpy as np
from datetime import datetime

y = pd.Series([0, 2], index=pd.to_datetime(['2010-01-01', '2010-01-02']))
tr = np.array([True, True])
print("y[tr]:", y[tr].values)
print("y[tr].unique():", y[tr].unique())
print("len(set):", len(set(y[tr].unique())))
