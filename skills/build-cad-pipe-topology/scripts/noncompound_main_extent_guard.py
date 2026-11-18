"""Exclude unresolved projected multi-pipe carriers before main-length reuse."""
from compound_pipe_label_evidence import collect as declarations
from compound_carrier_members import carrier_risks


def barriers(doc,graph,source_hash):
    native=declarations(doc,source_hash)
    if not native['records']:
        return dict(status='not_applicable_no_native_compound_declarations',corridors=[])
    return carrier_risks(doc,graph,source_hash)


def check(row,proof):
    affected=[]
    for corridor in proof['corridors']:
        hits=[r for r in corridor['edges']if r['edge_id']in row['plan_edges']]
        if hits:affected.append(dict(source_LINE=corridor['source_LINE'],edges=hits))
    if affected:
        raise ValueError('compound_carrier_requires_its_member_identity_not_scalar_main_extent')
