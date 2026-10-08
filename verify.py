"""Compare independent arithmetic with the production model. Standard library only."""
from dataclasses import replace
import json
from pathlib import Path
import engine as E
from verification import manual_check, manual_three_effective, weight100, er_only

def main():
    maximum_error=0.0
    cases=0
    def same(actual,expected,label):
        nonlocal maximum_error
        error=abs(float(actual)-float(expected))
        maximum_error=max(maximum_error,error)
        if error>1e-9:
            raise AssertionError(f'{label}: {actual} != {expected}')

    for art,manual in zip(E.SAMPLES,manual_check.output):
        inf=E.infer(art)
        same(inf.current_mean,manual['current'],art.name)
        for row in manual['results']:
            actual=E.analyze(inf,guarantee=row['guarantee'])
            for key in ('pwin','gain','per_dust','raw_mean'):
                same(actual[key],row[key],f'{art.name} {key}')
            cases+=1

    three=replace(E.SAMPLES[0],rows=tuple(replace(r,weight='1') if r.stat=='er' else r for r in E.SAMPLES[0].rows))
    inf=E.infer(three)
    same(inf.current_mean,manual_three_effective.current,'three-effective current')
    same(sum(row['score_mean'] for row in inf.row_summary),inf.current_mean,'score contributions')
    for g,expected in manual_three_effective.results.items():
        actual=E.analyze(inf,guarantee=g)
        for key,value in expected.items():
            same(actual[key],value,f'three-effective {g} {key}')
        cases+=1

    weighted=replace(three,rows=tuple(replace(r,weight='100') if r.stat=='er' else r for r in three.rows))
    inf=E.infer(weighted)
    same(inf.current_mean,weight100.current,'ER100 current')
    for pair in ((2,3),(0,2),(0,3)):
        for g in (2,3,4):
            expected=weight100.independent(pair,g)
            actual=E.analyze(inf,selected=pair,guarantee=g)
            for key,value in expected.items():
                if isinstance(value,tuple):
                    for i,item in enumerate(value):
                        same(actual[key][i],item,f'ER100 {pair} {g} {key}')
                else:
                    same(actual[key],value,f'ER100 {pair} {g} {key}')
            cases+=1

    only=replace(three,rows=tuple(replace(r,weight='1' if r.stat=='er' else '0') for r in three.rows))
    inf=E.infer(only); actual=E.analyze(inf)
    same(actual['pwin'],er_only.win,'ER-only win')
    same(actual['gain'],float(er_only.positive_pp)/5.505,'ER-only selected improvement')
    same(actual['raw_mean']-inf.current_mean,float(er_only.raw_pp)/5.505,'ER-only raw downside')
    same(er_only.win+er_only.tie+er_only.bad,1,'ER-only probability sum')
    cases+=1

    summary=dict(version=E.VERSION,independent_cases=cases,max_absolute_error=maximum_error)
    output=Path(__file__).parent/'artifacts'/'verification.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(f'PASS: {cases} independent cases; max absolute error {maximum_error:.3e}')

if __name__=='__main__':
    main()
