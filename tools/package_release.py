"""Assemble a portable Windows release with examples, notices and SHA256."""
import argparse
import hashlib
from pathlib import Path
import sys
from zipfile import ZipFile,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import engine as E

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('exe',type=Path)
    args=parser.parse_args()
    executable=args.exe.resolve()
    out=ROOT/'dist'; out.mkdir(exist_ok=True)
    stem=f'GenshinDustCalculator-{E.VERSION}-win64'
    renamed=out/f'{stem}.exe'
    if executable!=renamed:
        renamed.write_bytes(executable.read_bytes())
    archive=out/f'{stem}.zip'
    with ZipFile(archive,'w',ZIP_DEFLATED) as z:
        z.write(renamed,renamed.name)
        for name in ('README.md','LICENSE','THIRD_PARTY_NOTICES.md','CHANGELOG.md'):
            z.write(ROOT/name,name)
        for folder in ('docs','examples','licenses'):
            for file in sorted((ROOT/folder).rglob('*')):
                if file.is_file():
                    z.write(file,file.relative_to(ROOT).as_posix())
    with ZipFile(archive) as z:
        if z.testzip() is not None:
            raise AssertionError('Release ZIP has an invalid CRC')
    hashes=''.join(f'{hashlib.sha256(file.read_bytes()).hexdigest()}  {file.name}\n'
                   for file in (renamed,archive))
    (out/'SHA256SUMS.txt').write_text(hashes,encoding='utf-8')
    print(renamed.name,archive.name,'SHA256SUMS.txt',sep='\n')

if __name__=='__main__':
    main()
