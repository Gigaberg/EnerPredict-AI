# test_predict.py
import requests, json, os  # type: ignore[import-not-found]

BASE = "http://localhost:8000"
feat_order = None

# try backend endpoint first
try:
    r = requests.get(f"{BASE}/predict/feature_order", timeout=5)
    j = r.json()
    feat_order = j.get("feature_order") if isinstance(j, dict) else j
except Exception:
    # fallback to local file
    local = os.path.join("AIRES_Backend","data","feature_order.json")
    with open(local, "r") as fh:
        feat_order = json.load(fh).get("feature_order")

print("Loaded feature_order length:", len(feat_order))
# build a safe features vector: zeros, but set a few sensible numeric fields if present
features = [0.0] * len(feat_order)
def set_if_exists(name, val):
    if name in feat_order:
        features[feat_order.index(name)] = val

# sensible defaults — adjust if your names differ
set_if_exists("MonthlyHours", 300)
set_if_exists("SolarGeneration_kWh", 50)
set_if_exists("GridConsumption_kWh", 250)
set_if_exists("TariffRate", 5.0)
set_if_exists("Fan", 1)
set_if_exists("AirConditioner", 1)

payload = {
    "house_id": "python_smoke_1",
    "model": "xgb",   # change to "rf" or "linear" to test others
    "features": features,
    "meta": {"source": "test_predict.py"}
}

resp = requests.post(f"{BASE}/predict/", json=payload, timeout=10)
print("status:", resp.status_code)
try:
    print(json.dumps(resp.json(), indent=2))
except Exception as e:
    print("Response text:", resp.text)
    print("Error:", e)