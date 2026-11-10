"""FreeCAD GUI player for a kalisim move timeline: watch the planned moves play out on the model (vt350#135 AC3).

    MOTION_MODEL=model.FCStd MOTION_GROUPS=groups.json MOTION_TIMELINE=timeline.jsonl MOTION_RIG=rig.json \\
        freecad platform/freecad/player_gui.FCMacro

A printer's launcher sets these (the VT350's is cad/motion/play.py). The environment:
    MOTION_MODEL     the model (.FCStd). The player opens a PRIVATE COPY in a temp dir, so nothing it or a stray
                     File > Save does can change the model; the copy is removed when the player closes
    MOTION_GROUPS    JSON {"groups": {group: [object Name, ...]}, "clip": {Name: [xmin, ymin, zmin, xmax, ymax, zmax]}}:
                     the leaf objects each moving group translates. Every group the rig moves must be there, and no
                     object may be in two groups. "clip" (optional): objects that don't move rigidly as a whole (a
                     belt loop, whose side runs change length) are shown cut down to a global box at the model pose;
                     the rest is hidden while the player is open
    MOTION_TIMELINE  the kalisim timeline (JSONL);  MOTION_RIG  the rig file (JSON). timeline.py turns them into frames
    MOTION_FPS       frames per second of timeline time (default 30);  MOTION_SPEED  the starting speed factor (1)
    MOTION_CARRIED   the head on the carriage at the start (default none)
    MOTION_COPY_DIR  where the private copy goes (default: the system temp dir; a model of 180 MB can exceed /tmp's quota)
    MOTION_AUTOTEST  a JSON path: play every frame unattended, stop, check every Placement is back, write the result
                     there and quit FreeCAD (for testing the GUI under xvfb)

The panel: Play/Pause, Step back/forward (one frame), Stop (restore every Placement, back to the first frame), a speed
factor, and a slider to scrub. Closing the panel restores, closes the copy and removes it. It never saves.

How a frame moves the model: each group's translation (model coordinates, from the saved pose) is added to every
object's SAVED Placement, turned into the object's parent frame first, so an object inside a rotated App::Part still
moves by the global translation. Moving an object that a boolean or compound uses doesn't change that result until a
recompute, so don't recompute while playing (Stop puts everything back first).

Generic: no printer's labels or numbers. The plain-python parts (Clock, Mover, check_groups, resolve, private_copy,
config, load) import without FreeCAD; the FreeCAD and Qt parts import it inside.
"""
import bisect
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    os.path.join(os.environ.get("VT350_REPO", "/home/dan/Code/vt350"), "platform/freecad")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import timeline  # noqa: E402

TICK_MS = 33                     # the GUI timer; the frame shown is the one at the elapsed time x speed
SPEEDS = (0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 10.0)


class Clock:
    """Which frame to show: playback time runs at `speed` x real time while playing."""

    def __init__(self, frames):
        if not frames:
            raise ValueError("no frames to play")
        self.ts = [f["t"] for f in frames]
        self.index, self.time, self.playing, self.speed = 0, self.ts[0], False, 1.0

    @property
    def at_end(self):
        return self.index == len(self.ts) - 1

    def set_speed(self, s):
        if not s > 0:
            raise ValueError(f"speed must be above 0, not {s}")
        self.speed = float(s)

    def play(self):
        if self.at_end:
            self.seek(0)
        self.playing = True

    def pause(self):
        self.playing = False

    def advance(self, dt):
        """Real seconds dt have passed: the frame to show now. Stops playing at the last frame."""
        if self.playing:
            self.time += dt * self.speed
            self.index = max(0, bisect.bisect_right(self.ts, self.time + 1e-9) - 1)
            if self.at_end:
                self.playing = False
        return self.index

    def seek(self, i):
        self.index = min(max(int(i), 0), len(self.ts) - 1)
        self.time = self.ts[self.index]
        return self.index

    def step(self, n):
        self.pause()
        return self.seek(self.index + n)

    def rewind(self):
        self.pause()
        return self.seek(0)


