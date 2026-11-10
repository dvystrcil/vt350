import sys, zipfile, re, collections
import xml.etree.ElementTree as ET
fc, docxml = sys.argv[1], sys.argv[2]
sizes = {i.filename: i.file_size for i in zipfile.ZipFile(fc).infolist()}
root = ET.parse(docxml).getroot()
types = {o.get('name'): o.get('type') for o in root.find('Objects')}
label, group, shapefile, placement_vis = {}, {}, {}, {}
for od in root.find('ObjectData'):
    n = od.get('name')
    for p in od.iter('Property'):
        pn = p.get('name')
        if pn == 'Label':
            label[n] = p.find('String').get('value')
        elif pn == 'Group':
            group[n] = [l.get('value') for l in p.iter('Link')]
        elif pn == 'Shape' and types[n] == 'Part::Feature':
            f = p.find('Part')
            if f is not None: shapefile[n] = f.get('file')
parent = {}
for g, kids in group.items():
    for k in kids: parent[k] = g
def path(n):
    out = []
    while n in parent:
        n = parent[n]; out.append(label.get(n, n))
    return list(reversed(out))
tops = [n for n in types if n not in parent and types[n] in ('App::Part','Part::Feature')]
print("top-level:", [(label[t], types[t]) for t in tops][:20])
# size per top-level subtree
def subtree(n):
    yield n
    for k in group.get(n, []): yield from subtree(k)
def bytes_of(n): return sum(sizes.get(shapefile.get(x,''),0) for x in subtree(n))
def count(n): return sum(1 for x in subtree(n) if types.get(x)=='Part::Feature')
print("\n== top-level & 2nd-level assemblies by geometry MB")
rows=[]
for t in tops:
    rows.append((bytes_of(t), 0, label[t], count(t)))
    for k in group.get(t, []):
        if types.get(k) in ('App::Part','Part::Feature'):
            rows.append((bytes_of(k), 1, label[k], count(k)))
for b,d,l,c in rows[:80]:
    print(f"{'   '*d}{b/1e6:8.1f} MB  {c:5d} shapes  {l}")
print("\n== duplicate geometry (same label stem, same brp size)")
stem = lambda s: re.sub(r'[\s_-]*\(?\d+\)?$|[\s_]*\d{3,}$', '', s)
dup = collections.defaultdict(list)
for n,f in shapefile.items(): dup[(stem(label[n]), sizes.get(f,0))].append(n)
d = sorted(dup.items(), key=lambda kv: -kv[0][1]*(len(kv[1])-1))
waste = sum(k[1]*(len(v)-1) for k,v in d)
print(f"bytes in duplicated copies: {waste/1e6:.0f} MB of {sum(sizes.get(f,0) for f in shapefile.values())/1e6:.0f} MB")
for (s,b),v in d[:30]:
    print(f"{len(v):4d} x {b/1e6:6.2f} MB  {s!r}  e.g. {' / '.join(path(v[0])[-2:])}")
print("\n== biggest single shapes")
for n,f in sorted(shapefile.items(), key=lambda kv:-sizes.get(kv[1],0))[:15]:
    print(f"{sizes[f]/1e6:6.1f} MB {label[n]!r}  in {' / '.join(path(n))}")
