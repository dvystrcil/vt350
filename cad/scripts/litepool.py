# litepool: a pool of persistent worker processes for litelib's checks (#45). No FreeCAD import here, so the
# worker count and the pool itself are tested with plain python3 (test_litepool.py, in CI).
#
#   pool = litepool.Pool(n, cmd=FREECADCMD, path=[scripts dir])
#   pool.map("litelib", "_t_vol", [(a, b), ...]) -> [("ok", value) | ("err", message) | ("stale", message), ...]
#   pool.close()
#
# Each worker is `cmd + [this file]`, started once and kept for every later map. It talks to the parent over a
# socketpair (fd in LITEPOOL_FD, removed from its environment at once), imports the op's module by name and calls
# module.fn(*args). Tasks are handed out one at a time to whichever worker is free, and the results come back in
# input order. An op that raises returns ("err", str(exception)); one that raises a class named Stale returns
# ("stale", ...), which tells the parent to redo that task itself. A worker that dies fails the map (RuntimeError),
# never a hang. Nothing here decides a result: the parent gets exactly what the op returned.
#
# Worker count = min(CPU count, memory cap). CPU count: VT350_WORKERS pins it (an integer >= 1; anything else is an
# error, not a guess); unset, the CPUs this process may actually use, minus 2. os.cpu_count() is the host's count: in
# a pod it ignores the cgroup CPU quota and the affinity mask, so available_cpus() reads both. Memory cap: every
# worker opens its own copy of the documents, so (available MB - RESERVE_MB) // WORKER_MB, at least 1 (serial); a pin
# can lower the count, never raise it past the cap. Available MB = MemAvailable, capped by the cgroup's memory.max -
# memory.current (in a pod /proc/meminfo is the host's). VT350_WORKER_MB / VT350_RESERVE_MB override the budget.
# (#45: 4 workers that each opened the 173 MB printer model and the filter took the laptop to ~1 GB free.)
import math, os, pickle, shutil, socket, subprocess, sys, tempfile
import weakref
from multiprocessing.connection import Connection, wait

HERE = os.path.abspath(__file__) if "__file__" in globals() else None
WORKER_MB = 2000        # one worker: ~0.5 GB at rest (trimmed) + its task; the worst light task measured on lite-30's
                        # parts peaked at 1.53 GB. The 10 GB distance to the carbon basket stays in the parent (litelib)
RESERVE_MB = 12000      # the parent pass: it keeps the heavy distance, so it can reach serial's peak (lite-30: 11.85 GB)


class Stale(Exception):
    """Raised by an op when its inputs don't match the parent's (e.g. a document shape changed in memory)."""


def _quota(root):
    """CPU limit from the cgroup (v2 cpu.max, else v1 cfs quota/period), rounded up; None when unlimited/unknown."""
    try:
        q, p = open(os.path.join(root, "cpu.max")).read().split()[:2]
        return None if q == "max" else max(1, math.ceil(int(q) / int(p)))
    except (OSError, ValueError): pass
    try:
        q = int(open(os.path.join(root, "cpu", "cpu.cfs_quota_us")).read())
        p = int(open(os.path.join(root, "cpu", "cpu.cfs_period_us")).read())
        return None if q <= 0 else max(1, math.ceil(q / p))
    except (OSError, ValueError): return None


def available_cpus(affinity=None, root="/sys/fs/cgroup"):
    """CPUs this process can really use: its affinity mask, capped by the cgroup CPU quota."""
    if affinity is None:
        try: affinity = os.sched_getaffinity(0)
        except AttributeError: affinity = range(os.cpu_count() or 1)
    n = len(affinity)
    q = _quota(root)
    return min(n, q) if q else n


def available_mb(meminfo="/proc/meminfo", root="/sys/fs/cgroup"):
    """MB this process can still take: MemAvailable, capped by the cgroup v2 limit (memory.max - memory.current)."""
    mb = None
    for line in open(meminfo):
        if line.startswith("MemAvailable:"): mb = int(line.split()[1]) // 1024
    try:
        lim = open(os.path.join(root, "memory.max")).read().strip()
        if lim != "max":
            cg = (int(lim) - int(open(os.path.join(root, "memory.current")).read())) // (1024 * 1024)
            mb = cg if mb is None else min(mb, cg)
    except (OSError, ValueError): pass
    if mb is None: raise RuntimeError(f"no MemAvailable in {meminfo}")
    return mb


def _env_int(env, k, lo):
    v = env[k]
    try: n = int(v)
    except ValueError: raise ValueError(f"{k}={v!r} is not an integer")
    if n < lo: raise ValueError(f"{k}={v!r} must be >= {lo}")
    return n


