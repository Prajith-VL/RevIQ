import sys
sys.path.insert(0, "src")
import pandas as pd
import src.diagnosis as diag

df = pd.read_csv("data/reference_set.csv")
row = df.loc[df["payment_id"] == "PMT-00006"].iloc[0]

result = diag.diagnose_with_ai(row)
print("RESULT:", result)
