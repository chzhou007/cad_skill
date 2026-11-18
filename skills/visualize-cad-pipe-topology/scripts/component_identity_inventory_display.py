"""Display canonical component names from an explicitly replayed identity change.

The immutable topology may retain historical inventory labels. Only a complete
closed source identity permutation plus original/current component CSV rows can
rename that display inventory. Counts, edge ownership and source graph stay put.
"""
import collections,copy

MODE='source_proved_component_identity_display_inventory_v1'

def normalize(graph,instances,graph_hash,component_hash):
    if graph.get('sourceComponentInventoryDisplayEvidence'):raise ValueError('component identity display normalization already applied')
    identity=graph.get('sourceExplodedCaptionIdentity',{});aliases=identity.get('aliases',{})
    if not aliases:return copy.deepcopy(graph),None
    if (identity.get('mode')!='native_exploded_equipment_caption_permutation_v1'
        or set(aliases)!=set(aliases.values())or len(set(aliases.values()))!=len(aliases)
        or identity.get('source_geometry_changed')is not False or identity.get('connections_changed')is not False
        or identity.get('human_accepted')is not False or not graph_hash or not component_hash):
        raise ValueError('component inventory lacks its original closed source identity proof')
    migrations={};expected=collections.Counter()
    for row in instances:
        eid=row['edge_id'];name=row['device_name'];expected[eid,name]+=1
        old_owner=row.get('original_owner_equipment');old_name=row.get('original_device_name')
        if old_owner not in aliases:
            # Historical repairs can retain older names of their own. Their
            # current names still have to match the unchanged raw inventory;
            # this adapter does not reinterpret those independent repairs.
            continue
        if (row.get('owner_equipment')!=aliases[old_owner]or not isinstance(old_name,str)
            or not old_name.startswith(old_owner+'/')or name!=aliases[old_owner]+old_name[len(old_owner):]
            or (eid,old_name)in migrations):
            raise ValueError('original/current component identity row differs or repeats')
        migrations[eid,old_name]=name
    out=copy.deepcopy(graph);used=set();records=[]
    for edge in out['edges']:
        for item in edge.get('equipment_inventory',[]):
            before=item.get('device_names',[]);after=[]
            if len(before)!=int(item['count']):raise ValueError('original inventory names and count differ')
            for name in before:
                key=(edge['edge_id'],name)
                if key in migrations:
                    if key in used:raise ValueError('component identity inventory repeated on one edge')
                    used.add(key);after.append(migrations[key]);records.append(dict(edge_id=edge['edge_id'],original_name=name,current_name=migrations[key]))
                else:after.append(name)
            item['device_names']=after
    if used!=set(migrations):raise ValueError('component identity CSV has no exact original inventory witness')
    actual=collections.Counter((e['edge_id'],name)for e in out['edges']for item in e.get('equipment_inventory',[])for name in item.get('device_names',[]))
    if actual!=expected:raise ValueError('canonical display names and current component audit differ')
    audit=dict(mode=MODE,input_graph_sha256=graph_hash,component_csv_sha256=component_hash,identity_aliases=copy.deepcopy(aliases),records=records,
        topology_or_source_geometry_changed=False,component_counts_or_edge_assignments_changed=False,source_graph_mutated=False,human_accepted=False)
    out['sourceComponentInventoryDisplayEvidence']=audit
    return out,audit
