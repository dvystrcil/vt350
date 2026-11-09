# Unit tests for litepool.py (#45): worker count + the worker pool, with plain python3 workers (no FreeCAD), so they
# run in CI:   python3 cad/scripts/test_litepool.py      # "Ran N tests" + "OK"
# The FreeCAD side (litelib's checks through the pool, bit-identical to serial) is in test_litelib.py.
import os, sys, tempfile, time, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import litepool


# ---- ops the workers run (imported by name in the worker: module "test_litepool")
def op_add(a, b): return a + b
def op_sleep_then(x, s): time.sleep(s); return x
def op_pid(s): time.sleep(s); return os.getpid()
def op_fail(msg): raise ValueError(msg)
def op_stale(msg): raise litepool.Stale(msg)
def op_crash(): os._exit(3)
def op_env(k): return os.environ.get(k)
def op_trims(): return sys.modules["__main__"].TRIMS            # the worker's own count (it runs as __main__)


BIG = 10 ** 9                                   # MB: no memory cap


def cgroup(tmp, cpu_max=None, v1=None):
    """A fake cgroup root: v2 cpu.max text, or v1 (quota_us, period_us)."""
    d = tempfile.mkdtemp(dir=tmp)
    if cpu_max is not None: open(os.path.join(d, "cpu.max"), "w").write(cpu_max + "\n")
    if v1 is not None:
        os.makedirs(os.path.join(d, "cpu"))
        open(os.path.join(d, "cpu", "cpu.cfs_quota_us"), "w").write(f"{v1[0]}\n")
        open(os.path.join(d, "cpu", "cpu.cfs_period_us"), "w").write(f"{v1[1]}\n")
    return d


class Cpus(unittest.TestCase):
    def setUp(self): self.tmp = tempfile.mkdtemp(prefix="litepool-test-")

    def test_affinity_without_a_quota(self):
        self.assertEqual(litepool.available_cpus(affinity=set(range(12)), root=cgroup(self.tmp, "max 100000")), 12)
        self.assertEqual(litepool.available_cpus(affinity=set(range(5)), root=cgroup(self.tmp)), 5)   # no cgroup files

    def test_a_cgroup_v2_quota_caps_it_rounded_up(self):
        self.assertEqual(litepool.available_cpus(affinity=set(range(32)), root=cgroup(self.tmp, "400000 100000")), 4)
        self.assertEqual(litepool.available_cpus(affinity=set(range(32)), root=cgroup(self.tmp, "150000 100000")), 2)
        self.assertEqual(litepool.available_cpus(affinity=set(range(32)), root=cgroup(self.tmp, "50000 100000")), 1)

    def test_a_cgroup_v1_quota_caps_it(self):
        self.assertEqual(litepool.available_cpus(affinity=set(range(32)), root=cgroup(self.tmp, v1=(300000, 100000))), 3)
        self.assertEqual(litepool.available_cpus(affinity=set(range(32)), root=cgroup(self.tmp, v1=(-1, 100000))), 32)

    def test_affinity_below_the_quota_wins(self):
        self.assertEqual(litepool.available_cpus(affinity={0, 1}, root=cgroup(self.tmp, "800000 100000")), 2)

    def test_worker_count_pinned_by_env(self):
        self.assertEqual(litepool.worker_count(env={"VT350_WORKERS": "3"}, cpus=12, mem_mb=BIG), 3)
        self.assertEqual(litepool.worker_count(env={"VT350_WORKERS": "1"}, cpus=12, mem_mb=BIG), 1)

    def test_a_bad_pin_is_an_error_not_a_guess(self):
        for bad in ("0", "-2", "ten", ""):
            with self.assertRaises(ValueError): litepool.worker_count(env={"VT350_WORKERS": bad}, cpus=12, mem_mb=BIG)

    def test_default_leaves_two_cpus_and_is_at_least_one(self):
        self.assertEqual(litepool.worker_count(env={}, cpus=12, mem_mb=BIG), 10)
        self.assertEqual(litepool.worker_count(env={}, cpus=2, mem_mb=BIG), 1)
        self.assertEqual(litepool.worker_count(env={}, cpus=1, mem_mb=BIG), 1)

    def test_default_cpus_come_from_available_cpus_not_cpu_count(self):
        real = litepool.os.cpu_count
        litepool.os.cpu_count = lambda: 999                                  # the host count a pod would see
        try: n = litepool.worker_count(env={}, mem_mb=BIG)
        finally: litepool.os.cpu_count = real
        self.assertEqual(n, max(1, litepool.available_cpus() - 2)); self.assertNotEqual(n, 997)


