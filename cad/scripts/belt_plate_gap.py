# #61: belts vs the parked MadMax plates at each head's dock pickup (parked and slid 6 mm to the keyslots' large
# opening), lite-25 vs lite-26. Headless, read-only. The belt part inside the XY joints' Y band moves with the gantry
# (as sweep_toolhead.py); gantry dY at pickup = dock carriage copy - gantry carriage (sweep_toolhead.log).
#   $APP freecadcmd /home/dan/Code/vt350/cad/scripts/belt_plate_gap.py   -> cad/data/logs/belt_plate_gap.log
import FreeCAD, Part, os, traceback
V=FreeCAD.Vector; out=open(os.environ.get("OUT", "/home/dan/Code/vt350/cad/data/logs/belt_plate_gap.log"),"w",buffering=1)
try:
  for f, ty in (("vt350-lite-25", -262.50), ("vt350-lite-26", -257.725)):
    d=FreeCAD.openDocument(f"/home/dan/Documents/VT350/{f}.FCStd")
    def g(l):
        c=[o for o in d.Objects if o.Label==l and o.isDerivedFrom("Part::Feature")]; s=c[0].Shape.copy(); s.Placement=c[0].getGlobalPlacement(); return s
    clip=Part.makeBox(470,51.3,60,V(-480,243.2,400))
    for bl in ("GT2 9mm belt, lower (Monolith 2WD)","GT2 9mm belt, upper (Monolith 2WD)"):
        b=g(bl).common(clip)
        for pl in ("Plate","Plate(Mirror)"):
            p=g(pl)
            for dy,what in ((ty,"parked"),(ty-6.0,"large opening")):
                bb=b.copy(); bb.translate(V(0,dy,0))
                dist=bb.distToShape(p)[0]; vol=bb.common(p).Volume if dist<1e-6 else 0.0
                # signed: if overlapping, how deep in Y — shift back until clear
                depth=0.0
                if vol>0:
                    for k in range(1,200):
                        t=bb.copy(); t.translate(V(0,0.05*k,0))
                        if t.distToShape(p)[0]>1e-6: depth=0.05*k; break
                out.write(f"{f} {bl.split(',')[1].strip()} vs {pl} at {what} (gantry dY {dy:.2f}): clearance {dist:.2f} mm, overlap {vol:.2f} mm3, depth {depth:.2f}\n")
    FreeCAD.closeDocument(d.Name)
except Exception: out.write(traceback.format_exc())
out.close(); os._exit(0)
