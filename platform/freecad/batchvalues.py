# Where a platform script's setting comes from, so another person edits a values file instead of the code
# (gpu-batch-docker docs/using-the-batch-tools.md, gap 4). Plain python3; works inside freecadcmd too.
#
#   1. the script's own env var, if set at all (even empty): what os.environ.get(VAR, default) did before
#   2. the "platform" section of the JSON file named by GPU_BATCH_VALUES (the same file whose "print_guard"
#      section the gpu-batch guard reads)
#   3. the script's built-in default: today's value, so a laptop with no values file behaves exactly as before
#
# A bad file is an error, never "no file", as with the guard: a missing or non-JSON file, or a key in "platform"
# this module doesn't know (a typo would otherwise fall back to the default without a word).
import json, os

# one entry per setting a script has moved here; add the key when the next script moves
KNOWN = {
    "freecad_appimage",       # the FreeCAD AppImage (or AppRun) whose `freecadcmd` the checks run; env FREECAD_APPIMAGE
}


class ValuesError(Exception):
    pass


def setting(key, env, default, environ=None):
    environ = os.environ if environ is None else environ
    if env in environ:
        return environ[env]
    path = environ.get("GPU_BATCH_VALUES")
    if path:
        section = platform_section(path)
        if key in section:
            return section[key]
    return default


def platform_section(path):
    try:
        with open(path) as f:
            doc = json.load(f)
    except (OSError, ValueError) as e:
        raise ValuesError(f"values file {path} (GPU_BATCH_VALUES): {e}") from e
    section = doc.get("platform", {})
    unknown = sorted(set(section) - KNOWN)
    if unknown:
        raise ValuesError(f"values file {path} (GPU_BATCH_VALUES): unknown platform key(s) {', '.join(unknown)}; "
                          f"known: {', '.join(sorted(KNOWN))}")
    return section