class Mover:
    """Applies frames to objects and puts them back. backend: save(obj) -> saved; move(obj, saved, d); restore(obj,
    saved). Every move is from the saved state, so frames never accumulate."""

    def __init__(self, objects, backend):
        self.objects, self.backend = objects, backend
        self.saved = {id(o): (o, backend.save(o)) for objs in objects.values() for o in objs}
        self.last = {}

    def apply(self, frame):
        for g, d in frame["groups"].items():
            d = tuple(d)
            if self.last.get(g) == d:
                continue
            if g not in self.objects:
                raise KeyError(f"frame moves group {g!r}, which has no objects")
            for o in self.objects[g]:
                self.backend.move(o, self.saved[id(o)][1], d)
            self.last[g] = d

    def restore(self):
        for o, s in self.saved.values():
            self.backend.restore(o, s)
        self.last = {}
        return len(self.saved)


class FreeCADBackend:
    """A saved state is (the Placement, the parent frame's rotation inverted): a global translation d becomes the
    local one R_parent^-1 d, since global = parent * local."""

    def save(self, obj):
        parent = obj.getGlobalPlacement().multiply(obj.Placement.inverse())
        return obj.Placement.copy(), parent.Rotation.inverted()

    def move(self, obj, saved, d):
        import FreeCAD
        pl, rinv = saved
        p = pl.copy()
        p.Base = pl.Base + rinv.multVec(FreeCAD.Vector(*d))
        obj.Placement = p

    def restore(self, obj, saved):
        obj.Placement = saved[0]


def check_groups(groups, frames):
    """Every group the frames move has objects, and no object is in two groups."""
    moved = sorted({g for f in frames for g in f["groups"]})
    missing = [g for g in moved if g not in groups]
    if missing:
        raise ValueError(f"the groups file has no {', '.join(missing)} (the rig moves {', '.join(moved)})")
    empty = [g for g in moved if not groups[g]]
    if empty:
        raise ValueError(f"group {', '.join(empty)} is empty")
    seen = {}
    for g, names in groups.items():
        for n in names:
            if n in seen and seen[n] != g:
                raise ValueError(f"object {n} is in two groups: {seen[n]} and {g}")
            seen[n] = g


def check_clip(clip, groups):
    """clip {Name: [xmin, ymin, zmin, xmax, ymax, zmax]}: each Name is in a group, each box has a volume."""
    names = {n for ns in groups.values() for n in ns}
    for n, box in clip.items():
        if n not in names:
            raise ValueError(f"clip: object {n} is in no group")
        if len(box) != 6 or not all(box[i] < box[i + 3] for i in range(3)):
            raise ValueError(f"clip: {n}'s box {box} isn't [xmin, ymin, zmin, xmax, ymax, zmax] with min < max")


def clip_objects(doc, objects, clip):
    """Show each clipped object cut down to its box: a new Part::Feature in the (private copy of the) document holds
    the global shape's common with the box, and takes the object's place in its group; the original is hidden and
    never moves. -> the new {group: [object]}."""
    import FreeCAD
    import Part
    out = {}
    for g, objs in objects.items():
        out[g] = []
        for o in objs:
            if o.Name not in clip:
                out[g].append(o)
                continue
            x0, y0, z0, x1, y1, z1 = clip[o.Name]
            s = o.Shape.copy(); s.Placement = o.getGlobalPlacement()
            c = doc.addObject("Part::Feature", o.Name + "_PlayerClip")
            c.Shape = s.common(Part.makeBox(x1 - x0, y1 - y0, z1 - z0, FreeCAD.Vector(x0, y0, z0)))
            c.Label = o.Label + " (player: clipped)"
            if getattr(o, "ViewObject", None) is not None and getattr(c, "ViewObject", None) is not None:
                for prop in ("ShapeAppearance", "DiffuseColor", "ShapeColor", "LineColor"):
                    if hasattr(o.ViewObject, prop) and hasattr(c.ViewObject, prop):
                        try:
                            setattr(c.ViewObject, prop, getattr(o.ViewObject, prop))
                        except Exception:
                            pass
                o.ViewObject.Visibility = False
            out[g].append(c)
    return out


def resolve(doc, groups):
    """{group: [Name]} -> {group: [object]}; a Name the document doesn't have is refused."""
    out = {}
    for g, names in groups.items():
        objs = [doc.getObject(n) for n in names]
        bad = [n for n, o in zip(names, objs) if o is None]
        if bad:
            raise ValueError(f"group {g}: the model has no object {', '.join(bad[:5])}"
                             + (f" (+{len(bad) - 5} more)" if len(bad) > 5 else ""))
        out[g] = objs
    return out


