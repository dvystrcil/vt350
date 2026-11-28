# SPDX-License-Identifier: GPL-3.0-or-later
"""vt350#78 option A: plan + front elevation of the left end, drawn from cad/data/crossbow_depressor_probe.json
(boxes, Left head carried). Plain python3, writes an SVG; rsvg-convert makes the PNG.

    python3 cad/studies/crossbow_depressor_draw.py   # -> cad/renders/c78-depressor/option-a.svg
"""
import json, os
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
d = json.load(open(REPO + "/cad/data/crossbow_depressor_probe.json"))
OUT = REPO + "/cad/renders/c78-depressor/option-a.svg"
XN0 = -245.0     # carried nozzle X in the model pose: docked -409.70 + T_pick 164.70 (sweep_toolhead.log)
LIM = -416.0     # sweep_toolhead.log: first nozzle X with no new overlap, left side (SpeedClip vs the XY left joint)
THROW = 9.0      # AFC _AFC_CUT_TIP_VARS cut_move_dist default 8.5 + 0.5; measure on the real cutter (AC1)
L={c["label"]:c["box_carried"] for c in d["Left"]["crossbow"]}
lev=L["Crossbow - Lever"]; body=L["Crossbow - Main Body"]; adp=[v for k,v in L.items() if "adapter" in k][0]
car=d["carriage"]; joint=d["XY left: _XY_left"]["box"]; beam=d["beam"][0]
TIP=lev[0]-XN0; XB=LIM+TIP+THROW; contact=XB-TIP
DOCK1=-409.70   # slot 1 (Left) docked nozzle X (sweep_toolhead.log); its lever tip sits at DOCK1+TIP
DTIP=DOCK1+TIP
fing=[XB-8,lev[1]-2,lev[2],XB,joint[1],lev[5]+4]
SC=3.2; X0,X1=-490,-200
views=[("PLAN, looking down (back of the printer at the top)",1,170,300),("FRONT ELEVATION, looking from the front",2,385,495)]
W=(X1-X0)*SC+120; H=15+sum((v[3]-v[2])*SC+90 for v in views)+70
o=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" font-family="sans-serif" font-size="12"><rect width="100%" height="100%" fill="white"/>',
   f'<text x="20" y="22" font-size="14" font-weight="bold">vt350#78 Option A: a finger on the left XY joint (rides with the gantry). Boxes from lite-81, Left head carried.</text>',
   f'<text x="20" y="42">Lever tip = nozzle X {TIP:+.2f}. Throw {THROW} mm (AFC default 8.5 + 0.5; measure on the real cutter). Finger face X {XB:.1f}: lever touches at nozzle X {contact:.1f}, fully pressed at the travel limit {LIM:.0f}.</text>',
   f'<text x="20" y="78" fill="#b00">Clash: the slot 1 dock holds its head at nozzle X {DOCK1:.1f}, lever tip X {DTIP:.1f}; this finger would press that lever {XB-DTIP:.1f} mm at pickup (a cut at the dock).</text>',
   f'<text x="20" y="60">Cost: printing must stay right of nozzle X {contact+1:.1f} (1 mm margin), so the left edge moves {contact+1-LIM:.1f} mm in: 342.0 to {342.0-(contact+1-LIM):.1f} mm wide.</text>']
top=95
for title,j,v0,v1 in views:
    h=(v1-v0)*SC
    px=lambda x:60+(x-X0)*SC; py=lambda v:top+30+(v1-v)*SC
    o.append(f'<text x="60" y="{top+18}" font-weight="bold">{title}</text>')
    o.append(f'<rect x="60" y="{top+30}" width="{(X1-X0)*SC}" height="{h}" fill="none" stroke="#ccc"/>')
    def R(b,dx=0,**k):
        a=" ".join(f'{kk.replace("_","-")}="{vv}"' for kk,vv in k.items())
        x0,x1=b[0]+dx,b[3]+dx; o.append(f'<rect x="{px(x0):.1f}" y="{py(b[j+3]):.1f}" width="{(x1-x0)*SC:.1f}" height="{(b[j+3]-b[j])*SC:.1f}" {a}/>')
    R(joint,fill="url(#h)",stroke="black",stroke_width=1.5); R(beam,fill="none",stroke="#777")
    for xn,dash,op in ((LIM,"",1),(contact,"6,4",0.55)):
        dx=xn-XN0
        R(car,dx,fill="none",stroke="#1f77b4",stroke_dasharray=dash,opacity=op,stroke_width=1.5)
        R(adp,dx,fill="none",stroke="#2ca02c",stroke_dasharray=dash,opacity=op); R(body,dx,fill="none",stroke="#2ca02c",stroke_dasharray=dash,opacity=op)
        R(lev,dx,fill="#d62728",fill_opacity=0.35*op,stroke="#d62728",stroke_dasharray=dash)
    R(fing,fill="#ff7f0e",stroke="black",opacity=0.9)
    o.append(f'<line x1="{px(DTIP)}" y1="{top+30}" x2="{px(DTIP)}" y2="{top+30+h}" stroke="#b00" stroke-dasharray="5,3"/><text x="{px(DTIP)-3}" y="{top+30+h-6}" fill="#b00" font-size="10" text-anchor="end">slot 1 docked lever tip {DTIP:.1f}</text>')
    o.append(f'<line x1="{px(-420)}" y1="{top+30}" x2="{px(-420)}" y2="{top+30+h}" stroke="#888" stroke-dasharray="2,3"/><text x="{px(-420)+3}" y="{top+44}" fill="#666" font-size="10">print square edge -420</text>')
    for x in range(-480,-199,20):
        o.append(f'<text x="{px(x)}" y="{top+30+h+14}" font-size="9" text-anchor="middle" fill="#666">{x}</text>')
    top+=h+90
ly=H-20
o.append(f'<text x="20" y="{ly}" font-size="11"><tspan fill="#d62728">red: Crossbow lever</tspan>   <tspan fill="#1f77b4">blue: carriage</tspan>   <tspan fill="#2ca02c">green: Crossbow body + adapter</tspan>   solid = at the travel limit {LIM:.0f}, dashed = first touch {contact:.1f}   <tspan fill="#ff7f0e">orange: finger</tspan>   hatched: XY left joint (box only)</text>')
o.insert(1,'<defs><pattern id="h" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="#999"/></pattern></defs>')
o.append("</svg>")
os.makedirs(os.path.dirname(OUT), exist_ok=True); open(OUT,"w").write("\n".join(o)); print(XB,contact,TIP, "gap lever->joint Y", joint[1]-lev[4], "lever Z", lev[2],lev[5], "joint top", joint[5])
