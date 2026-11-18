"""Replay an immutable original DN owner with exact semantic serialization.

Retain the original receipt and bytes. Only JSON object-key ordering may differ;
array order, scalar types, values and every source field remain significant.
"""
import json
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from legacy_named_provider_inventory import require

def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))

def compare(original,native):
    require(canonical(original)==canonical(native),'original complete plan DN native semantic value differs')

def replay(directory,diagnostic_directory=None,announce=lambda value:None):
    from rebuild_inherited_full_plan_DN import compute,implementation_hashes
    directory=Path(directory);rp=directory/'inherited-plan-DN-receipt.json';target=directory/'inherited-plan-DN-results.json';receipt=load(rp)
    before=sha(rp)
    def checked():
        require(sha(rp)==before and receipt['implementation_sha256']==implementation_hashes()
                and sha(receipt['manifest']['path'])==receipt['manifest']['sha256']and sha(target)==receipt['output_sha256'],
                'original DN receipt, source owner or canonical bytes changed')
    checked();native=compute(load(receipt['manifest']['path']),announce);original=load(target)
    try:compare(original,native)
    except ValueError:
        if diagnostic_directory is not None:
            diagnostic_directory=Path(diagnostic_directory);diagnostic_directory.mkdir(parents=True,exist_ok=False)
            (diagnostic_directory/'fresh-native-result.json').write_bytes(encode(native))
            (diagnostic_directory/'original-binding.json').write_bytes(encode(dict(receipt_sha256=before,proof_sha256=sha(target),original_proof=str(target),original_bytes_retained=True)))
        raise
    checked()
    return original,dict(owner='rebuild_inherited_full_plan_DN',original_receipt_sha256=before,original_proof_sha256=sha(target),
                         native_semantic_value_exact=True,original_bytes_retained=True,native_encoded_bytes_exact=encode(native)==target.read_bytes(),human_accepted=False)
