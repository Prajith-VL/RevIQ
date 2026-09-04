import sys
sys.path.insert(0, "src")
import src.diagnosis as diag
import pandas as pd

df = pd.read_csv("data/reference_set.csv")
row = df.loc[df["failure_code"].eq("CARD_DECLINED_SOFT")].iloc[1]

api_key = diag.os.environ.get("GEMINI_API_KEY")
client = diag.genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Respond ONLY with raw JSON: {\"status\": \"ok\"}"
    )
    print("SUCCESS:", response.text)
except Exception as e:
    import traceback
    print("ERROR TYPE:", type(e).__name__)
    traceback.print_exc()
