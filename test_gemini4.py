import sys
sys.path.insert(0, "src")
import src.diagnosis as diag

print("diag.genai:", diag.genai)
print("diag.json:", diag.json)
print("diag.os:", diag.os)
print("GEMINI_API_KEY via diag.os:", bool(diag.os.environ.get("GEMINI_API_KEY")))

import pandas as pd
df = pd.read_csv("data/reference_set.csv")
row = df.loc[df["failure_code"].eq("CARD_DECLINED_SOFT")].iloc[0]

api_key = diag.os.environ.get("GEMINI_API_KEY")
client = diag.genai.Client(api_key=api_key)

prompt = f"""You are an AI subscription payment diagnosis agent. Analyze this payment failure context and classify the failure category.

Payment Context:
- Failure Code: {row.get("failure_code")}
- Failure Category (raw): {row.get("failure_category")}
- Previous Successful Renewals: {row.get("previous_successes")}
- Previous Failures: {row.get("previous_failures")}
- Retry Count: {row.get("retry_count")}
- Customer LTV: INR {row.get("customer_ltv")}
- Subscription Age (days): {row.get("subscription_age_days")}
- Days Since Last Payment: {row.get("days_since_last_payment")}

Respond ONLY with raw JSON: {{"category": "TEMPORARY", "confidence": 0.85, "explanation": "example"}}
"""

try:
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    print("SUCCESS via module objects:", response.text)
except Exception as e:
    import traceback
    print("FAILED via module objects:")
    traceback.print_exc()
