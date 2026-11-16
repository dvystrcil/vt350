# GUI study (vt350#195 AC1): how long a model takes to open in the FreeCAD GUI, the 3D view included.
#   VT350_MODEL=~/Documents/VT350/vt350-lite-48.FCStd $NV $APP $PWD/cad/studies/open_time.py
# Appends one line to cad/data/logs/open_time.log: model, file size, the open, the first full redraw of the view, the
# total. Read-only: never saves. Exits by itself.
import FreeCAD, os, time
t0 = time.time()
REPO = os.environ.get("VT350_REPO", "/home/dan/Code/vt350")
path = os.path.expanduser(os.environ.get("VT350_MODEL", "~/Documents/VT350/vt350-lite-47.FCStd"))
doc = FreeCAD.openDocument(path)
t_open = time.time() - t0
line = f"{time.strftime('%Y-%m-%d %H:%M')}  {os.path.basename(path)}  {os.path.getsize(path) / 2 ** 20:.0f} MiB  open {t_open:.1f}s"
if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtGui
    FreeCADGui.ActiveDocument.ActiveView.viewIsometric(); FreeCADGui.SendMsgToActiveView("ViewFit")
    QtGui.QApplication.processEvents()
    FreeCADGui.updateGui()
    t_draw = time.time() - t0 - t_open
    line += f"  view {t_draw:.1f}s  total {time.time() - t0:.1f}s  (GUI)"
else:
    line += "  (headless: no view)"
with open(f"{REPO}/cad/data/logs/open_time.log", "a") as f: f.write(line + "\n")
os._exit(0)