def private_copy(model, parent=None):
    """Copy the model into a new temp dir under parent (default: the system temp dir). -> (the copy's path,
    cleanup()); cleanup removes the dir."""
    if not os.path.isfile(model):
        raise FileNotFoundError(model)
    if parent:
        os.makedirs(parent, exist_ok=True)
    d = tempfile.mkdtemp(prefix="motion-player-", dir=parent)
    path = os.path.join(d, os.path.basename(model))
    try:
        shutil.copyfile(model, path)
    except BaseException:
        shutil.rmtree(d, True)
        raise
    return path, lambda: shutil.rmtree(d, True)


def config(env):
    need = ("MOTION_MODEL", "MOTION_GROUPS", "MOTION_TIMELINE", "MOTION_RIG")
    missing = [k for k in need if not env.get(k)]
    if missing:
        raise ValueError(f"set {', '.join(missing)} (see platform/freecad/player.py)")
    return {"model": env["MOTION_MODEL"], "groups": env["MOTION_GROUPS"], "timeline": env["MOTION_TIMELINE"],
            "rig": env["MOTION_RIG"], "fps": float(env.get("MOTION_FPS") or 30), "speed": float(env.get("MOTION_SPEED") or 1),
            "carried": env.get("MOTION_CARRIED") or None, "autotest": env.get("MOTION_AUTOTEST") or None,
            "copy_dir": env.get("MOTION_COPY_DIR") or None}


def load(cfg):
    """-> (frames, {group: [Name]}, clip {Name: box}), checked against each other."""
    with open(cfg["rig"]) as f:
        rig = json.load(f)
    with open(cfg["timeline"]) as f:
        records = [json.loads(line) for line in f if line.strip()]
    frames = timeline.frames(rig, records, cfg["fps"], cfg["carried"])
    with open(cfg["groups"]) as f:
        data = json.load(f)
    groups, clip = data["groups"], data.get("clip", {})
    check_groups(groups, frames)
    check_clip(clip, groups)
    return frames, groups, clip


# ------------------------------------------------------------------------------------------------ the GUI
def describe(frame, i, n, speed):
    p = frame["pos"]
    return (f"frame {i + 1}/{n}  t {frame['t']:.2f} s  seq {frame['seq']}  X {p[0]:.2f} Y {p[1]:.2f} Z {p[2]:.2f}  "
            f"carried: {frame['carried'] or 'none'}  speed x{speed:g}")


class Panel:
    """The dock widget. Holds the model copy, the mover and the clock; everything else is Qt wiring."""

    def __init__(self, cfg):
        import time
        import FreeCAD
        import FreeCADGui
        from PySide import QtCore, QtWidgets
        self.cfg, self.time = cfg, time.monotonic
        self.frames, groups, clip = load(cfg)
        self.copy, self.cleanup = private_copy(cfg["model"], cfg["copy_dir"])
        try:
            self.doc = FreeCAD.openDocument(self.copy)
            self.doc.Label = self.doc.Label + " (player copy: read-only, never saved)"
            objects = clip_objects(self.doc, resolve(self.doc, groups), clip)
            # every Placement as opened, before anything moves: the autotest checks Stop against this, not the
            # Mover's own record
            self.opened = {o.Name: o.Placement.copy() for objs in objects.values() for o in objs}
            self.mover = Mover(objects, FreeCADBackend())
        except BaseException:
            self.cleanup()
            raise
        self.clock = Clock(self.frames)
        self.clock.set_speed(cfg["speed"])
        self.last_tick, self.closed = None, False

        self.dock = QtWidgets.QDockWidget("Motion player")
        w = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(w)
        self.info = QtWidgets.QLabel(); self.info.setWordWrap(True); lay.addWidget(self.info)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(0, len(self.frames) - 1); lay.addWidget(self.slider)
        row = QtWidgets.QHBoxLayout(); lay.addLayout(row)
        self.b_back, self.b_play, self.b_fwd, self.b_stop = (QtWidgets.QPushButton(t) for t in ("|<", "Play", ">|", "Stop"))
        for b in (self.b_back, self.b_play, self.b_fwd, self.b_stop):
            row.addWidget(b)
        self.speed = QtWidgets.QComboBox()
        for s in sorted(set(SPEEDS) | {self.clock.speed}):
            self.speed.addItem(f"x{s:g}", s)
        self.speed.setCurrentIndex(self.speed.findData(self.clock.speed)); row.addWidget(self.speed)
        self.dock.setWidget(w)
        self.b_play.clicked.connect(self.toggle)
        self.b_back.clicked.connect(lambda: self.show(self.clock.step(-1)))
        self.b_fwd.clicked.connect(lambda: self.show(self.clock.step(1)))
        self.b_stop.clicked.connect(self.stop)
        self.speed.currentIndexChanged.connect(lambda i: self.clock.set_speed(self.speed.itemData(i)))
        self.slider.sliderMoved.connect(lambda i: self.show(self.clock.step(i - self.clock.index)))
        self.dock.visibilityChanged.connect(lambda v: None if v or self.closed else self.close())
        self.timer = QtCore.QTimer(); self.timer.timeout.connect(self.tick)
        FreeCADGui.getMainWindow().addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dock)
        FreeCADGui.SendMsgToActiveView("ViewFit")
        self.show(0)

    def show(self, i):
        self.mover.apply(self.frames[i])
        self.slider.blockSignals(True); self.slider.setValue(i); self.slider.blockSignals(False)
        self.info.setText(describe(self.frames[i], i, len(self.frames), self.clock.speed))
        self.b_play.setText("Pause" if self.clock.playing else "Play")

    def toggle(self):
        if self.clock.playing:
            self.clock.pause(); self.timer.stop()
        else:
            self.clock.play(); self.last_tick = self.time(); self.timer.start(TICK_MS)
        self.show(self.clock.index)

    def tick(self):
        now = self.time()
        i = self.clock.advance(now - self.last_tick)
        self.last_tick = now
        if not self.clock.playing:
            self.timer.stop()
        self.show(i)

    def stop(self):
        """Pause, put every Placement back, show the first frame's position in the panel only."""
        self.timer.stop()
        self.clock.rewind()
        n = self.mover.restore()
        self.slider.setValue(0)
        self.info.setText(f"stopped: {n} Placements restored. " + describe(self.frames[0], 0, len(self.frames), self.clock.speed))
        self.b_play.setText("Play")
        return n

    def close(self):
        """Restore, close the copy without saving, remove it."""
        import FreeCAD
        if self.closed:
            return
        self.closed = True
        try:
            self.stop()
        finally:
            try:
                FreeCAD.closeDocument(self.doc.Name)
            finally:
                self.cleanup()
                self.dock.deleteLater()


