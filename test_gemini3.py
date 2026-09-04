import os
import sys
sys.path.insert(0, "src")
import pandas as pd
from google import genai
import json

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

df = pd.read_csv("data/reference_set.csv")
row = df.loc[df["failure_code"].eq("CARD_DECLINED_SOFT")].iloc[0]

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

Based on the failure code and the customer''s history, determine the most likely root-cause failure category.
The category must be one of: TEMPORARY, CUSTOMER_ACTION_NEEDED, PERMANENT, AMBIGUOUS.
Assign a confidence score between 0.0 and 1.0.
Provide a 1-2 sentence explanation in plain English suitable for an audit log.

You must respond ONLY with a raw JSON object and no other text, markdown formatting, or preamble. Example:
{{"category": "TEMPORARY", "confidence": 0.85, "explanation": "example"}}
"""

try:
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    content = response.text.strip()
    print("RAW:", repr(content))
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            content = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])
    content = content.strip()
    parsed = json.loads(content)
    print("PARSED:", parsed)
except Exception as e:
    import traceback
    print("REAL ERROR:")
    traceback.print_exc()
