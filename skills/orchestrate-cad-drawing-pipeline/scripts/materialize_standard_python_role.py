"""Restore a standard Python role using only the supplied split runtime bytes."""
from pathlib import Path,PurePosixPath
import argparse,base64,csv,hashlib,json,os

def sha(path):
    with open(path,'rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def wheel_spellings(root):
    """Use supplied wheel RECORD names, not guesses, for case-sensitive imports."""
    actual={p.relative_to(root).as_posix().casefold():p for p in root.rglob('*')if p.is_file()}
    result={}
    for record in root.glob('*.dist-info/RECORD'):
        with record.open(encoding='utf-8-sig',newline='')as stream:
            for row in csv.reader(stream):
                if len(row)!=3:raise ValueError('Invalid supplied wheel RECORD')
                name,digest,size=row;relative=PurePosixPath(name)
                if relative.is_absolute()or '\\'in name:raise ValueError('Wheel file name leaves library namespace')
                # Console scripts live outside site-packages and are not part
                # of this library role. Never construct an output from them.
                if '..'in relative.parts:continue
                key=relative.as_posix().casefold();source=actual.get(key)
                if source is None:continue
                if not source.resolve().is_relative_to(root.resolve()):raise ValueError('Wheel RECORD source escaped library root')
                if size and source.stat().st_size!=int(size):raise ValueError('Wheel RECORD size differs')
                if digest:
                    algorithm,expected=digest.split('=',1)
                    if algorithm not in ('sha256','sha384','sha512'):raise ValueError('Unsupported wheel RECORD hash')
                    with source.open('rb')as data:observed=base64.urlsafe_b64encode(hashlib.file_digest(data,algorithm).digest()).decode().rstrip('=')
                    if observed!=expected:raise ValueError('Wheel RECORD content hash differs')
                if key in result and result[key]!=relative:raise ValueError('Conflicting wheel filename case')
                result[key]=relative
    return result

def restore(package,relative='runtime/standard-python'):
    package=Path(package).resolve();output=(package/relative).resolve()
    bases=[package/'runtime/python',package/'runtime/site-packages']
    if not output.is_relative_to(package)or output==package or any(output.is_relative_to(p)or p.is_relative_to(output)for p in bases):raise ValueError('Runtime output must be separate and stay in the package')
    if output.exists():raise FileExistsError(output)
    if not all(p.is_dir()for p in bases):raise ValueError('Delivered split runtime is incomplete')
    output.mkdir(parents=True);files={}
    def native(path):return '\\\\?\\'+str(path.absolute())if os.name=='nt'else str(path)
    def copy(source,relative):
        target=output/relative
        if not source.resolve().is_relative_to(package):raise ValueError('Runtime source escaped package')
        os.makedirs(native(target.parent),exist_ok=True)
        os.link(native(source),native(target))
        if sha(target)!=sha(source):raise ValueError('Runtime role bytes changed')
        files[target.relative_to(package).as_posix()]=sha(target)
    for source in bases[0].rglob('*'):
        if not source.is_file():continue
        relative_source=source.relative_to(bases[0])
        if source.suffix=='._pth'or tuple(v.lower()for v in relative_source.parts[:2])==('lib','site-packages'):continue
        copy(source,relative_source)
    spellings=wheel_spellings(bases[1])
    directories={}
    for relative in spellings.values():
        for parent in relative.parents:
            key=parent.as_posix().casefold()
            if key in directories and directories[key]!=parent:raise ValueError('Conflicting wheel directory case')
            directories[key]=parent
    # An unrecorded cache file may be enumerated before its source module.
    # Create the authoritative package spelling first on Windows too.
    for parent in sorted(directories.values(),key=lambda p:len(p.parts)):
        os.makedirs(native(output/'Lib/site-packages'/parent),exist_ok=True)
    for source in bases[1].rglob('*'):
        if source.is_file():
            original=source.relative_to(bases[1]);restored=spellings.get(original.as_posix().casefold(),original)
            copy(source,Path('Lib/site-packages')/restored)
    for name in ('python312._pth','python._pth','python3.12._pth'):
        path=output/name;path.write_text('.\nDLLs\nLib\nLib/site-packages\n',encoding='utf8');files[path.relative_to(package).as_posix()]=sha(path)
    proof=dict(mode='delivered_standard_python_library_role_v1',executable=(output/'python.exe').relative_to(package).as_posix(),files=files,
        source_runtime_bytes_modified=False,global_python_modified=False,wheel_RECORD_case_entries=len(spellings),derived_pth_files=['python312._pth','python._pth','python3.12._pth'])
    (output/'role-manifest.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
    return proof

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--package',required=True,type=Path);parser.add_argument('--relative-output',default='runtime/standard-python')
    args=parser.parse_args();proof=restore(args.package,args.relative_output);print(json.dumps(dict(files=len(proof['files']),executable=proof['executable'])))