def autotest(panel, out):
    """Play every frame unattended (stepping, so every frame is applied), stop, and check every Placement is back."""
    import FreeCAD
    import hashlib
    def sha(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()
    before = panel.opened                                      # the panel already shows frame 0, so not "now"
    model_sha = sha(panel.cfg["model"])
    moved_max = 0.0
    for i in range(len(panel.frames)):
        panel.show(panel.clock.seek(i))
        if i == len(panel.frames) // 2:
            moved_max = max((o.Placement.Base - before[o.Name].Base).Length
                            for objs in panel.mover.objects.values() for o in objs)
    panel.clock.seek(0); panel.clock.play()                    # and the timer path, at speed
    panel.clock.set_speed(1000.0); panel.last_tick = panel.time() - 1.0
    panel.tick()
    played_to_end = panel.clock.at_end
    restored = panel.stop()
    bad = [n for objs in panel.mover.objects.values() for o in objs for n in [o.Name]
           if not o.Placement.isSame(before[n], 1e-9)]
    res = {"frames": len(panel.frames), "objects": len(before), "restored": restored, "not_restored": bad,
           "moved_max_mm_mid": round(moved_max, 3), "played_to_end": played_to_end,
           "model_unchanged": sha(panel.cfg["model"]) == model_sha, "copy": panel.copy}
    panel.close()
    res["copy_removed"] = not os.path.exists(os.path.dirname(res["copy"]))
    res["documents_open"] = sorted(FreeCAD.listDocuments())
    with open(out, "w") as f:
        json.dump(res, f, indent=1)


def _keep(panel):
    import FreeCADGui
    FreeCADGui.motion_player = panel           # keep a reference: Qt slots die with the Python object


def gui_main(env=os.environ, panel=None, test=None, keep=_keep, exit=os._exit):
    """Open the panel. Under MOTION_AUTOTEST run the test, write {"fatal": traceback} on ANY failure (opening the panel
    included) and quit, so an unattended run can never hang."""
    cfg = config(env)
    panel, test = panel or Panel, test or autotest
    if not cfg["autotest"]:
        p = panel(cfg)
        keep(p)
        return p
    try:
        p = panel(cfg)
        keep(p)
        test(p, cfg["autotest"])
    except BaseException:
        import traceback
        with open(cfg["autotest"], "w") as f:
            json.dump({"fatal": traceback.format_exc()}, f)
    finally:
        exit(0)
