"""A GLB (binary glTF) -> the same glTF as one JSON file, its binary buffer embedded as a base64 data URI (vt350#220).

For hosts that serve .json but not .glb. three.js's GLTFLoader.parse() reads either. Stdlib only.

    python3 platform/viewer/glbjson.py in.glb out.gltf.json
"""
import base64, json, struct, sys

MAGIC, JSON_CHUNK, BIN_CHUNK = 0x46546C67, 0x4E4F534A, 0x004E4942


def convert(glb):
    """bytes of a GLB -> the glTF dict with buffer 0 embedded."""
    magic, version, length = struct.unpack_from("<III", glb, 0)
    if magic != MAGIC or version != 2:
        raise ValueError("not a glTF 2.0 GLB")
    i, doc, binary = 12, None, b""
    while i < length:
        n, kind = struct.unpack_from("<II", glb, i)
        chunk = glb[i + 8:i + 8 + n]
        if kind == JSON_CHUNK:
            doc = json.loads(chunk.decode("utf-8"))
        elif kind == BIN_CHUNK:
            binary = chunk
        i += 8 + n
    if doc is None:
        raise ValueError("GLB has no JSON chunk")
    if doc.get("buffers"):
        b = doc["buffers"][0]
        if "uri" in b:
            raise ValueError("buffer 0 already has a uri")
        b["uri"] = "data:application/octet-stream;base64," + base64.b64encode(binary[:b["byteLength"]]).decode("ascii")
    return doc


def write(glb_fn, json_fn):
    doc = convert(open(glb_fn, "rb").read())
    with open(json_fn, "w", encoding="utf-8") as f:
        json.dump(doc, f, separators=(",", ":"))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    write(sys.argv[1], sys.argv[2])
