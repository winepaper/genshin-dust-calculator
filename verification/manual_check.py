"""Independent arithmetic for the two hand-derived screenshot examples.

Only the dice law and the manually listed base/current possibilities are used;
this script does not import engine.py or its inference/DP implementation.
"""
from collections import defaultdict
from fractions import Fraction as F
from math import comb, lcm
import json
from pathlib import Path

cr = (272,311,350,389)
cd = (544,622,699,777)
factor_cr, factor_cd = F(4,sum(cr)), F(4,sum(cd))
scale = lcm(factor_cr.denominator,factor_cd.denominator)
a,b = int(factor_cr*scale),int(factor_cd*scale)
dice = [a*x for x in cr]+[b*x for x in cd]
sum_dists = [{0:1.}]
for k in range(1,6):
    nxt = defaultdict(float)
    for x,p in sum_dists[-1].items():
        for d in dice:
            nxt[x+d] += p/8
    sum_dists.append(dict(nxt))

# CD 20.2% consists of ordered triples with tier patterns:
# (1,3,4): 6 orders; (2,2,4): 3; (2,3,3): 3.
# Grouping by the FIRST (base) value and exact table total gives these masses.
cd_states = [(544,2020,2/12),(622,2020,1/12),(622,2021,2/12),
             (699,2020,4/12),(777,2020,2/12),(777,2021,1/12)]
samples = [("截图1 · 攻击杯",5,2,[(272,544,1.)]),
           ("截图2 · 花",4,1,[(value,661,.25) for value in cr])]
output=[]
for name,n,cost,cr_states in samples:
    hypotheses=[]
    for base_cr,current_cr,pcr in cr_states:
        for base_cd,current_cd,pcd in cd_states:
            old=a*current_cr+b*current_cd
            base=a*base_cr+b*base_cd
            hypotheses.append((old,base,pcr*pcd))
    rows=[]
    for g in (2,3,4):
        pk=defaultdict(float)
        for k in range(n+1):
            pk[max(k,g)] += comb(n,k)/2**n
        win=gain=raw=0.
        for old,base,p in hypotheses:
            for k,p_k in pk.items():
                for s,p_s in sum_dists[k].items():
                    mass=p*p_k*p_s
                    raw += mass*(base+s)/scale
                    if base+s>old:
                        win += mass
                        gain += mass*(base+s-old)/scale
        rows.append(dict(guarantee=g,pwin=win,gain=gain,per_dust=gain/cost,raw_mean=raw))
    current=sum(old*p for old,base,p in hypotheses)/scale
    output.append(dict(name=name,current=current,results=rows))
if __name__ == "__main__":
    path=Path(__file__).resolve().parents[1]/"artifacts"/"manual-independent.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(output,ensure_ascii=False,indent=2))
