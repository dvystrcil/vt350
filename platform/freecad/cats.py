import sys, zipfile, re, collections
import xml.etree.ElementTree as ET
fc, docxml = sys.argv[1], sys.argv[2]
sizes = {i.filename: i.file_size for i in zipfile.ZipFile(fc).infolist()}
root = ET.parse(docxml).getroot()
types = {o.get('name'): o.get('type') for o in root.find('Objects')}
label, group, shapefile = {}, {}, {}
for od in root.find('ObjectData'):
    n = od.get('name')
    for p in od.iter('Property'):
        pn = p.get('name')
        if pn == 'Label': label[n] = p.find('String').get('value')
        elif pn == 'Group': group[n] = [l.get('value') for l in p.iter('Link')]
        elif pn == 'Shape' and types[n]=='Part::Feature':
            f = p.find('Part'); shapefile[n] = f.get('file') if f is not None else ''
parent = {k:g for g,ks in group.items() for k in ks}
def anc(n):
    out=[]
    while n in parent: n=parent[n]; out.append(label[n])
    return out
rules = [('fasteners (screws/nuts/washers/inserts)', r'screw|bolt|nut\b|t-nut|washer|insert|91290|shcs|bhcs|fhcs|\bm[2-6]\s*[x*]'),
         ('PCBs/electronics components', r'octopus|nitehawk|pcb|res0|cap0|c0402|r0402|raspberry|ds10|electronics'),
         ('leadscrews', r'leadscrew'),
         ('extrusions (2020/2040/4040)', r'\b(2020|2040|4040)\b|horizontals|verticals')]
tot = collections.Counter(); cnt = collections.Counter()
for n,f in shapefile.items():
    hay = ' | '.join([label[n]]+anc(n)[:4]).lower()
    cat = next((c for c,r in rules if re.search(r, hay)), 'everything else (printed parts, motors, rails...)')
    tot[cat]+=sizes.get(f,0); cnt[cat]+=1
for c,b in tot.most_common(): print(f"{b/1e6:7.0f} MB  {cnt[c]:5d} shapes  {c}")
print("GuiDocument.xml", sizes['GuiDocument.xml']/1e6, "MB; Document.xml", sizes['Document.xml']/1e6, "MB")
