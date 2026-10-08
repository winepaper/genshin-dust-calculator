"""Exact independent check of the screenshot using integer outcome counts."""
from collections import Counter,defaultdict
from fractions import Fraction as F
from math import comb,lcm
import json

# Two-decimal growth table, stored in hundredths of one percentage point.
cr=(272,311,350,389); cd=(544,622,699,777); er=(453,518,583,648)
factors=[F(4,sum(v))*w for v,w in zip((er,cd,cr),(100,1,1))]
scale=lcm(*(f.denominator for f in factors))
c,b,a=[int(f*scale) for f in factors]
dice_rows=([c*v for v in er],[0]*4,[b*v for v in cd],[a*v for v in cr])

def count_sums(dice):
    output=[{0:1}]
    for k in range(5):
        next_dist=Counter()
        for total,ways in output[-1].items():
            for value in dice: next_dist[total+value]+=ways
        output.append(dict(next_dist))
    return output

# These states are derived by hand from the visible artifact values.
cd_states=[(544,2020,F(2,12)),(622,2020,F(1,12)),(622,2021,F(2,12)),
           (699,2020,F(4,12)),(777,2020,F(2,12)),(777,2021,F(1,12))]
er_states=[(518,F(1,6)),(583,F(1,3)),(648,F(1,2))]
hypotheses=[(a*544+b*current_cd+c*1814,a*272+b*base_cd+c*base_er,p_cd*p_er)
            for base_cd,current_cd,p_cd in cd_states for base_er,p_er in er_states]
current=sum(F(old,scale)*p for old,base,p in hypotheses)

def independent(pair,g):
    other=tuple(i for i in range(4) if i not in pair)
    selected=count_sums(dice_rows[pair[0]]+dice_rows[pair[1]])
    not_selected=count_sums(dice_rows[other[0]]+dice_rows[other[1]])
    k_ways=Counter()
    for k in range(6): k_ways[max(k,g)]+=comb(5,k)
    upgrade=Counter()
    for k,ways_k in k_ways.items():
        for x,ways_x in selected[k].items():
            for y,ways_y in not_selected[5-k].items():
                upgrade[x+y]+=ways_k*ways_x*ways_y
    denominator=32*8**5
    assert sum(upgrade.values())==denominator
    win=target=gain=raw=F(0)
    state_wins=[]; state_gains=[]
    for old,base,p_state in hypotheses:
        wins=targets=gain_num=raw_num=0
        for inc,ways in upgrade.items():
            diff=base+inc-old
            raw_num+=(base+inc)*ways
            if diff>0:
                wins+=ways
                gain_num+=diff*ways
            if diff>=scale: targets+=ways
        pw=F(wins,denominator); pg=F(gain_num,denominator*scale)
        state_wins.append(pw); state_gains.append(pg)
        win+=p_state*pw; target+=p_state*F(targets,denominator)
        gain+=p_state*pg; raw+=p_state*F(raw_num,denominator*scale)
    return dict(pwin=win,gain=gain,per_dust=gain/2,raw_mean=raw,
                final_mean=current+gain,target_probability=target,
                success_gain=gain/win if win else F(0),
                gain_range=(min(state_gains),max(state_gains)),
                pwin_range=(min(state_wins),max(state_wins)))


if __name__=='__main__':
    result={'current':float(current),'results':{}}
    for pair in ((2,3),(0,2),(0,3)):
        for g in (2,3,4):
            row=independent(pair,g)
            values={k:[float(v) for v in value] if isinstance(value,tuple) else float(value) for k,value in row.items()}
            values['pwin_exact']=str(row['pwin'])
            result['results'][f'{pair}:{g}']=values
    print(json.dumps(result,ensure_ascii=False,indent=2))
