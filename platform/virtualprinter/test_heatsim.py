#!/usr/bin/env python3
"""heatsim.py's thermal model and duty meter, without Docker or simulavr (vt350#224).

    python3 platform/virtualprinter/test_heatsim.py
"""
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import heatsim  # noqa: E402


def time_to(model, temp, duty=1.0, dt=0.1, limit=3600):
    t = 0.0
    while model.temp < temp:
        model.step(dt, duty)
        t += dt
        if t > limit:
            return None
    return t


class Model(unittest.TestCase):
    def test_starts_at_ambient_and_full_power_settles_at_ambient_plus_rise(self):
        m = heatsim.ThermalModel(rise=350, tau=40)
        self.assertEqual(m.temp, heatsim.AMBIENT)
        m.step(10000, 1.0)
        self.assertAlmostEqual(m.temp, heatsim.AMBIENT + 350, places=6)
        m.step(10000, 0.5)
        self.assertAlmostEqual(m.temp, heatsim.AMBIENT + 175, places=6)

    def test_step_is_exact_for_any_dt(self):
        a, b = heatsim.ThermalModel(350, 40), heatsim.ThermalModel(350, 40)
        a.step(30, 1.0)
        for _ in range(300):
            b.step(0.1, 1.0)
        self.assertAlmostEqual(a.temp, b.temp, places=6)
        self.assertAlmostEqual(a.temp, 25 + 350 * (1 - math.exp(-30 / 40)), places=6)

    def test_cools_to_ambient_when_off(self):
        m = heatsim.ThermalModel(350, 40)
        m.temp = 200.0
        m.step(40, 0.0)
        self.assertAlmostEqual(m.temp, 25 + 175 * math.exp(-1), places=6)
        m.step(1000, 0.0)
        self.assertAlmostEqual(m.temp, 25.0, places=3)

    def test_duty_is_clamped_and_negative_dt_ignored(self):
        m = heatsim.ThermalModel(100, 10)
        m.step(-5, 1.0)
        self.assertEqual(m.temp, 25.0)
        m.step(1000, 7.0)
        self.assertAlmostEqual(m.temp, 125.0, places=6)

    def test_kinds_reach_their_targets_quickly_enough_for_verify_heater(self):
        # verify_heater wants 2 C of gain within check_gain_time (20 s, a bed 60 s) at full power; the defaults
        # reach typical targets in well under a minute, and full power settles above max_temp-ish targets
        hot = heatsim.ThermalModel(**heatsim.KINDS["hotend"])
        self.assertLess(time_to(hot, 200), 40)
        hot = heatsim.ThermalModel(**heatsim.KINDS["hotend"])
        hot.step(20, 1.0)
        self.assertGreater(hot.temp - 25, 2 * 10)
        self.assertLess(time_to(heatsim.ThermalModel(**heatsim.KINDS["bed"]), 60), 60)
        self.assertGreater(heatsim.AMBIENT + heatsim.KINDS["hotend"]["rise"], 300)
        self.assertGreater(heatsim.AMBIENT + heatsim.KINDS["bed"]["rise"], 110)

    def test_kind_of(self):
        self.assertEqual(heatsim.kind_of("heater_bed"), "bed")
        self.assertEqual(heatsim.kind_of("extruder1"), "hotend")
        self.assertEqual(heatsim.kind_of("heater_generic chamber"), "hotend")

    def test_closed_loop_holds_target_then_cools(self):
        # a PID like Kalico's (its default extruder gains, /255), the reading every 0.3 s: it holds 200 within 3 C
        m = heatsim.ThermalModel(**heatsim.KINDS["hotend"])
        kp, ki, kd = 25.566 / 255, 1.794 / 255, 91.080 / 255
        integ, prev, duty, t = 0.0, m.temp, 0.0, 0.0
        temps = []
        while t < 180:
            m.step(0.3, duty)
            t += 0.3
            err = 200 - m.temp
            deriv = (m.temp - prev) / 0.3
            prev = m.temp
            integ = max(0.0, min(1.0 / ki, integ + err * 0.3))
            duty = max(0.0, min(0.995, kp * err + ki * integ - kd * deriv))
            temps.append((t, m.temp))
        self.assertTrue(all(abs(T - 200) < 3 for tt, T in temps if tt > 120), temps[-5:])
        self.assertLess(max(T for _, T in temps), 215)
        m.step(300, 0.0)
        self.assertLess(m.temp, 30)


class Duty(unittest.TestCase):
    def test_on_fraction_over_each_window(self):
        d = heatsim.DutyMeter(0)
        d.change(10, True)
        d.change(40, False)
        self.assertAlmostEqual(d.take(100), 0.3)
        d.change(150, True)
        self.assertAlmostEqual(d.take(200), 0.5)   # on from 150, still on at the take
        self.assertAlmostEqual(d.take(300), 1.0)
        self.assertEqual(d.take(300), 1.0)          # no time passed: the current state

    def test_repeated_same_state_counts_once(self):
        d = heatsim.DutyMeter(0)
        d.change(0, True)
        d.change(50, True)
        d.change(50, True)
        self.assertAlmostEqual(d.take(100), 1.0)

    def test_pin_on_respects_inversion_and_ignores_other_states(self):
        HIGH, LOW, TRI = "H", "L", "t"
        self.assertTrue(heatsim.pin_on(HIGH, False, HIGH, LOW))
        self.assertFalse(heatsim.pin_on(LOW, False, HIGH, LOW))
        self.assertTrue(heatsim.pin_on(LOW, True, HIGH, LOW))
        self.assertFalse(heatsim.pin_on(HIGH, True, HIGH, LOW))
        self.assertFalse(heatsim.pin_on(TRI, True, HIGH, LOW))
        self.assertFalse(heatsim.pin_on(TRI, False, HIGH, LOW))


class Cli(unittest.TestCase):
    def test_usage_without_heaters(self):
        self.assertEqual(heatsim.main([]), 2)
        self.assertEqual(heatsim.main(["-m", "atmega644p"]), 2)


if __name__ == "__main__":
    unittest.main()
