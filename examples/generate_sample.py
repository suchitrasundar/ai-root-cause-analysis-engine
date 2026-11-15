"""Generate a deterministic sample incident: a cost-saving change shrinks a DB connection pool,
causing connection timeouts and a latency spike 20 minutes after deploy. Includes decoy changes."""
import csv
import json
import random
from datetime import datetime, timedelta, timezone

random.seed(7)
T0 = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)   # baseline starts
START = datetime(2026, 11, 10, 14, 0, tzinfo=timezone.utc)  # incident window starts
END = datetime(2026, 11, 10, 14, 30, tzinfo=timezone.utc)
iso = lambda d: d.isoformat().replace("+00:00", "Z")

logs = []
for m in range(0, 150):
    t = T0 + timedelta(minutes=m)
    logs.append({"ts": iso(t), "level": "INFO", "service": "checkout-service", "message": f"Order {1000 + m} processed in {random.randint(80, 140)} ms"})
    if m % 20 == 0:  # constant background noise that must not be flagged
        logs.append({"ts": iso(t), "level": "WARN", "service": "email-service", "message": f"Retrying email send for user {random.randint(1, 999)}"})
for m in range(0, 30):
    t = START + timedelta(minutes=m)
    for _ in range(4):
        logs.append({"ts": iso(t + timedelta(seconds=random.randint(0, 59))), "level": "ERROR", "service": "checkout-service",
                     "message": f"Timeout acquiring connection from pool after {30000} ms (pool size 5, active 5)"})
    if m % 20 == 0:
        logs.append({"ts": iso(t), "level": "WARN", "service": "email-service", "message": f"Retrying email send for user {random.randint(1, 999)}"})

metrics = []
for m in range(0, 150):
    t = T0 + timedelta(minutes=m)
    metrics.append({"ts": iso(t), "metric": "checkout_p99_latency_ms", "value": round(random.gauss(220, 12), 1)})
    metrics.append({"ts": iso(t), "metric": "email_queue_depth", "value": round(random.gauss(40, 5), 1)})
for m in range(0, 30):
    t = START + timedelta(minutes=m)
    metrics.append({"ts": iso(t), "metric": "checkout_p99_latency_ms", "value": round(random.gauss(3100, 150), 1)})
    metrics.append({"ts": iso(t), "metric": "email_queue_depth", "value": round(random.gauss(40, 5), 1)})

changes = [
    {"id": "a1c9e02", "ts": iso(START - timedelta(hours=19)), "author": "dev1", "title": "Update README with onboarding steps", "files": ["README.md"]},
    {"id": "7be4f10", "ts": iso(START - timedelta(hours=3)), "author": "dev2", "title": "Refresh email templates", "files": ["email-service/templates/welcome.html"]},
    {"id": "d93b5a7", "ts": iso(START - timedelta(minutes=25)), "author": "dev3",
     "title": "Reduce database connection pool size from 50 to 5 to save cost", "files": ["checkout-service/config/database.yml"]},
]

with open("examples/logs.jsonl", "w") as f:
    f.write("\n".join(json.dumps(r) for r in sorted(logs, key=lambda r: r["ts"])) + "\n")
with open("examples/metrics.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["ts", "metric", "value"]); w.writeheader(); w.writerows(sorted(metrics, key=lambda r: r["ts"]))
with open("examples/changes.json", "w") as f:
    json.dump(changes, f, indent=2)
print("incident window:", iso(START), iso(END))
