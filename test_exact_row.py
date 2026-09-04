import sys
sys.path.insert(0, "src")
import src.diagnosis as diag
import pandas as pd
import json

df = pd.read_csv("data/reference_set.csv")
row = df.loc[df["payment_id"] == "PMT-00006"].iloc[0]

print("ROW DATA:")
print(row)

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

You must respond ONLY with a raw JSON object and no other text, markdown formatting, or preamble. Example:
{{"category": "TEMPORARY", "confidence": 0.85, "explanation": "example"}}
"""

try:
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    print("RAW:", repr(response.text))
    content = response.text.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            content = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])
    content = content.strip()
    parsed = json.loads(content)
    print("PARSED OK:", parsed)
except Exception as e:
    import traceback
    print("REAL ERROR:")
    traceback.print_exc()
