import sys
sys.path.insert(0, "src")
import pandas as pd
import src.diagnosis as diag
import traceback

df = pd.read_csv("data/reference_set.csv")
row = df.loc[df["payment_id"] == "PMT-00016"].iloc[0]

api_key = diag.os.environ.get("GEMINI_API_KEY")
client = diag.genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Respond ONLY with raw JSON: {\"status\": \"ok\"}"
    )
    print("SUCCESS:", response.text)
except Exception:
    traceback.print_exc()
