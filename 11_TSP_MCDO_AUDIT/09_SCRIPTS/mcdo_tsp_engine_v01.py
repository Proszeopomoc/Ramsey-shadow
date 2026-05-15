from pathlib import Path
from array import array
import argparse
import csv
import hashlib
import json
import math
import random
import time

ROOT = Path(r"C:\machura_ramsey_shadow_grid_1_10")
BASE = ROOT / "11_TSP_MCDO_AUDIT"

OPTIMA = {
    "dsj1000": 18659688,
    "pr1002": 259045,
    "pcb1173": 56892,
}

def now_id():
    return time.strftime("%Y%m%d_%H%M%S")

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def parse_tsp(path):
    name = path.stem
    weight_type = "EUC_2D"
    coords = []
    in_coords = False

    for raw in path.read_text(errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue

        u = line.upper()

        if u.startswith("NAME"):
            parts = line.replace(":", " ").split()
            if len(parts) >= 2:
                name = parts[1]

        if u.startswith("EDGE_WEIGHT_TYPE"):
            parts = line.replace(":", " ").split()
            if len(parts) >= 2:
                weight_type = parts[1].upper()

        if u.startswith("NODE_COORD_SECTION"):
            in_coords = True
            continue

        if u.startswith("EOF"):
            break

        if in_coords:
            parts = line.split()
            if len(parts) >= 3:
                coords.append((float(parts[1]), float(parts[2])))

    if not coords:
        raise ValueError(f"No coordinates found in {path}")

    return {
        "name": name,
        "path": str(path),
        "weight_type": weight_type,
        "coords": coords,
    }

def distance_value(a, b, weight_type):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    d = math.sqrt(dx * dx + dy * dy)

    if weight_type == "CEIL_2D":
        return int(math.ceil(d))
    return int(round(d))

def build_distance_matrix(coords, weight_type):
    n = len(coords)
    mat = []
    for i in range(n):
        row = array("I", [0]) * n
        ai = coords[i]
        for j in range(n):
            if i != j:
                row[j] = distance_value(ai, coords[j], weight_type)
        mat.append(row)
    return mat

def build_candidate_lists(dist, k):
    n = len(dist)
    cand = []
    for i in range(n):
        order = sorted(range(n), key=lambda j: dist[i][j] if j != i else 10**18)
        cand.append([j for j in order if j != i][:k])
    return cand

def tour_length(tour, dist):
    n = len(tour)
    return sum(dist[tour[i]][tour[(i + 1) % n]] for i in range(n))

def nearest_neighbor(dist, start=0):
    n = len(dist)
    unused = set(range(n))
    tour = [start]
    unused.remove(start)

    while unused:
        last = tour[-1]
        nxt = min(unused, key=lambda v: dist[last][v])
        tour.append(nxt)
        unused.remove(nxt)

    return tour

def reverse_segment(tour, pos, i, j):
    tour[i:j+1] = reversed(tour[i:j+1])
    for k in range(i, j + 1):
        pos[tour[k]] = k

def two_opt_candidate(
    tour,
    dist,
    cand,
    max_passes=100,
    max_seconds=30.0,
    mode="two_opt",
    seed=1,
    edge_pool=250,
):
    rng = random.Random(seed)
    n = len(tour)
    pos = [0] * n
    for i, v in enumerate(tour):
        pos[v] = i

    started = time.time()
    current = tour_length(tour, dist)
    initial = current
    trace = []

    metrics = {
        "mode": mode,
        "initial_length": initial,
        "final_length": None,
        "runtime_sec": None,
        "passes": 0,
        "total_moves_checked": 0,
        "improving_moves": 0,
        "accepted_moves": 0,
        "rejected_moves": 0,
        "mcdo_pruned_moves": 0,
        "mcdo_priority_hits": 0,
        "mcdo_window_rejections": 0,
        "gain_total": 0,
        "gain_per_1000_moves": 0.0,
    }

    trace.append({
        "pass": 0,
        "elapsed_sec": 0.0,
        "tour_length": current,
        "accepted_moves": 0,
        "moves_checked": 0,
    })

    for p in range(1, max_passes + 1):
        if time.time() - started > max_seconds:
            break

        improved = False
        accepted_this_pass = 0

        edge_indices = list(range(n))

        if mode == "mcdo":
            edge_indices.sort(
                key=lambda i: dist[tour[i]][tour[(i + 1) % n]],
                reverse=True
            )
            edge_indices = edge_indices[:min(edge_pool, n)]
        else:
            rng.shuffle(edge_indices)

        best_delta = 0
        best_pair = None

        for i in edge_indices:
            if time.time() - started > max_seconds:
                break

            a = tour[i]
            b = tour[(i + 1) % n]
            ab = dist[a][b]

            local_candidates = cand[a]

            for c in local_candidates:
                j = pos[c]

                if j == i:
                    continue
                if (i + 1) % n == j:
                    continue
                if (j + 1) % n == i:
                    continue

                i1, j1 = i, j
                if j1 < i1:
                    i1, j1 = j1, i1

                if i1 == 0 and j1 == n - 1:
                    continue

                a2 = tour[i1]
                b2 = tour[(i1 + 1) % n]
                c2 = tour[j1]
                d2 = tour[(j1 + 1) % n]

                old_len = dist[a2][b2] + dist[c2][d2]
                new_len = dist[a2][c2] + dist[b2][d2]
                delta = new_len - old_len

                metrics["total_moves_checked"] += 1

                if mode == "mcdo":
                    long_edge_pressure = old_len
                    if long_edge_pressure < ab:
                        metrics["mcdo_window_rejections"] += 1
                        continue

                    if delta >= 0:
                        metrics["mcdo_pruned_moves"] += 1
                        continue

                    score = delta - 0.001 * long_edge_pressure

                    if score < best_delta:
                        best_delta = score
                        best_pair = (i1 + 1, j1, delta)
                        metrics["mcdo_priority_hits"] += 1

                else:
                    if delta < best_delta:
                        best_delta = delta
                        best_pair = (i1 + 1, j1, delta)

        if best_pair is not None:
            l, r, real_delta = best_pair
            reverse_segment(tour, pos, l, r)
            current += real_delta
            metrics["improving_moves"] += 1
            metrics["accepted_moves"] += 1
            metrics["gain_total"] += -real_delta
            accepted_this_pass += 1
            improved = True
        else:
            metrics["rejected_moves"] += 1

        metrics["passes"] = p

        trace.append({
            "pass": p,
            "elapsed_sec": round(time.time() - started, 6),
            "tour_length": current,
            "accepted_moves": metrics["accepted_moves"],
            "moves_checked": metrics["total_moves_checked"],
        })

        if not improved:
            break

    metrics["final_length"] = current
    metrics["runtime_sec"] = round(time.time() - started, 6)

    if metrics["total_moves_checked"] > 0:
        metrics["gain_per_1000_moves"] = (
            metrics["gain_total"] / metrics["total_moves_checked"] * 1000.0
        )

    return tour, metrics, trace

def gap_percent(length, optimum):
    if not optimum:
        return None
    return (length - optimum) / optimum * 100.0

def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def run_instance(tsp_path, run_dir, candidate_k, max_passes, max_seconds, seed):
    inst = parse_tsp(tsp_path)
    name = Path(inst["name"]).stem
    coords = inst["coords"]
    weight_type = inst["weight_type"]
    n = len(coords)
    optimum = OPTIMA.get(name.lower())

    print(f"INSTANCE {name} n={n} weight={weight_type}")

    dist = build_distance_matrix(coords, weight_type)
    cand = build_candidate_lists(dist, candidate_k)

    rows = []
    traces = []

    # nearest neighbor
    t0 = time.time()
    nn_tour = nearest_neighbor(dist, start=0)
    nn_len = tour_length(nn_tour, dist)
    nn_time = time.time() - t0

    rows.append({
        "instance": name,
        "method": "nearest_neighbor",
        "n": n,
        "length": nn_len,
        "optimum": optimum,
        "gap_percent": gap_percent(nn_len, optimum),
        "runtime_sec": round(nn_time, 6),
        "passes": 0,
        "total_moves_checked": 0,
        "improving_moves": 0,
        "accepted_moves": 0,
        "rejected_moves": 0,
        "mcdo_pruned_moves": 0,
        "mcdo_priority_hits": 0,
        "mcdo_window_rejections": 0,
        "gain_per_1000_moves": 0.0,
    })

    # two opt from NN
    two_tour = list(nn_tour)
    two_tour, two_metrics, two_trace = two_opt_candidate(
        two_tour,
        dist,
        cand,
        max_passes=max_passes,
        max_seconds=max_seconds,
        mode="two_opt",
        seed=seed,
    )

    rows.append({
        "instance": name,
        "method": "two_opt",
        "n": n,
        "length": two_metrics["final_length"],
        "optimum": optimum,
        "gap_percent": gap_percent(two_metrics["final_length"], optimum),
        "runtime_sec": two_metrics["runtime_sec"],
        "passes": two_metrics["passes"],
        "total_moves_checked": two_metrics["total_moves_checked"],
        "improving_moves": two_metrics["improving_moves"],
        "accepted_moves": two_metrics["accepted_moves"],
        "rejected_moves": two_metrics["rejected_moves"],
        "mcdo_pruned_moves": two_metrics["mcdo_pruned_moves"],
        "mcdo_priority_hits": two_metrics["mcdo_priority_hits"],
        "mcdo_window_rejections": two_metrics["mcdo_window_rejections"],
        "gain_per_1000_moves": two_metrics["gain_per_1000_moves"],
    })

    for r in two_trace:
        r2 = dict(r)
        r2["instance"] = name
        r2["method"] = "two_opt"
        traces.append(r2)

    # mcdo from NN
    mcdo_tour = list(nn_tour)
    mcdo_tour, mcdo_metrics, mcdo_trace = two_opt_candidate(
        mcdo_tour,
        dist,
        cand,
        max_passes=max_passes,
        max_seconds=max_seconds,
        mode="mcdo",
        seed=seed,
        edge_pool=min(300, n),
    )

    rows.append({
        "instance": name,
        "method": "mcdo",
        "n": n,
        "length": mcdo_metrics["final_length"],
        "optimum": optimum,
        "gap_percent": gap_percent(mcdo_metrics["final_length"], optimum),
        "runtime_sec": mcdo_metrics["runtime_sec"],
        "passes": mcdo_metrics["passes"],
        "total_moves_checked": mcdo_metrics["total_moves_checked"],
        "improving_moves": mcdo_metrics["improving_moves"],
        "accepted_moves": mcdo_metrics["accepted_moves"],
        "rejected_moves": mcdo_metrics["rejected_moves"],
        "mcdo_pruned_moves": mcdo_metrics["mcdo_pruned_moves"],
        "mcdo_priority_hits": mcdo_metrics["mcdo_priority_hits"],
        "mcdo_window_rejections": mcdo_metrics["mcdo_window_rejections"],
        "gain_per_1000_moves": mcdo_metrics["gain_per_1000_moves"],
    })

    for r in mcdo_trace:
        r2 = dict(r)
        r2["instance"] = name
        r2["method"] = "mcdo"
        traces.append(r2)

    write_csv(
        run_dir / f"{name}_results.csv",
        rows,
        [
            "instance","method","n","length","optimum","gap_percent","runtime_sec",
            "passes","total_moves_checked","improving_moves","accepted_moves",
            "rejected_moves","mcdo_pruned_moves","mcdo_priority_hits",
            "mcdo_window_rejections","gain_per_1000_moves"
        ],
    )

    write_csv(
        run_dir / f"{name}_trace.csv",
        traces,
        ["instance","method","pass","elapsed_sec","tour_length","accepted_moves","moves_checked"],
    )

    report = []
    report.append(f"TSP MCDO ENGINE V01 REPORT")
    report.append(f"INSTANCE: {name}")
    report.append(f"N: {n}")
    report.append(f"WEIGHT_TYPE: {weight_type}")
    report.append(f"OPTIMUM: {optimum}")
    report.append("")
    for r in rows:
        report.append(
            f"{r['method']}: length={r['length']} gap={r['gap_percent']} time={r['runtime_sec']} "
            f"moves={r['total_moves_checked']} gain_per_1000_moves={r['gain_per_1000_moves']}"
        )
    report.append("")
    report.append("CLAIM: measured behavior only on this run.")
    (run_dir / f"{name}_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")

    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(BASE / "00_INPUT"))
    ap.add_argument("--candidate-k", type=int, default=40)
    ap.add_argument("--max-passes", type=int, default=120)
    ap.add_argument("--max-seconds", type=float, default=30.0)
    ap.add_argument("--seed", type=int, default=123)
    args = ap.parse_args()

    input_dir = Path(args.input)
    tsp_files = sorted(input_dir.glob("*.tsp"))

    if not tsp_files:
        print("NO_TSP_FILES_FOUND")
        print(f"Put dsj1000.tsp, pr1002.tsp, pcb1173.tsp into: {input_dir}")
        return

    run_id = "MCDO_TSP_ENGINE_V01_" + now_id()
    run_dir = BASE / "01_RUNS" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []

    config = {
        "run_id": run_id,
        "input_dir": str(input_dir),
        "candidate_k": args.candidate_k,
        "max_passes": args.max_passes,
        "max_seconds_per_method": args.max_seconds,
        "seed": args.seed,
        "claim_rule": "measured behavior only"
    }
    (run_dir / "CONFIG.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    for tsp in tsp_files:
        all_rows.extend(run_instance(
            tsp,
            run_dir,
            candidate_k=args.candidate_k,
            max_passes=args.max_passes,
            max_seconds=args.max_seconds,
            seed=args.seed,
        ))

    write_csv(
        run_dir / "ALL_RESULTS.csv",
        all_rows,
        [
            "instance","method","n","length","optimum","gap_percent","runtime_sec",
            "passes","total_moves_checked","improving_moves","accepted_moves",
            "rejected_moves","mcdo_pruned_moves","mcdo_priority_hits",
            "mcdo_window_rejections","gain_per_1000_moves"
        ],
    )

    summary_lines = ["MCDO TSP ENGINE V01 SUMMARY", ""]
    for r in all_rows:
        summary_lines.append(
            f"{r['instance']} | {r['method']} | length={r['length']} | gap={r['gap_percent']} | time={r['runtime_sec']}"
        )

    (BASE / "02_REPORTS" / f"{run_id}_SUMMARY.txt").write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8"
    )

    manifest_files = list(run_dir.glob("*")) + [BASE / "02_REPORTS" / f"{run_id}_SUMMARY.txt"]
    manifest_path = BASE / "04_EVIDENCE_SHA256" / f"{run_id}_MANIFEST_SHA256.txt"
    manifest_path.write_text(
        "\n".join(f"{sha256_file(p)}  {p}" for p in manifest_files if p.is_file()) + "\n",
        encoding="utf-8"
    )

    print("DONE")
    print("RUN_DIR:", run_dir)
    print("SUMMARY:", BASE / "02_REPORTS" / f"{run_id}_SUMMARY.txt")
    print("MANIFEST:", manifest_path)

if __name__ == "__main__":
    main()
