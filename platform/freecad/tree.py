import sys, xml.etree.ElementTree as ET
root = ET.parse(sys.argv[1]).getroot(); maxd=int(sys.argv[2])
types = {o.get('name'): o.get('type') for o in root.find('Objects')}
label, group = {}, {}
for od in root.find('ObjectData'):
    n=od.get('name')
    for p in od.iter('Property'):
        if p.get('name')=='Label': label[n]=p.find('String').get('value')
        elif p.get('name')=='Group': group[n]=[l.get('value') for l in p.iter('Link')]
skip={'App::Origin','App::Plane','App::Line','App::Point'}
def walk(n,d):
    kids=[k for k in group.get(n,[]) if types.get(k) not in skip]
    print('  '*d+f"{label[n]}  [{len(kids)}]" if kids else '  '*d+label[n])
    if d<maxd:
        for k in kids:
            if group.get(k) or d+1<maxd: walk(k,d+1)
par={k for ks in group.values() for k in ks}
walk([n for n in types if types[n]=="App::Part" and n not in par][0],0)
