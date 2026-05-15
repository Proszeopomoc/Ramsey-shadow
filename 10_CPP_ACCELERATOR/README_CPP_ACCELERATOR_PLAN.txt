C++ ACCELERATOR PLAN
====================

Purpose:
Move heavy MDO speedup search loops from Python to C++.

Reason:
Python is used for orchestration, reports, SHA256 manifests, and plots.
C++ is used for high-speed bitmask search, pruning, and DFS.

Expected benefit:
Approx. 4x or more speedup for tight inner loops, depending on case.

First target:
R(3,6)

Reference target mode:
critical_n = 17
boundary_n = 18

Rules:
- do not compute n=1..16 when target boundary is known as checkpoint
- n=17: stop on first valid clean graph
- n=18: search for closure / no clean graph, with author-controlled time limit
- record partial status if stopped

No external solver rule:
C++ accelerator must not use SAT/CP/ILP/external graph solvers.
