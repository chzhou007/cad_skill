"""Inherit the original observer and qualify only bound fresh-parent receipts."""
import hashlib,importlib.util,json,os
from pathlib import Path

MODE='qualified_fresh_parent_producer_receipt_v1'
def sha(p):
    with open(p,'rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def key(p):return os.path.normcase(os.path.abspath(p))
def receipt_bindings(index,work):
    work=Path(work).resolve();groups={}
    for logical,row in index.get('generated_local_parents',{}).items():
        target=(work/row['relative']).resolve();receipt=(work/row['producer_receipt_relative']).resolve()
        if not target.is_relative_to(work)or not receipt.is_relative_to(work):raise ValueError('fresh producer receipt or output escaped work')
        pointer=row['producer_field']
        if not(isinstance(pointer,list)and len(pointer)==3 and pointer[0]=='local_topologies'and type(pointer[1])is int and pointer[1]>=0 and pointer[2]in('graph','components')):
            raise ValueError('fresh producer receipt needs actual output role')
        name=key(receipt);entry=groups.setdefault(name,dict(path=str(receipt),sha256=row['producer_receipt_sha256'],outputs=[]))
        if entry['sha256']!=row['producer_receipt_sha256']:raise ValueError('conflicting fresh producer receipt identity')
        value=dict(logical=logical,path=str(target),sha256=row['sha256'],producer_field=pointer)
        if value not in entry['outputs']:entry['outputs'].append(value)
    if any(name in {key(o['path'])for g in groups.values()for o in g['outputs']}for name in groups):raise ValueError('receipt cannot also be a generated output')
    return groups

def checked_receipt(binding):
    p=Path(binding['path'])
    if sha(p)!=binding['sha256']:raise ValueError('fresh parent producer receipt changed')
    proof=json.loads(p.read_text('utf8'))
    if proof.get('mode')!='raw_CAD_to_current_local_topology_delivered_API_input_replay_v1':raise ValueError('fresh parent producer receipt mode differs')
    for row in binding['outputs']:
        field=row['producer_field'];records=proof.get('local_topologies',[])
        if field[1]>=len(records):raise ValueError('fresh parent producer output pointer absent')
        record=records[field[1]]
        if record.get('graph_and_component_bytes_exact')is not True or record.get(field[2],{}).get('sha256')!=row['sha256']:
            raise ValueError('fresh parent producer output identity differs')
        if sha(row['path'])!=row['sha256']:raise ValueError('fresh parent output changed')
    return dict(mode=MODE,producer_receipt=dict(path=str(p),sha256=binding['sha256']),actual_generated_outputs=binding['outputs'],startup_seed=False,historical_final_graph_used=False)

class Observation:
    def __new__(cls,runtime,policy,binding):
        original=binding.get('base_observer')
        if not isinstance(original,dict):raise ValueError('original observer binding required')
        path=(runtime.package/original['relative']).resolve()
        if not path.is_relative_to(runtime.package)or sha(path)!=original['sha256']:raise ValueError('original observer changed or escaped package')
        spec=importlib.util.spec_from_file_location('_bound_original_producer_observer',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        class BoundObservation(module.Observation):
            def __init__(self,*args):
                super().__init__(*args);self.parent_receipts=receipt_bindings(self.runtime.index,self.runtime.work);self.receipt_reads={}
                self.physical[self.runtime.key(path)]=original['sha256']
            def target(self,value,writing=False):
                actual,role=super().target(value,writing)
                return(actual,'qualified_fresh_parent_receipt')if actual in self.parent_receipts else(actual,role)
            def screen(self,path,role,state,operation,writing=False):
                if role!='qualified_fresh_parent_receipt':return super().screen(path,role,state,operation,writing)
                if writing:raise PermissionError('Fresh parent producer receipt is read-only')
                proof=checked_receipt(self.parent_receipts[path])
                if state.get('kind')!='file'or state.get('sha256',proof['producer_receipt']['sha256'])!=proof['producer_receipt']['sha256']:
                    raise ValueError('observed fresh parent receipt differs')
                self.receipt_reads[path]=proof;return proof
            def finish(self):
                result=super().finish()
                def save():
                    for value in self.parent_receipts.values():checked_receipt(value)
                    with module.OPEN(result['path'],encoding='utf8')as f:report=json.load(f)
                    report['qualified_fresh_parent_producer_receipts']=list(self.receipt_reads.values())
                    with module.OPEN(result['path'],'w',encoding='utf8')as f:json.dump(report,f,ensure_ascii=False,indent=2)
                    result['sha256']=module.sha(result['path']);return result
                return self.quiet(save)
        return BoundObservation(runtime,policy,binding)
