import time, json, csv, hashlib
from pathlib import Path

ROOT = Path(r"C:\machura_ramsey_shadow_grid_1_10")
CASE = "R3_6"
A, B = 3, 6
LIMIT_SEC = 600
MAX_N = 20

RUN_ID = "SPEEDUP_D13R_V21_R3_6_" + time.strftime("%Y%m%d_%H%M%S")
OUT = ROOT / "08_SPEEDUP_D13R_V21" / "02_RUNS" / RUN_ID
REPORT = ROOT / "08_SPEEDUP_D13R_V21" / "03_REPORTS" / (RUN_ID + "_REPORT.txt")
FIG = ROOT / "08_SPEEDUP_D13R_V21" / "04_FIGURES" / (RUN_ID + "_PROGRESS.csv")
MANIFEST = ROOT / "08_SPEEDUP_D13R_V21" / "05_EVIDENCE_SHA256" / (RUN_ID + "_MANIFEST_SHA256.txt")

OUT.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)
FIG.parent.mkdir(parents=True, exist_ok=True)
MANIFEST.parent.mkdir(parents=True, exist_ok=True)

start = time.time()
rows = []

print("RUN_ID:", RUN_ID)
print("CASE: R(3,6)")
print("METHOD: MDO_SPEEDUP_D13R_V21_ACCELERATOR_ATTEMPT")
print("LIMIT_SEC:", LIMIT_SEC)

# V01 placeholder controller record.
# This file establishes controlled one-case run protocol.
# Next revision plugs in the real D13R V21 branching/cut engine.

status = "PROTOCOL_CREATED_NEEDS_ENGINE_BINDING"
reason = "This run initialized the controlled R(3,6) speedup protocol. Real D13R V21 engine binding is next."

for n in range(1, MAX_N + 1):
    elapsed = time.time() - start
    if elapsed > LIMIT_SEC:
        status = "TIME_LIMIT_REACHED"
        reason = "Stopped by time limit before engine binding/computation."
        break

    rows.append({
        "case": "R(3,6)",
        "n": n,
        "elapsed_sec": round(elapsed, 6),
        "method": "MDO_SPEEDUP_D13R_V21_PROTOCOL",
        "status": "WAITING_FOR_ENGINE_BINDING"
    })

    print(f"[{n}/{MAX_N}] R(3,6) protocol checkpoint elapsed={elapsed:.2f}s")
    time.sleep(0.02)

with open(FIG, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["case","n","elapsed_sec","method","status"])
    w.writeheader()
    w.writerows(rows)

summary = {
    "run_id": RUN_ID,
    "case": "R(3,6)",
    "a": A,
    "b": B,
    "method": "MDO_SPEEDUP_D13R_V21_ACCELERATOR_ATTEMPT",
    "status": status,
    "reason": reason,
    "limit_sec": LIMIT_SEC,
    "elapsed_sec": round(time.time() - start, 6),
    "claim": "NO_RAMSEY_VALUE_CLAIM",
    "next_step": "Bind real MDO_RAMSEY_MEGA_SPEEDUP_D13R_V21 engine logic to this single-case protocol."
}

(OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

REPORT.write_text(
    "MDO SPEEDUP D13R V21 SINGLE CASE RUN\n"
    "====================================\n\n"
    f"RUN_ID: {RUN_ID}\n"
    "CASE: R(3,6)\n"
    "METHOD: MDO_SPEEDUP_D13R_V21_ACCELERATOR_ATTEMPT\n"
    f"STATUS: {status}\n"
    f"REASON: {reason}\n"
    "CLAIM: NO_RAMSEY_VALUE_CLAIM\n\n"
    "This file creates the clean one-case speedup run protocol.\n"
    "The real D13R V21 engine binding is the next implementation step.\n",
    encoding="utf-8"
)

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

files = [OUT / "summary.json", REPORT, FIG]
MANIFEST.write_text(
    "\n".join(f"{sha(p)}  {p.relative_to(ROOT)}" for p in files) + "\n",
    encoding="utf-8"
)

print("DONE")
print("OUT:", OUT)
print("REPORT:", REPORT)
print("MANIFEST:", MANIFEST)
