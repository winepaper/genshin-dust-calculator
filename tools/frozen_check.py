"""Launch the built Windows executable and verify its actual outputs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from verification import manual_check

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('exe',type=Path)
    args=parser.parse_args()
    exe=args.exe.resolve()
    output=ROOT/'artifacts'/'frozen'
    output.mkdir(parents=True,exist_ok=True)
    startup=None
    if sys.platform=='win32':
        startup=subprocess.STARTUPINFO()
        startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow=subprocess.SW_HIDE
    cases=(('--verify',output/'verification.json'),
           ('--smoke-test',output/'light.png'),
           ('--smoke-test',output/'three-effective.png','--preset','er'),
           ('--smoke-test',output/'dark.png','--preset','er','--dark'))
    for case in cases:
        subprocess.run([str(exe),*(str(v) for v in case)],cwd=ROOT,check=True,
                       timeout=45,startupinfo=startup)
        file=case[1]
        if not file.exists() or file.stat().st_size==0:
            raise AssertionError(f'Missing output: {file}')
    actual=json.loads((output/'verification.json').read_text(encoding='utf-8'))
    maximum=0.0
    for current,expected in zip(actual,manual_check.output):
        maximum=max(maximum,abs(current['current']-expected['current']))
        for row in expected['results']:
            for key in ('pwin','gain','per_dust','raw_mean'):
                error=abs(current['results'][str(row['guarantee'])][key]-row[key])
                maximum=max(maximum,error)
    if len(actual)!=len(manual_check.output) or maximum>1e-9:
        raise AssertionError(f'Frozen/manual mismatch: {maximum}')
    print(f'PASS: frozen startup, four outputs and exact sample checks; max error {maximum:.3e}')

if __name__=='__main__':
    main()
