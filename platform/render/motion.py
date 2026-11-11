"""Motion frames for the real renderer (vt350#135 AC4): the plain-python glue between a timeline's frames
(platform/freecad/timeline.py), the mesh export (export_meshes.py with VT350_GROUPS) and the Blender frame render
(render.py --frames).

The meshes are exported ONCE at the model pose. A moving group's parts go in buckets of their own ("<group>__<key>"),
so each is one Blender object that a frame moves by its group's translation; nothing is re-exported per frame.

Stdlib only: FreeCAD, Blender and the tests all import it. Generic: no printer's names or numbers.
"""
import os

SEP = "__"


class Assign:
    """Which bucket an exported part goes in, from a groups file (cad/motion/play.py's, also the FreeCAD player's):
    {"groups": {group: [Name]}, "clip": {Name: [xmin, ymin, zmin, xmax, ymax, zmax]}, "hide": [Name]}.
    None: no groups, every part keeps its bucket (a still render)."""

    def __init__(self, data):
        data = data or {}
        self.group, seen = {}, {}
        for g, names in data.get("groups", {}).items():
            for n in names:
                if n in seen and seen[n] != g:
                    raise ValueError(f"object {n} is in two groups: {seen[n]} and {g}")
                seen[n] = g
        self.group = seen
        self.hide = set(data.get("hide", []))
        moving = sorted(self.hide & set(self.group))
        if moving:
            raise ValueError(f"hide: {', '.join(moving)} moves; hide only parts that stay put")
        self._clip = dict(data.get("clip", {}))

    def bucket(self, name, key):
        """-> (the bucket key, the group or None)."""
        g = self.group.get(name)
        return (key, None) if g is None else (f"{g}{SEP}{key}", g)

    def hidden(self, name):
        return name in self.hide

    def clip(self, name):
        return self._clip.get(name)


def frames_file(frames, fps, every=1):
    """timeline.frames() -> what the Blender job reads: {"fps", "frames": [{i, t, seq, pos, carried, groups}]}. Every
    `every`-th frame, and always the last one (the end pose). fps is the rate of the frames kept."""
    if not frames:
        raise ValueError("no frames")
    every = max(1, int(every))
    idx = list(range(0, len(frames), every))
    if idx[-1] != len(frames) - 1:
        idx.append(len(frames) - 1)
    keep = ("t", "seq", "pos", "carried", "groups")
    return {"fps": fps / every, "frames": [dict({"i": i}, **{k: frames[i][k] for k in keep if k in frames[i]})
                                           for i in idx]}


def offsets(frame, buckets):
    """A frame's translation (mm) for each bucket: its group's, or (0, 0, 0) for a static bucket."""
    out = {}
    for key, b in buckets.items():
        g = b.get("group")
        if g is None:
            out[key] = (0, 0, 0)
        elif g in frame["groups"]:
            out[key] = tuple(frame["groups"][g])
        else:
            raise ValueError(f"bucket {key} moves with group {g}, which the frame doesn't move")
    return out


def check_scene(ff, scene):
    """Every group the frames move has a bucket in the export (else it would never be drawn moving)."""
    have = {b.get("group") for b in scene["buckets"].values()}
    moved = sorted({g for f in ff["frames"] for g in f["groups"]})
    missing = [g for g in moved if g not in have]
    if missing:
        raise ValueError(f"the export has no bucket for group {', '.join(missing)} (export with VT350_GROUPS)")
    for f in ff["frames"][:1]:
        offsets(f, scene["buckets"])


def frame_name(i):
    return f"frame-{i:05d}.png"


def missing(ff, out):
    """The frame indices not yet rendered in out (a resumed run renders only these)."""
    return [f["i"] for f in ff["frames"] if not os.path.exists(os.path.join(out, frame_name(f["i"])))]


def encode_cmd(frames_dir, ff, out, crf=23):
    """-> (the ffmpeg command, the concat listing it reads on stdin): the frames in order, each held 1/fps s."""
    gone = [frame_name(i) for i in missing(ff, frames_dir)]
    if gone:
        raise ValueError(f"{len(gone)} frames not rendered in {frames_dir}: {', '.join(gone[:5])}")
    dur = 1 / ff["fps"]
    files = [os.path.join(frames_dir, frame_name(f["i"])) for f in ff["frames"]]
    listing = "".join(f"file '{p}'\nduration {dur}\n" for p in files) + f"file '{files[-1]}'\n"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(crf), "-r", f"{ff['fps']:g}",
           "-movflags", "+faststart", out]
    return cmd, listing