def worker_count(env=None, cpus=None, mem_mb=None, per_worker_mb=None, reserve_mb=None):
    """min(VT350_WORKERS or available CPUs - 2, (available MB - reserve) // per-worker MB), at least 1."""
    env = os.environ if env is None else env
    if "VT350_WORKERS" in env: n = _env_int(env, "VT350_WORKERS", 1)
    else: n = (available_cpus() if cpus is None else cpus) - 2
    per = per_worker_mb or (_env_int(env, "VT350_WORKER_MB", 1) if "VT350_WORKER_MB" in env else WORKER_MB)
    res = reserve_mb if reserve_mb is not None else (_env_int(env, "VT350_RESERVE_MB", 0) if "VT350_RESERVE_MB" in env
                                                      else RESERVE_MB)
    mem = available_mb() if mem_mb is None else mem_mb
    return max(1, min(n, (mem - res) // per))


def _discard(procs, d):
    """Pool clean-up that needs no Pool: end any worker still running, remove the dir."""
    for pr in procs:
        if pr.poll() is None:
            pr.kill(); pr.wait()
    shutil.rmtree(d, ignore_errors=True)


class Pool:
    def __init__(self, n, cmd, path=(), cwd=None, env=None):
        self.n = n
        self.dir = tempfile.mkdtemp(prefix="litepool-")
        self.procs, self.conns, self.errs = [], [], []
        # close() is the normal path; this also runs if the pool is dropped or the process exits without close()
        self._discard = weakref.finalize(self, _discard, self.procs, self.dir)
        base = dict(os.environ if env is None else env, LITEPOOL_PATH=os.pathsep.join(path))
        for k in range(n):
            a, b = socket.socketpair()
            err = os.path.join(self.dir, f"w{k}.err")
            with open(err, "w") as ef:
                pr = subprocess.Popen(list(cmd) + [HERE], env=dict(base, LITEPOOL_FD=str(b.fileno())),
                                      pass_fds=(b.fileno(),), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                      stderr=ef, cwd=cwd or self.dir)
            b.close()
            self.procs.append(pr); self.conns.append(Connection(a.detach())); self.errs.append(err)

    def _dead(self, i, why):
        tail = ""
        try: tail = open(self.errs[i]).read()[-1500:]
        except OSError: pass
        return RuntimeError(f"litepool worker {i} (pid {self.procs[i].pid}) {why}; stderr tail: {tail!r}")

    def map(self, module, fn, tasks):
        tasks = list(tasks)
        out = [None] * len(tasks)
        todo = iter(enumerate(tasks))
        busy = {}

        def feed(i):
            nxt = next(todo, None)
            if nxt is None: return
            try: self.conns[i].send((nxt[0], module, fn, nxt[1]))
            except OSError: raise self._dead(i, "is gone")
            busy[self.conns[i]] = i

        for i in range(self.n): feed(i)
        while busy:
            for c in wait(list(busy), timeout=60):
                i = busy.pop(c)
                try: tid, res = c.recv()
                except (EOFError, OSError): raise self._dead(i, f"died (exit {self.procs[i].poll()})")
                out[tid] = res
                feed(i)
            for c, i in busy.items():                      # nothing came back for a while: is anyone dead?
                if self.procs[i].poll() is not None and not c.poll(): raise self._dead(i, f"exited {self.procs[i].returncode}")
        return out

    def close(self):
        for c in self.conns:
            try: c.send(None)
            except OSError: pass
        for pr in self.procs:
            try: pr.wait(timeout=30)
            except subprocess.TimeoutExpired: pr.kill(); pr.wait()
        for c in self.conns:
            try: c.close()
            except OSError: pass
        self.conns = []
        self._discard()


# ----------------------------------------------------------------------------------------------------- worker side
TRIMS = 0


def trim():
    """Give freed heap back to the OS (glibc malloc_trim). Without it a worker keeps its high-water mark: one
    distToShape against the StealthMax carbon basket (18,651 faces) left 3.7 GB resident; trimmed, 0.57 GB (#45)."""
    global TRIMS
    TRIMS += 1
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except (OSError, AttributeError): pass


def _serve(fd):
    import importlib
    for p in reversed([p for p in os.environ.pop("LITEPOOL_PATH", "").split(os.pathsep) if p]): sys.path.insert(0, p)
    conn = Connection(fd)
    mods = {}
    while True:
        try: msg = conn.recv()
        except (EOFError, OSError): break
        if msg is None: break
        tid, module, fn, args = msg
        try:
            if module not in mods: mods[module] = importlib.import_module(module)
            res = ("ok", getattr(mods[module], fn)(*args))
        except Exception as e:
            res = ("stale" if type(e).__name__ == "Stale" else "err", str(e))
        try: pickle.dumps(res)
        except Exception as e: res = ("err", f"result not picklable: {e}")
        trim()
        conn.send((tid, res))


if os.environ.get("LITEPOOL_FD"):
    _fd = int(os.environ.pop("LITEPOOL_FD"))       # popped: a second import of this file must not serve again
    try: _serve(_fd)
    finally:
        sys.stdout.flush(); sys.stderr.flush(); os._exit(0)
