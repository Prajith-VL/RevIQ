import os
import sys
sys.path.insert(0, "src")
import src.diagnosis as diag
import pandas as pd

df = pd.read_csv("data/reference_set.csv")
row = df.loc[df["failure_code"].eq("CARD_DECLINED_SOFT")].iloc[0]

result = diag.diagnose_with_ai(row)
print("RESULT:", result)
