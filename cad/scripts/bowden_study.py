import os, numpy as np
OUT=open(os.path.dirname(os.path.abspath(__file__))+"/study2.out","w")
t=np.linspace(0,1,200)[:,None]
B=[(1-t)**3,3*(1-t)**2*t,3*(1-t)*t**2,t**3]
D1=[-3*(1-t)**2,3*(1-t)**2-6*(1-t)*t,6*(1-t)*t-3*t**2,3*t**2]
D2=[6*(1-t),-12*(1-t)+6*t,6*(1-t)-12*t,6*t]
def ev(P0,T0,P1,T1,a,b):
    c=[P0,P0+T0*a,P1-T1*b,P1]
    p=sum(B[i]*c[i] for i in range(4)); d1=sum(D1[i]*c[i] for i in range(4)); d2=sum(D2[i]*c[i] for i in range(4))
    k=np.linalg.norm(np.cross(d1,d2),axis=1)/np.maximum(np.linalg.norm(d1,axis=1),1e-9)**3
    return np.sum(np.linalg.norm(np.diff(p,axis=0),axis=1)), 1/max(k.max(),1e-9), p
H=np.arange(20,900,20)
def best(P0,T0,P1,T1,L=None,tol=10):
    bestv=None
    for a in H:
        for b in H:
            l,r,_=ev(P0,T0,P1,T1,a,b)
            if L is not None and abs(l-L)>tol: continue
            if bestv is None or r>bestv[1]: bestv=(l,r,a,b)
    return bestv
up=np.array([0,0,1.]); INZ=456.4; DOCKY=30.1
heads={'left':-399.0,'right':-92.0}
poses=lambda hx:[('docked',hx,DOCKY)]+[(f'({x:.0f},{y:.0f})',x,y) for x in (-420,-245,-70) for y in (60,240,420)]
exits={'roof y460 +Z':(lambda x:np.array([x,460,690.]),up),
       'roof y460 45 back':(lambda x:np.array([x,460,690.]),np.array([0,1,1])/2**.5),
       'back z630 +Y':(lambda x:np.array([x,508,630.]),np.array([0,1,0.]))}
for en,(E,T1) in exits.items():
  for h,hx in heads.items():
    P1=E(hx)
    free=best(np.array([hx,DOCKY,INZ]),up,P1,T1)
    OUT.write(f"{en:18} {h:5} docked, free length: L {free[0]:5.0f}  R {free[1]:5.0f}  (handles {free[2]},{free[3]})\n")
    for L in (650,700,750,800):
        rs=[]
        for nm,x,y in poses(hx):
            r=best(np.array([x,y,INZ]),up,P1,T1,L)
            rs.append((r[1] if r else 0.0,nm))
        mn=min(rs); OUT.write(f"{'':24}fixed L {L}: worst R {mn[0]:5.0f} at {mn[1]}; docked R {rs[0][0]:5.0f}\n")
    OUT.flush()
OUT.close(); os._exit(0)
