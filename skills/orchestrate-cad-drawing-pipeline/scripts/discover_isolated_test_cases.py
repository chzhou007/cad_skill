"""Enumerate explicitly qualified per-method tests in a disposable subprocess."""
import contextlib,hashlib,importlib,io,json,os,sys,unittest
from pathlib import Path

def discover(name):
    if os.getcwd()not in sys.path:sys.path.insert(0,os.getcwd())
    with contextlib.redirect_stdout(io.StringIO()):
        module=importlib.import_module(name)
        if any(hasattr(module,key)for key in ('load_tests','setUpModule','tearDownModule')):raise ValueError('module fixtures must remain together')
        suite=unittest.defaultTestLoader.loadTestsFromModule(module);ids=[]
        def walk(test):
            if isinstance(test,unittest.TestSuite):
                for child in test:walk(child)
            else:
                if any(any(key in cls.__dict__ for key in ('setUpClass','tearDownClass'))for cls in type(test).__mro__ if cls is not unittest.TestCase):raise ValueError('class fixtures must remain together')
                ident=test.id()
                if not ident.startswith(name+'.'):raise ValueError('imported test must remain with original module')
                ids.append(ident)
        walk(suite)
    if not ids or len(ids)!=len(set(ids)):raise ValueError('unique nonempty test IDs required')
    return dict(module=name,module_sha256=hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(),test_ids=ids)

if __name__=='__main__':print(json.dumps(discover(sys.argv[1])),flush=True)