class MemoryCap(unittest.TestCase):
    """#45: each worker opens its own copy of the documents, so the count is also capped by free memory."""
    def test_available_mb_reads_memavailable(self):
        f = os.path.join(tempfile.mkdtemp(), "meminfo")
        open(f, "w").write("MemTotal:       32144636 kB\nMemFree:  1 kB\nMemAvailable:   21504000 kB\n")
        self.assertEqual(litepool.available_mb(f), 21000)

    def test_a_cgroup_memory_limit_caps_it_in_a_pod(self):               # /proc/meminfo is the HOST's in a pod
        d = tempfile.mkdtemp(); f = os.path.join(d, "meminfo")
        open(f, "w").write("MemAvailable:   21504000 kB\n")
        open(os.path.join(d, "memory.max"), "w").write(f"{8 * 1024 ** 3}\n")
        open(os.path.join(d, "memory.current"), "w").write(f"{3 * 1024 ** 3}\n")
        self.assertEqual(litepool.available_mb(f, root=d), 5 * 1024)
        open(os.path.join(d, "memory.max"), "w").write("max\n")
        self.assertEqual(litepool.available_mb(f, root=d), 21000)

    def test_memory_caps_the_cpu_count(self):
        kw = dict(env={}, per_worker_mb=2000, reserve_mb=6000)
        self.assertEqual(litepool.worker_count(cpus=12, mem_mb=20000, **kw), 7)    # (20000 - 6000) // 2000
        self.assertEqual(litepool.worker_count(cpus=4, mem_mb=20000, **kw), 2)     # CPUs are the tighter limit
        self.assertEqual(litepool.worker_count(cpus=12, mem_mb=9999, **kw), 1)
        self.assertEqual(litepool.worker_count(cpus=12, mem_mb=7000, **kw), 1)     # under one worker: serial
        self.assertEqual(litepool.worker_count(cpus=12, mem_mb=3000, **kw), 1)     # under the reserve: serial

    def test_a_pin_lowers_the_count_but_never_raises_it_past_the_memory_cap(self):
        kw = dict(cpus=12, mem_mb=12000, per_worker_mb=2000, reserve_mb=6000)
        self.assertEqual(litepool.worker_count(env={"VT350_WORKERS": "10"}, **kw), 3)
        self.assertEqual(litepool.worker_count(env={"VT350_WORKERS": "2"}, **kw), 2)

    def test_budget_and_reserve_from_env(self):
        env = {"VT350_WORKER_MB": "1000", "VT350_RESERVE_MB": "2000"}
        self.assertEqual(litepool.worker_count(env=env, cpus=12, mem_mb=7000), 5)
        for bad in ({"VT350_WORKER_MB": "0"}, {"VT350_WORKER_MB": "x"}, {"VT350_RESERVE_MB": "-1"}):
            with self.assertRaises(ValueError): litepool.worker_count(env=bad, cpus=12, mem_mb=7000)

    def test_defaults_are_the_measured_budget(self):
        self.assertEqual(litepool.worker_count(env={}, cpus=12, mem_mb=litepool.RESERVE_MB + 3 * litepool.WORKER_MB), 3)

    def test_unset_memory_is_read_from_the_system(self):
        real = litepool.available_mb
        litepool.available_mb = lambda *a, **k: litepool.RESERVE_MB + 2 * litepool.WORKER_MB
        try: self.assertEqual(litepool.worker_count(env={}, cpus=12), 2)
        finally: litepool.available_mb = real


