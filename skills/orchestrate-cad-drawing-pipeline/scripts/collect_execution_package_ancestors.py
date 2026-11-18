"""Record real Node package configuration and absence for new output ancestors."""
from pathlib import Path
import hashlib,json,os,shutil
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def extend(index,package,work):
    package,work=Path(package).resolve(),Path(work).resolve();observed=[];added=[]
    if package.is_relative_to(work)or work.is_relative_to(package):raise ValueError('Input and output roots must be disjoint')
    for folder in work.parents:
        candidate=folder/'package.json';key=os.path.normcase(str(candidate))
        if candidate.is_file():
            if key in index['negative']:raise ValueError('Previously absent Node ancestor package appeared: '+str(candidate))
            expected=sha(candidate)
            if key in index['files']:
                if index['files'][key]['sha256']!=expected:raise ValueError('Original Node ancestor package changed: '+str(candidate))
            else:
                target=package/'supplements/execution-ancestor-packages'/expected/'package.json';target.parent.mkdir(parents=True,exist_ok=True)
                if target.exists():
                    if sha(target)!=expected:raise ValueError('Delivered ancestor package changed')
                else:shutil.copyfile(candidate,target)
                index['files'][key]=dict(relative=target.relative_to(package).as_posix(),sha256=expected,source_scope='new_execution_output_ancestor_Node_package')
                added.append(key)
            observed.append(dict(path=str(candidate),state='file',sha256=expected))
        elif candidate.exists():
            raise ValueError('Node package configuration is not a regular file')
        else:
            if key in index['files']:raise ValueError('Fixed Node ancestor package disappeared: '+str(candidate))
            if key not in index['negative']:index['negative'].append(key);added.append(key)
            observed.append(dict(path=str(candidate),state='missing'))
    index['execution_output_ancestor_package_constraints']=observed
    return dict(observed=observed,added=added)
