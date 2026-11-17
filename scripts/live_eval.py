"""POST the brief's samples and the tricky cases to a deployed /score and check results.

Usage: python scripts/live_eval.py [BASE_URL] [ROUNDS]
Default BASE_URL is the production deployment. Exits non-zero if any call is wrong.
"""

import json
import pathlib
import sys
import time

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tests.fixtures import SAMPLES  # noqa: E402
from tests.tricky_cases import TRICKY  # noqa: E402

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://lead-scoring-eight.vercel.app").rstrip("/")
ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 1

cases = {k: {"request": v["request"], "scores": {v["expected"]["score"]}, "tier": v["expected"]["tier"]}
         for k, v in SAMPLES.items()}
cases.update(TRICKY)

times, wrong = [], []
with httpx.Client(timeout=40) as client:
    for rnd in range(1, ROUNDS + 1):
        for name, case in cases.items():
            start = time.perf_counter()
            r = client.post(f"{BASE}/score", json=case["request"])
            elapsed = time.perf_counter() - start
            times.append(elapsed)
            try:
                body = r.json()
            except ValueError:
                body = {"raw": r.text[:200]}
            ok = r.status_code == 200 and body.get("score") in case["scores"] and body.get("tier") == case["tier"]
            if not ok:
                wrong.append((rnd, name, r.status_code, json.dumps(body, ensure_ascii=False)[:400]))
            print(f"{'ok  ' if ok else 'FAIL'} r{rnd} {name:26} HTTP {r.status_code} {elapsed:5.2f}s "
                  f"score={body.get('score')} expected={sorted(case['scores'])} tier={body.get('tier')}")

times.sort()
print(f"\n{len(times)} calls, {len(wrong)} wrong; median {times[len(times) // 2]:.2f}s, max {times[-1]:.2f}s")
for w in wrong:
    print("WRONG", *w)
sys.exit(1 if wrong else 0)
