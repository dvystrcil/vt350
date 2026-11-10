import sys, re, collections, xml.etree.ElementTree as ET
root = ET.parse(sys.argv[1]).getroot()
types = {o.get('name'): o.get('type') for o in root.find('Objects')}
label, group = {}, {}
for od in root.find('ObjectData'):
    n=od.get('name')
    for p in od.iter('Property'):
        if p.get('name')=='Label': label[n]=p.find('String').get('value')
        elif p.get('name')=='Group': group[n]=[l.get('value') for l in p.iter('Link')]
parent={k:g for g,ks in group.items() for k in ks}
SELF = re.compile(r'screw|bolt|\bnuts?\b|t-nut|washer|threaded insert|heat.?set|91290|shcs|bhcs|fhcs|\bdin ?(912|7380|7991|125|934)|\biso ?\d{4}|^m[2-6]\s*[x*×]', re.I)
hit, anc_only = collections.Counter(), collections.Counter()
for n,t in types.items():
    if t!='Part::Feature': continue
    l=label[n]; a=[]; m=n
    while m in parent: m=parent[m]; a.append(label[m])
    stem=re.sub(r'\s*\(\d+\)|\d{3}$|\(Mirror\)','',l)
    if SELF.search(l): hit[stem]+=1
    elif any(SELF.search(x) for x in a[:2]): anc_only[(stem, a[0])]+=1
print("== matched by OWN label:"); [print(f"{c:4d} {s}") for s,c in hit.most_common()]
print("\n== only matched via parent label (review):"); [print(f"{c:4d} {s!r} in {p!r}") for (s,p),c in anc_only.most_common()]
