# Squiggly Purge (vendored, unchanged)

Copied **unchanged** from [mjonuschat/voron-mods](https://github.com/mjonuschat/voron-mods) at commit
[`4ee68e7`](https://github.com/mjonuschat/voron-mods/tree/4ee68e7ff3e465c2e9a741417447388164b963ae/Squiggly%20Purge),
the purge line the owner runs on the Neptune (2026-11-24: "we will use the same purge cfg"). The Neptune runs an older
version of the same macro (`dvystrcil/neptune-4pro-klipper-backup`, `printer_data/config/squiggly_purge.cfg`); the
owner chose the current upstream, pinned. Called bare (`SQUIGGLY_PURGE`), it behaves the same: a 100 mm purge as a
wavy line, 10 periods of 5 mm along X with a 5 mm amplitude, from nozzle X 5, Y 3.5, moved next to the first layer
when `[exclude_object]` knows the print's objects.

**Licence:** **GPL-3.0** (the upstream repository's `LICENSE`, copied here unchanged).

| File here | Upstream path at the pinned commit | git blob |
|---|---|---|
| `squiggly_purge.cfg` | [`Squiggly Purge/Macro/squiggly_purge.cfg`](https://github.com/mjonuschat/voron-mods/blob/4ee68e7ff3e465c2e9a741417447388164b963ae/Squiggly%20Purge/Macro/squiggly_purge.cfg) | `b13ea744` |

`../test_purge.py` checks the blob id. Don't edit the file; the VT350's side is in `../printer.cfg` (the include and
`[exclude_object]`) and `../t0.cfg` / `../t1.cfg` (`max_extrude_cross_section`).

Notes for the VT350:
- The macro reads `filament_diameter` and `max_extrude_cross_section` from `[extruder]` (T0) for every tool. Both
  tools set the same values.
- `max_extrude_cross_section: 5` is the Neptune's value. Without it the macro falls back to Klipper's default,
  4 × nozzle², 0.64 mm² at 0.4, and shortens the purge to fit.
- It runs last in the start of print, after the bed mesh (`beacon.cfg`: the order).
