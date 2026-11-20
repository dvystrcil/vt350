#!/usr/bin/env python3
"""A simulated MCU board whose heaters heat (vt350#224): Kalico's scripts/avrsim.py, plus a thermal model.

    heatsim.py --heaters <heaters.json> -m atmega644p -s 20000000 -b 250000 -p <pty> <firmware.elf>

The options after --heaters are avrsim.py's, and the board is set up as avrsim.py sets it up (its serial classes are
imported from Kalico's scripts/). Without a heater model, a thermistor's ADC pin floats: simulavr reads it at 0.55 of
Vcc, a steady 124.3 C for a 104GT-2 on a 2.2k pull-up, and Kalico's verify_heater shuts down ("not heating at
expected rate") the first time a heater is given a target.

For each heater in heaters.json (written by prepare.py from the printer's config), this follows the heater pin's
output on the simulated board, feeds its duty to a first-order thermal model (ThermalModel: heating toward ambient +
duty * rise, with time constant tau), and drives the sensor's ADC pin with the voltage the thermistor would give at
that temperature (Kalico's own Thermistor.calc_adc, so the reading round-trips exactly). The model runs in wall-clock
time, as verify_heater does: simulavr runs far below real time, and a model in simulated time would heat too slowly
for verify_heater's checks.

heaters.json: [{"name", "heater_pin": "C3", "inverted": false, "sensor_pin": "A0", "pullup": 4700, "inline": 0,
"thermistor": {"t1", "r1", "t2", "r2", "t3", "r3"} or {"t1", "r1", "beta"}, "rise", "tau"}], pins as simulavr names
them (port letter + bit). The model and duty meter are plain python (test_heatsim.py); main() needs pysimulavr and
Kalico (the virtual-printer image).
"""
import json
import math
import optparse
import os
import sys
import time

KALICO = "/opt/klipper"
AMBIENT = 25.0          # C, where every heater starts and cools to
VCC = 5.0               # simulavr's supply and ADC reference (avrdevice.cpp: v_supply(5.0); Klipper's AVR ADC uses AVcc)
STEP_NS = 10 ** 7       # the model's update interval, in simulated time (10 ms; about 0.1 s of wall clock)
SIMULAVR_FREQ = 10 ** 9  # simulavr's clock: ns


class ThermalModel:
    """First-order heating: dT/dt = (ambient + duty * rise - T) / tau. Full power settles at ambient + rise."""

    def __init__(self, rise, tau, ambient=AMBIENT):
        self.rise, self.tau, self.ambient = float(rise), float(tau), float(ambient)
        self.temp = self.ambient

    def step(self, dt, duty):
        """Advance dt seconds at a constant duty (0..1); exact for any dt, so a stalled update can't overshoot."""
        duty = min(1.0, max(0.0, duty))
        settle = self.ambient + duty * self.rise
        self.temp = settle + (self.temp - settle) * math.exp(-max(0.0, dt) / self.tau)
        return self.temp


class DutyMeter:
    """The fraction of time a pin was on, from its state changes (times in any one unit, e.g. simulavr's ns)."""

    def __init__(self, start=0):
        self.on = False
        self.since = start       # the last change or take
        self.window = start      # the last take
        self.on_time = 0

    def change(self, now, on):
        if self.on:
            self.on_time += now - self.since
        self.on, self.since = bool(on), now

    def take(self, now):
        """The on fraction since the last take (the current state if no time passed); starts a new window."""
        self.change(now, self.on)
        span = now - self.window
        duty = self.on_time / span if span > 0 else float(self.on)
        self.on_time, self.window = 0, now
        return duty


# Model parameters per heater kind. Rise is how far full power settles above ambient; tau sets the pace. A hotend
# reaches 200 C in about 30 s at full power, a bed 60 C in about 30 s: quicker than most real ones, slow enough for
# Kalico's PID to settle and for verify_heater (2 C per 20 s, or 60 s for a bed) to pass with a wide margin.
KINDS = {"bed": {"rise": 120.0, "tau": 90.0}, "hotend": {"rise": 350.0, "tau": 40.0}}


def kind_of(section):
    return "bed" if section.split()[0].lower() == "heater_bed" else "hotend"


def pin_on(state, inverted, high, low):
    """Whether a heater pin in simulavr state `state` drives its heater: high (or low if inverted); else off."""
    if state == high:
        return not inverted
    if state == low:
        return inverted
    return False


def _thermistor(spec):
    sys.path.insert(0, f"{KALICO}/klippy")
    from extras.thermistor import Thermistor  # Kalico's, so a reading converts back to exactly the model's temp
    t = Thermistor(float(spec["pullup"]), float(spec.get("inline", 0.0)))
    p = spec["thermistor"]
    if "beta" in p:
        t.setup_coefficients_beta(p["t1"], p["r1"], p["beta"])
    else:
        t.setup_coefficients(p["t1"], p["r1"], p["t2"], p["r2"], p["t3"], p["r3"], name=spec["name"])
    return t


