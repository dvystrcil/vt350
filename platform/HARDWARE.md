# What to run the tools on, and how long they take

The CAD checks here are slow. A full reach sweep of a printer model takes **hours on a laptop** and about **two hours
on a 32-thread server** sized the way ours was. This page says why, what hardware helps, and what we measured, so the
first long run doesn't come as a surprise. Every number below is from the VT350 model (FreeCAD 26.3rc2 AppImage,
`vt350-lite-75` … `lite-77`, about 1,300 solids, a 37 MB `.FCStd`). A smaller printer runs faster; a bigger one
slower.

## Why it's slow

- **Each check is many solid-on-solid booleans** (OpenCASCADE `common()`), one pose at a time. A boolean runs on one
  CPU core.
- **The tools run poses in parallel on worker processes** (`freecad/litepool.py`, `freecad/clashlib.py`), and **each
  worker opens its own copy of the model**. On the VT350, a worker needs 1.5–3 GB of memory.
- So **memory, not the number of cores, usually decides how many workers run**. A 12-thread laptop with 32 GB runs 4
  sweep workers. A 32-thread server ran only 5 until its job was given more memory (see
  [LESSONS.md](freecad/LESSONS.md), "Memory, not cores, sets a sweep's speed").
- A GPU doesn't help the CAD checks. Only the Blender renders use one.

## Recommended platforms

| | CPU | Memory | What it's like |
|---|---|---|---|
| **Minimum** | 6 cores / 12 threads | 32 GB | Passes, the FreeCAD GUI and quick checks are fine. A full sweep runs 4 workers and takes **many hours**; leave it overnight. |
| **Recommended** | 16 cores / 32 threads | 64 GB | A full sweep runs 10+ workers. Expect **about 1 hour** for the refresh sweep. |
| **Comfortable** | 32 threads | 128 GB | Room for a sweep's workers and other work at the same time. |

Disk is not the limit: a model and its outputs are a few hundred MB. Any recent SSD is fine.

**FreeCAD:** use the official AppImage from FreeCAD's GitHub releases, the same version everywhere you run the tools.
FreeCAD's mesh output differs between builds, so mixing versions makes results drift. The tools find it through
`FREECAD_APPIMAGE` (see [Settings](README.md#settings-the-values-file)).

## What we measured

Our two machines:

- **Laptop:** Intel Core i7-10750H (6 cores / 12 threads), 32 GB.
- **Server (max-01):** AMD Ryzen AI Max+ (Strix Halo), 32 threads, 128 GB shared with a local LLM. The tools run
  there in a Kubernetes job that gets 10 CPUs and a memory limit.

| Job | Where | Workers | Time |
|---|---|---|---|
| Print-part STL export (`derive_stls`) | server | 1 | 3½ min |
| Toolhead reach sweep + Z sweep (the refresh's long step) | server, 16 GiB limit | 5 (Z sweep: 2) | **1 h 58 min – 2 h 01 min** (lite-75, 76, 77) |
| … the Z sweep alone | server, 16 GiB limit | 2 | 22 min |
| Print area from the sweep's log | anywhere | — | 1 s |
| Front-edge reach study, 35 poses, one round | laptop | 4 | 1 h 29 min |
| Front-edge reach study, both heads, ~4 rounds each | laptop | 4 | **over 12 h** (the first head took about 10 h) |
| Opening the printer model in the FreeCAD GUI | laptop | — | 47 s (median, lite-52) |

Memory per worker on the same model:

| Worker | Peak |
|---|---|
| Clash sweep (`clashlib`) | 1.5–1.8 GB (lite-76/77); 2.5 GB on lite-35 |
| Z sweep (`litepool`) | 2.9 GB, plus 2.9 GB for the parent process |

## Making a run faster

- **Check how many workers it used.** The log says it near the start: `clashlib: 5 workers on …`. If that's far
  below your core count, memory capped it.
- **Give it memory, or tell it the budget.** The worker count is
  `min(CPUs − 2, (free MB − reserve) ÷ MB per worker)`. Set `VT350_WORKERS`, `VT350_WORKER_MB` and
  `VT350_RESERVE_MB` to override (these get neutral names in
  [#300](https://github.com/dvystrcil/vt350/issues/300)). In a container, the limit that counts is the container's,
  not the host's.
- **Run one heavy FreeCAD job at a time on a laptop.** Two at once ran the laptop out of memory and killed a model
  pass before it saved (2026-11-18).
- **Put the long, read-only studies on the biggest machine you have**, and keep the laptop for passes and the GUI.
- **Close the FreeCAD GUI** while a sweep runs: the open model holds several GB.
