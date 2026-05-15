MCDO TSP MECHANISM AUDIT V01
============================

Purpose:
Measure why MCDO improves TSPLIB routes.

Scope:
This is a mechanism audit, not a new optimization claim.

Benchmarks:
- dsj1000
- pr1002
- pcb1173

Compared modes:
- nearest_neighbor
- two_opt
- mcdo

Required metrics:
- tour_length
- gap_percent
- runtime_sec
- total_moves_checked
- improving_moves
- rejected_moves
- accepted_moves
- mcdo_pruned_moves
- mcdo_priority_hits
- mcdo_window_rejections
- improvement_per_1000_moves
- convergence_trace

Claim rule:
Do not claim global superiority.
Only report measured behavior on these benchmark runs.