def main(argv):
    if len(argv) < 2 or argv[0] != "--heaters":
        print("usage: heatsim.py --heaters <heaters.json> <avrsim.py options> <firmware.elf>")
        return 2
    with open(argv[1]) as f:
        heaters = json.load(f)
    import pysimulavr
    sys.path.insert(0, f"{KALICO}/scripts")
    import avrsim

    class HeaterPin(pysimulavr.Pin):
        """On the heater pin's net: told each change of the board's output."""

        def __init__(self, sc, meter, inverted):
            pysimulavr.Pin.__init__(self)
            self.sc, self.meter, self.inverted = sc, meter, inverted

        def SetInState(self, pin):
            pysimulavr.Pin.SetInState(self, pin)
            self.meter.change(self.sc.GetCurrentTime(), pin_on(pin.outState, self.inverted, pin.HIGH, pin.LOW))

    class Heaters(pysimulavr.PySimulationMember):
        """Every STEP_NS of simulated time: each heater's duty since the last step, its model, its sensor pin."""

        def __init__(self, sc, items):
            pysimulavr.PySimulationMember.__init__(self)
            self.sc, self.items, self.wall = sc, items, time.monotonic()
            sc.Add(self)

        def DoStep(self, trueHwStep):
            now, wall = self.sc.GetCurrentTime(), time.monotonic()
            dt, self.wall = wall - self.wall, wall
            for meter, model, therm, sensor in self.items:
                model.step(dt, meter.take(now))
                sensor.SetAnalogValue(therm.calc_adc(model.temp) * VCC)
            return STEP_NS

    # avrsim.main()'s set-up, with the heaters added before the run loop
    opts = optparse.OptionParser("heatsim.py --heaters FILE [avrsim options] <program.elf>")
    for flag, long, typ, dest, default in (("-m", "--machine", "string", "machine", "atmega644"),
                                           ("-s", "--speed", "int", "speed", 16000000),
                                           ("-r", "--rate", "float", "pacing_rate", 0.0),
                                           ("-b", "--baud", "int", "baud", 250000),
                                           ("-p", "--port", "string", "port", "/tmp/pseudoserial")):
        opts.add_option(flag, long, type=typ, dest=dest, default=default)
    options, args = opts.parse_args(argv[2:])
    if len(args) != 1:
        opts.error("Incorrect number of arguments")
    sc = pysimulavr.SystemClock.Instance()
    dev = pysimulavr.AvrFactory.instance().makeDevice(options.machine)
    dev.Load(args[0])
    dev.SetClockFreq(SIMULAVR_FREQ // options.speed)
    sc.Add(dev)
    pysimulavr.cvar.sysConHandler.SetUseExit(False)
    keep = []                     # nets and pins live as long as the simulation
    if options.pacing_rate:
        keep.append(avrsim.Pacing(options.pacing_rate))
    io = avrsim.TerminalIO()
    rxpin = avrsim.SerialRxPin(options.baud, io)
    keep.append(_net(pysimulavr, rxpin, dev.GetPin("D1")))
    txpin = avrsim.SerialTxPin(options.baud, io)
    keep.append(_net(pysimulavr, dev.GetPin("D0"), txpin))
    items = []
    for h in heaters:
        meter = DutyMeter(sc.GetCurrentTime())
        hpin = HeaterPin(sc, meter, bool(h.get("inverted")))
        sensor = pysimulavr.Pin()
        model = ThermalModel(h["rise"], h["tau"])
        therm = _thermistor(h)
        sensor.SetAnalogValue(therm.calc_adc(model.temp) * VCC)
        keep += [hpin, sensor, _net(pysimulavr, dev.GetPin(h["heater_pin"]), hpin),
                 _net(pysimulavr, sensor, dev.GetPin(h["sensor_pin"]))]
        items.append((meter, model, therm, sensor))
        print(f"heatsim: {h['name']}: heater {h['heater_pin']}{' (inverted)' if h.get('inverted') else ''}, "
              f"sensor {h['sensor_pin']}, rise {h['rise']} C, tau {h['tau']} s")
    if items:
        keep.append(Heaters(sc, items))
    print(f"Starting AVR simulation: machine={options.machine} speed={options.speed}\n"
          f"Serial: port={options.port} baud={options.baud}", flush=True)
    fd = avrsim.create_pty(options.port)
    try:
        io.run(fd)
        sc.RunTimeRange(0x7FFF0000FFFF0000)
    finally:
        os.unlink(options.port)
    return 0


def _net(pysimulavr, *pins):
    net = pysimulavr.Net()
    for p in pins:
        net.Add(p)
    return net


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