class ClashlibCount(unittest.TestCase):
    def test_clashlib_uses_the_same_worker_count(self):                 # its sweeps run in batch-lane pods too
        import clashlib
        old = os.environ.get("VT350_WORKERS")
        try:
            os.environ["VT350_WORKERS"] = "3"; self.assertEqual(clashlib.default_n(), 3)
            del os.environ["VT350_WORKERS"]; self.assertEqual(clashlib.default_n(), litepool.worker_count())
        finally:
            if old is not None: os.environ["VT350_WORKERS"] = old


class PoolTest(unittest.TestCase):
    def pool(self, n, **kw):
        p = litepool.Pool(n, cmd=[sys.executable], path=[HERE], **kw)
        self.addCleanup(p.close)
        return p

    def test_results_come_back_in_input_order(self):
        p = self.pool(3)
        tasks = [(i, 0.05 * ((7 * i) % 4)) for i in range(12)]          # uneven durations: finish out of order
        self.assertEqual(p.map("test_litepool", "op_sleep_then", tasks), [("ok", i) for i in range(12)])
        self.assertEqual(p.map("test_litepool", "op_add", [(1, 2), (3, 4)]), [("ok", 3), ("ok", 7)])

    def test_tasks_spread_over_all_workers(self):
        p = self.pool(3)
        pids = {v for _, v in p.map("test_litepool", "op_pid", [(0.2,)] * 6)}
        self.assertEqual(len(pids), 3); self.assertNotIn(os.getpid(), pids)

    def test_workers_persist_between_maps(self):
        p = self.pool(2)
        a = {v for _, v in p.map("test_litepool", "op_pid", [(0.2,)] * 4)}
        b = {v for _, v in p.map("test_litepool", "op_pid", [(0.2,)] * 4)}
        self.assertEqual(a, b)

    def test_an_exception_comes_back_as_its_message(self):
        p = self.pool(2)
        self.assertEqual(p.map("test_litepool", "op_fail", [("boom",), ("bang",)]), [("err", "boom"), ("err", "bang")])
        self.assertEqual(p.map("test_litepool", "op_add", [(1, 1)]), [("ok", 2)])        # the worker survives it

    def test_stale_is_reported_so_the_parent_can_redo_the_task(self):
        p = self.pool(2)
        self.assertEqual(p.map("test_litepool", "op_stale", [("moved",)]), [("stale", "moved")])

    def test_a_dead_worker_fails_the_map_and_does_not_hang(self):
        p = self.pool(2)
        t = time.time()
        with self.assertRaises(RuntimeError): p.map("test_litepool", "op_crash", [(), ()])
        self.assertLess(time.time() - t, 30)

    def test_a_worker_gives_freed_memory_back_after_every_task(self):  # #45: glibc keeps it otherwise
        p = self.pool(1)
        r = p.map("test_litepool", "op_add", [(1, 1)] * 3) + p.map("test_litepool", "op_trims", [()])
        self.assertEqual(r[-1], ("ok", 3))                                  # one trim after each of the 3 tasks

    def test_workers_do_not_inherit_the_pool_fd_variable(self):
        p = self.pool(1)
        self.assertEqual(p.map("test_litepool", "op_env", [("LITEPOOL_FD",)]), [("ok", None)])

    def test_close_ends_every_worker(self):
        p = litepool.Pool(2, cmd=[sys.executable], path=[HERE])
        p.map("test_litepool", "op_add", [(1, 1), (2, 2)])
        procs = list(p.procs); p.close()
        self.assertTrue(all(pr.poll() is not None for pr in procs))
        p.close()                                                           # twice is fine


if __name__ == "__main__":
    unittest.main(verbosity=2)
