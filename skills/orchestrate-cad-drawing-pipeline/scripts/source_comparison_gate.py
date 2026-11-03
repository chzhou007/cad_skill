"""Machine contract for native comparison/repair BEFORE final expert HIL."""
import hashlib
from pathlib import Path
def check(report, graph_hash, root):
    errors=[];pending=[];root=Path(root).resolve()
    if report.get('graph_sha256')!=graph_hash:errors.append('comparison is stale for graph')
    if report.get('rounds_completed',0)<1:pending.append('native comparison round missing')
    if not report.get('families'):pending.append('source issue families not classified')
    if not report.get('native_comparisons'):pending.append('native comparison evidence missing')
    for item in report.get('native_comparisons',[]):
        p=(root/item['path']).resolve()
        if not p.is_relative_to(root)or not p.is_file():errors.append('missing/unsafe comparison evidence');continue
        if hashlib.sha256(p.read_bytes()).hexdigest()!=item.get('sha256'):errors.append('comparison evidence hash mismatch')
    for family in report.get('families',[]):
        if family.get('status')not in ('resolved','source_ambiguity'):pending.append('algorithm family not consumed: '+family.get('id','unknown'))
        if not family.get('source_handles')or not family.get('disposition'):errors.append('family lacks source evidence/disposition')
    if report.get('algorithm_blockers'):pending.extend(report['algorithm_blockers'])
    if report.get('unclassified_terminal_count',0)>0:pending.append('unclassified terminals cannot be transferred to experts')
    return {'status':'failed'if errors else 'pending'if pending else 'completed','errors':errors,'pending':pending,'hil_ready':not errors and not pending}
