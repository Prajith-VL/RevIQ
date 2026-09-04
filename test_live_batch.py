import sys
sys.path.insert(0, "src")
import pandas as pd
from src.detection import detect_at_risk
import src.diagnosis as diag
import time
import traceback

reference = pd.read_csv("data/reference_set.csv")
at_risk = detect_at_risk(reference)

for idx, row in at_risk.iterrows():
    res = diag.classify_failure_deterministic(row)
    if res is None:
        pid = row["payment_id"]
        print("--- AI PATH for", pid, "---")
        try:
            api_key = diag.os.environ.get("GEMINI_API_KEY")
            client = diag.genai.Client(api_key=api_key)
            prompt = "You are an AI subscription payment diagnosis agent. Failure code: " + str(row.get("failure_code")) + ". Respond ONLY with raw JSON: {\"category\": \"TEMPORARY\", \"confidence\": 0.8, \"explanation\": \"x\"}"
            response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
            print("SUCCESS:", response.text[:80])
        except Exception:
            print("FAILED on", pid, ":")
            traceback.print_exc()
        time.sleep(4)
