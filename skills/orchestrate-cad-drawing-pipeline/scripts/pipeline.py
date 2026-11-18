"""CAD plans, contract checks and explicit hash-bound batch execution.

Legacy plan/validate remain read-only coordination. Use batch for staged owner
execution, batch-release for a source-bound release recipe, and actions for
bounded discovery of both argparse and historical dispatched commands.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from source_comparison_gate import check as check_comparison

FAMILIES={
    'schedule':{'parameters'},
    'plant_schematic':{'parameters','topology','visualization'},
    'outdoor_plan':{'parameters','topology','architecture','visualization'},
    'ceiling_plan':{'parameters','topology','architecture','visualization'},
    'isometric':{'parameters','topology','visualization'},
    'architectural_support':{'architecture'},
}
OWNERS={'source':'orchestrate-cad-drawing-pipeline','parameters':'build-cad-pipe-topology',
        'topology':'build-cad-pipe-topology','architecture':'extract-cad-building-context',
        'source_comparison':'build-cad-pipe-topology','visualization':'visualize-cad-pipe-topology'}
STATES={'completed','not_applicable','pending','failed'}
ROLES={'source':{'inventory','parse_issues'},'parameters':{'parameter_library','parameter_bindings','audit'},
       'topology':{'graph','nodes','edges','ports','components','audit','quality'},
       'architecture':{'building_context','building_svg','audit','quality'},
       'source_comparison':{'comparison','audit'},
       'visualization':{'viewer','pair','quality','audit'}}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,data):Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')

def applicable(t):
    active=set(FAMILIES.get(t['family'],set()))|{'source'};tags=set(t['tags'])
    if 'architecture'in tags:active.add('architecture')
    if tags & {'parameters','equipment'}:active.add('parameters')
    if 'pipe'in tags:active.update(['parameters','topology','visualization'])
    if 'topology'in active:active.add('source_comparison')
    return active if t['family']in FAMILIES else set(OWNERS)

def plan(config,output):
    config=Path(config).resolve();output=Path(output).resolve();cfg=read(config)
    if output.exists():raise ValueError('Choose a new output directory')
    if not cfg.get('project_id') or not cfg.get('tasks'):raise ValueError('Project and tasks required')
    tasks=[];ids=set()
    for t in cfg['tasks']:
        tid=t['task_id']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',tid) or tid in ids:raise ValueError('Invalid/duplicate task ID')
        ids.add(tid)
        if not t.get('evidence') or not isinstance(t.get('tags'),list):raise ValueError('Family evidence and tag list required')
        source=(config.parent/t['source']).resolve()
        if not source.is_file():raise ValueError('Missing source: '+str(source))
        family=t['family'];known=family in FAMILIES;active=applicable(t)
        stages={}
        for name,owner in OWNERS.items():
            deps=[] if name=='source' else ['source']
            if name=='topology':deps.append('parameters')
            if name=='source_comparison':deps.extend(x for x in ('parameters','topology','architecture')if x in active)
            if name=='visualization':deps.extend(x for x in ('parameters','topology','architecture','source_comparison')if x in active)
            required=name in active
            stages[name]={'owner':owner,'required':required,'status':'pending' if required else 'not_applicable',
                          'reason':'Await stage execution' if required else 'Excluded by evidence-backed family/tags',
                          'evidence':t['evidence'],'depends_on':deps,'artifacts':[]}
        tasks.append({'schema_version':1,'pipeline_version':'1.1.5','task_id':tid,'source':str(source),
                      'source_sha256':sha(source),'family':family,'tags':t['tags'],'family_evidence':t['evidence'],
                      'routing_status':'completed' if known else 'pending','stages':stages,
                      'review':{'scope':'this_task_only','confirmation':None}})
    profiles=[]
    for value in cfg.get('profile_files',[]):
        p=(config.parent/value).resolve();profiles.append({'path':str(p),'sha256':sha(p)})
    output.mkdir(parents=True)
    write(output/'configuration.json',cfg)
    for t in tasks:
        folder=output/t['task_id'];folder.mkdir();write(folder/'task-plan.json',t)
    code_locks=[];skill_root=Path(__file__).resolve().parents[2]
    for owner in sorted(set(OWNERS.values())):
        base=skill_root/owner
        for p in sorted(base.rglob('*')):
            if p.is_file()and '__pycache__'not in p.parts and (p.name=='SKILL.md'or ('scripts'in p.relative_to(base).parts or 'assets'in p.relative_to(base).parts)and p.suffix in ('.py','.js','.mjs','.html','.css','.json')):
                code_locks.append({'path':str(p),'sha256':sha(p)})
    manifest={'schema_version':1,'pipeline_version':'1.1.5','project_id':cfg['project_id'],
              'config_sha256':sha(config),'frozen_config_sha256':sha(output/'configuration.json'),'profile_locks':profiles,'tasks':[t['task_id']for t in tasks],
              'source_locks':{t['task_id']:{'path':t['source'],'sha256':t['source_sha256']}for t in tasks},'implementation_locks':code_locks,
              'execution':'planned_only','human_review':'unconfirmed'}
    write(output/'batch-plan.json',manifest);return manifest

def validate(run):
    run=Path(run).resolve();batch=read(run/'batch-plan.json');results=[]
    if sha(run/'configuration.json')!=batch['frozen_config_sha256']:raise ValueError('Frozen configuration changed')
    cfg=read(run/'configuration.json');expected={t['task_id']:t for t in cfg['tasks']}
    if len(batch['tasks'])!=len(expected)or set(batch['tasks'])!=set(expected):raise ValueError('Batch tasks differ from frozen configuration')
    for lock in batch.get('profile_locks',[])+batch.get('implementation_locks',[]):
        if not Path(lock['path']).is_file()or sha(lock['path'])!=lock['sha256']:raise ValueError('Profile/implementation lock mismatch: '+lock['path'])
    for tid in batch['tasks']:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',tid):raise ValueError('Unsafe task ID')
        folder=run/tid;t=read(folder/'task-plan.json');errors=[];pending=[];claimed={};coordinates=[]
        original=expected[tid];active=applicable(original)
        locked=batch['source_locks'][tid]
        if t['source']!=locked['path']or t['source_sha256']!=locked['sha256']:errors.append('Receipt source differs from frozen input')
        if t.get('family')!=original['family']or t.get('tags')!=original['tags']:errors.append('Routing changed without new plan')
        if t['task_id']!=tid:errors.append('Task identity mismatch')
        if not Path(t['source']).is_file()or sha(t['source'])!=t['source_sha256']:errors.append('Source changed')
        if original['family']not in FAMILIES or t.get('routing_status')!='completed':pending.append('Unresolved family routing')
        if set(t['stages'])!=set(OWNERS):errors.append('Missing or unexpected stage')
        for name,s in t['stages'].items():
            status=s.get('status')
            if name not in OWNERS or s.get('owner')!=OWNERS[name]:errors.append(name+': wrong owner')
            deps=[]if name=='source'else ['source']
            if name=='topology':deps.append('parameters')
            if name=='source_comparison':deps.extend(x for x in ('parameters','topology','architecture')if x in active)
            if name=='visualization':deps.extend(x for x in ('parameters','topology','architecture','source_comparison')if x in active)
            if s.get('depends_on')!=deps:errors.append(name+': altered dependencies')
            if s.get('required')!=(name in active):errors.append(name+': altered applicability')
            if status not in STATES:errors.append(name+': invalid state')
            if not s.get('reason')or not s.get('evidence'):errors.append(name+': missing reason/evidence')
            if status=='failed':errors.append(name+': stage failed')
            if s.get('required')and status!='completed':pending.append(name+': incomplete')
            if status!='completed':continue
            if s.get('task_id')!=tid or s.get('source_sha256')!=t['source_sha256']:errors.append(name+': receipt identity mismatch')
            if not s.get('artifacts'):errors.append(name+': completed without artifacts')
            for dep in s.get('depends_on',[]):
                if dep not in t['stages']or t['stages'][dep]['status']!='completed':errors.append(name+': unmet dependency '+dep)
            if name=='source_comparison'and not any(a.get('role')=='comparison'for a in s.get('artifacts',[])):errors.append('Missing comparison gate report')
            for a in s.get('artifacts',[]):
                p=(folder/a['path']).resolve()
                if not p.is_relative_to(folder.resolve()):errors.append(name+': artifact outside task');continue
                if p in claimed:errors.append(name+': duplicate artifact writer '+claimed[p])
                claimed[p]=name
                if a.get('role')not in ROLES.get(name,set()):errors.append(name+': invalid artifact role')
                if not p.is_file()or sha(p)!=a.get('sha256'):errors.append(name+': artifact hash mismatch')
                if name=='source_comparison'and a.get('role')=='comparison'and p.is_file():
                    graphs=[a for a in t['stages']['topology']['artifacts']if a.get('role')=='graph']
                    graph_path=(folder/graphs[0]['path']).resolve() if len(graphs)==1 else folder/'missing-unique-graph'
                    check=check_comparison(read(p),graphs[0]['sha256']if len(graphs)==1 else None,folder,graph_path)
                    errors.extend(check['errors']);pending.extend(check['pending'])
                if a.get('role')in ('graph','building_context'):
                    c=a.get('coordinate_contract',{})
                    if c.get('frame')!='WCS'or not c.get('units')or c.get('source_sha256')!=t['source_sha256']:errors.append(name+': invalid WCS contract')
                    coordinates.append(c)
        if coordinates and any(c!=coordinates[0]for c in coordinates):errors.append('Coordinate contracts differ')
        results.append({'task_id':tid,'status':'failed'if errors else 'pending'if pending else 'completed','errors':errors,'pending':pending})
    status='failed'if any(t['errors']for t in results)else 'pending'if any(t['pending']for t in results)else 'completed'
    return {'status':status,'tasks':results,'scope':'Artifact contracts only; no physical or human attestation'}

def validate_crossview(mapping_run,plan_graph,iso_graph):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from confirm_crossview_paths import verify_output
    mapping=verify_output(mapping_run)
    if mapping['plan_graph_sha256']!=sha(plan_graph) or mapping['iso_graph_sha256']!=sha(iso_graph):raise ValueError('cross-view mapping stale for current local graph')
    if mapping.get('status')!='confirmed_path_correspondence_attributes_pending' or not mapping.get('records') or mapping.get('local_graphs_mutated') is not False or mapping.get('human_accepted') is not False:raise ValueError('unsupported cross-view mapping state')
    return dict(status='pending',path_correspondence='native_replayed',mapped_paths=len(mapping['records']),
        plan_graph_sha256=sha(plan_graph),iso_graph_sha256=sha(iso_graph),
        pending=['attribute segment extents and source annotation attribution require validation'],
        local_scope=mapping['local_scope'],human_accepted=False,hil_ready=False)


def validate_anchored_floor_main_attributes(attribute_run):
    """Independently replay DN/XY; conflicts are explicit pending source scopes."""
    import math,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from anchored_floor_main_plan_attributes import verify_output,MODE
    data=verify_output(attribute_run)
    if data.get('mode')!=MODE or any(data.get(k) is not False for k in ('local_graphs_mutated','physical_values_fused','human_accepted','hil_ready')):
        raise ValueError('unsupported floor main attribute state')
    rows=data.get('records',[])
    if not rows or len({r['mapping_id'] for r in rows})!=len(rows) or len({tuple(r['plan_edges']) for r in rows})!=len(rows):
        raise ValueError('main attribute mappings missing or duplicated')
    conflicts=[];known=0;inline=0
    for row in rows:
        dn=row['diameter'];metric=row['horizontal_projection'];value=dn['nominal_mm'];mm=metric['value_mm']
        if (row.get('floor')!=data['floor'] or row.get('system') not in ('supply','return') or len(row['plan_edges'])!=1 or len(row['iso_edges'])!=1
            or dn.get('edge_id')!=row['plan_edges'][0] or dn.get('system')!=row['system'] or not metric.get('pieces')
            or isinstance(mm,bool) or not isinstance(mm,(int,float)) or not math.isfinite(mm) or mm<=0
            or row.get('installed_whole_edge_length_mm') is not None or row.get('physical_ports_verified') is not False or row.get('human_accepted') is not False
            or metric.get('installed_whole_edge_length_mm') is not None or metric.get('unshown_connection_length_mm') is not None):
            raise ValueError('main attribute scope or physical-length claim differs')
        if value is None:
            if dn.get('status') not in ('conflict','unresolved'):raise ValueError('unknown DN status differs')
            conflicts.append(dict(mapping_id=row['mapping_id'],plan_edge=dn['edge_id'],status=dn['status'],lineage=dn['lineage']))
        elif (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0
              or dn.get('status') not in ('direct_plan_DN','T_inherited_plan_DN') or not dn.get('lineage')):
            raise ValueError('known main DN lacks valid native inheritance')
        else:known+=1
        if row.get('inline_interiors_unknown') is True:
            inline+=1
            if metric.get('joint_graphic_spans_added') is not False or metric.get('inline_joint_interior_length_mm') is not None:
                raise ValueError('inline drawing span became a physical length')
    if (data.get('known_DN_records')!=known or data.get('unresolved_DN_records')!=len(conflicts)
        or data.get('inline_length_incomplete_records')!=inline):raise ValueError('main attribute summary differs')
    return dict(status='pending',source_replay='native_floor_main_DN_XY_independently_reconstructed',floor=data['floor'],
        mapped_main_paths=len(rows),known_DN_records=known,unresolved_DN_records=len(conflicts),DN_pending_scopes=conflicts,
        native_XY_records=len(rows),inline_length_incomplete_records=inline,source_sha256=data['source_sha256'],graph_sha256=data['graph_sha256'],
        protected_prior_main_values=len(data['preserved_main_value_comparisons']),human_accepted=False,hil_ready=False,
        pending=['Resolve explicit DN conflicts at their source stage; then validate complete-parent fusion, source comparison, viewer and HIL'])


def validate_network_named_lower_approaches(mapping_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from match_network_named_lower_approaches import verify_output,MODE
    data=verify_output(mapping_run);rows=data.get('records',[])
    if (data.get('mode')!=MODE or data.get('status')!='source_checked_network_named_lower_approaches_attributes_pending'
        or any(data.get(k) is not False for k in ('local_graphs_mutated','physical_values_fused','physical_ports_verified','human_accepted','hil_ready'))
        or data.get('DN_values_assigned')!=0 or data.get('physical_lengths_assigned')!=0 or len(rows)!=2 or len({r['mapping_id'] for r in rows})!=2
        or len({tuple(r['plan_edges']) for r in rows})!=2 or len({tuple(r['iso_edges']) for r in rows})!=2
        or {r['system'] for r in rows}!={'supply','return'}):raise ValueError('unsupported named-network approach result')
    for row in rows:
        scopes=row['iso_segment_scopes']
        if (row.get('kind')!='network_anchored_named_lower_floor_approach' or row['floor']!=data['floor'] or len(row['plan_edges'])!=1 or len(row['iso_edges'])!=1
            or len(scopes)!=1 or scopes[0].get('whole_local_edge') is not False or scopes[0]['edge_id']!=row['iso_edges'][0] or scopes[0]['path_index']!=0
            or scopes[0]['segment_indices']!=list(range(len(scopes[0]['segment_indices']))) or not scopes[0]['segment_indices']
            or scopes[0]['scope_paths'][0][-1]!=row['retained_vertical_scope']['scope_points'][0]
            or row['retained_vertical_scope']['floor_pair']!=[data['floor'],data['floor']+1]
            or scopes[0]['segment_indices'][-1]+1!=row['retained_vertical_scope']['segment_index']
            or row.get('graphic_circle_radius_added_to_length') is not False or row.get('axis_bend_is_attribute_limit_not_new_physical_node') is not True
            or any(row.get(k) is not False for k in ('whole_axis_DN_assigned','whole_axis_length_assigned','physical_port_verified','human_accepted'))
            or row.get('physical_length_mm') is not None or not row.get('independent_adjoining_main_mapping_id')):raise ValueError('named-network prefix scope or unknown values differ')
    return dict(status='pending',path_correspondence='native_network_named_lower_approaches_replayed',mapped_approaches=len(rows),floor=data['floor'],
        graph_sha256=data['graph_sha256'],source_sha256=data['source_sha256'],physical_values_assigned=0,human_accepted=False,hil_ready=False,
        pending=['Rebuild plan DN/metric scopes and compose exact horizontal prefixes; preserve vertical values, unknown mixed-edge lengths and human acceptance'])


def validate_native_external_destinations(evidence_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from native_external_pipe_destination import verify_output,MODE
    data=verify_output(evidence_run);rows=data.get('records',[])
    if (data.get('mode')!=MODE or data.get('status')!='source_declared_destinations_not_hydraulic_connection'
        or any(data.get(k) is not False for k in ('common_marker_creates_pipe_connection','graph_mutated','human_accepted','hil_ready'))
        or any(data.get(k)!=0 for k in ('nodes_merged','new_connections_added','physical_values_assigned'))
        or len(rows)<2 or len({r['node_id'] for r in rows})!=len(rows) or len({r['identifier'] for r in rows})!=len(rows)
        or len({r['source_line_handle'] for r in rows})!=len(rows)):raise ValueError('unsupported external destination evidence')
    for row in rows:
        if (row.get('destination')!=data.get('destination') or row.get('destination_status')!='source_declared_external_destination'
            or row.get('system') not in ('supply','return') or row.get('physical_length_mm') is not None
            or any(row.get(k) is not False for k in ('whole_edge_DN_verified','physical_external_connection_verified','physical_port_verified','human_accepted'))):
            raise ValueError('external destination cannot claim a physical connection or whole pipe value')
    return dict(status='pending',source_replay='native_external_destination_annotation_replayed',named_frontiers=len(rows),destination=data['destination'],
        source_sha256=data['source_sha256'],graph_sha256=data['graph_sha256'],nodes_merged=0,new_connections_added=0,physical_values_assigned=0,human_accepted=False,hil_ready=False,
        pending=['Known source destination does not prove external hydraulic connectivity; graph/port semantics, cross-view paths and HIL remain separate'])


def validate_network_named_lower_plan_attributes(attribute_run):
    import math,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from network_named_lower_plan_attributes import verify_output,MODE
    data=verify_output(attribute_run);rows=data.get('records',[])
    if (data.get('mode')!=MODE or data.get('status')!='source_checked_network_named_lower_plan_DN_XY_not_fused'
        or any(data.get(k) is not False for k in ('local_graphs_mutated','physical_values_fused','physical_ports_verified','human_accepted','hil_ready'))
        or data.get('installed_lengths_assigned')!=0 or len(rows)!=2 or len({r['mapping_id'] for r in rows})!=2 or {r['system'] for r in rows}!={'supply','return'}):raise ValueError('unsupported named-network plan attribute state')
    known=0
    for row in rows:
        d=row['diameter'];m=row['horizontal_projection'];value=d['nominal_mm'];mm=m['value_mm']
        if (len(row['plan_edges'])!=1 or len(row['iso_edges'])!=1 or d['edge_id']!=row['plan_edges'][0] or d['system']!=row['system']
            or d.get('scope')!='native_plan_drawn_pipe_paths_only' or not m.get('pieces') or isinstance(mm,bool) or not isinstance(mm,(int,float)) or not math.isfinite(mm) or mm<=0
            or any(row.get(k) is not False for k in ('whole_axis_DN_selected','whole_axis_DN_assigned','physical_port_verified','plan_glyph_radius_added_to_length','human_accepted'))
            or row.get('whole_axis_physical_length_mm') is not None or row.get('installed_whole_edge_length_mm') is not None
            or m.get('installed_whole_edge_length_mm') is not None or m.get('unshown_connection_length_mm') is not None):raise ValueError('named-network plan values cannot fill unknown mixed extents')
        if value is not None:
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0 or not d.get('lineage') or d.get('status') not in ('direct_plan_DN','T_inherited_plan_DN'):raise ValueError('named-network DN evidence missing')
            known+=1
        elif d.get('status') not in ('unknown','unresolved','conflict'):raise ValueError('unknown named-network DN status differs')
    if data.get('known_DN_records')!=known or data.get('unresolved_DN_records')!=len(rows)-known:raise ValueError('named-network attribute summary differs')
    return dict(status='pending',source_replay='native_network_named_lower_plan_DN_XY_replayed',prefix_records=len(rows),known_DN_records=known,unresolved_DN_records=len(rows)-known,
        source_sha256=data['source_sha256'],graph_sha256=data['graph_sha256'],human_accepted=False,hil_ready=False,
        pending=['Compose only mapped horizontal prefixes; preserve vertical sources, unknown installed lengths, source comparison and HIL'])


def validate_inline_joint_path_coverage(coverage_run):
    """Replay source pipes and qualified inline markers without assigning length."""
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from native_inline_joint_path_coverage import verify_output
    data=verify_output(coverage_run)
    if (data.get('mode')!='native_inline_joint_path_coverage_v1'
        or any(data.get(k) is not False for k in ('graph_mutated','human_accepted','hil_ready'))
        or data.get('new_connections_added')!=0 or data.get('physical_lengths_assigned')!=0):raise ValueError('unsupported native inline path audit')
    rows=data.get('records',[])
    if not rows or len({r['edge_id'] for r in rows})!=len(rows):raise ValueError('inline path records missing or duplicated')
    handles=[]
    for row in rows:
        if (row.get('status')!='native_pipe_and_inline_joint_chain_source_checked' or row.get('joint_spans_excluded_from_pipe_length') is not True
            or row.get('physical_length_mm') is not None or row.get('physical_ports_verified') is not False or row.get('human_accepted') is not False
            or not row.get('joints') or not row.get('native_path_proofs') or not row.get('private_ordered_pieces')):
            raise ValueError('inline chain cannot claim physical lengths or ports')
        for joint in row['joints']:
            if joint.get('edge_id')!=row['edge_id'] or joint.get('physical_length_mm') is not None or joint.get('physical_port_verified') is not False:
                raise ValueError('inline component scope differs')
            handles.append(joint['source_handle'])
    if len(handles)!=len(set(handles)):raise ValueError('inline component repeated across audited paths')
    return dict(status='pending',source_replay='passed',source_sha256=data['source_sha256'],graph_sha256=data['graph_sha256'],
        source_checked_inline_paths=len(rows),source_checked_inline_instances=len(handles),physical_lengths_assigned=0,
        human_accepted=False,hil_ready=False,pending=['Current full local topology, cross-view correspondence, attribute fusion and human acceptance remain separate checks'])


def validate_capped_marker_context(context_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from native_capped_marker_port_context import verify_output
    data=verify_output(context_run)
    return dict(status='pending',source_replay='passed',marker_groups=len(data['records']),
        separate_source_checked_ports=sum(len(r['members'])for r in data['records']),unresolved_caption_scopes=data['pending'],
        scope='Direct source annotation and exact existing port membership only',graph_mutated=False,
        human_accepted=False,hil_ready=False,pending=['Local topology, cross-view identity, full declared quantity population, physical lengths and HIL remain separate checks'])


def validate_full_batch_plan_fusion(fusion_run):
    from full_batch_plan_attribute_gate import check
    from pathlib import Path
    import hashlib,json
    root=Path(fusion_run);graph=root/'graph_with_edges.json';report=json.loads((root/'source-comparison-gate.json').read_text(encoding='utf8'))
    return check(root,report,hashlib.sha256(graph.read_bytes()).hexdigest(),graph)



def validate_compound_pipe_labels(evidence_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from compound_pipe_label_evidence import verify
    return verify(evidence_run)


def validate_anchor_bounded_main_attribute_refresh(bundle):
    import sys
    owner=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from refresh_anchor_bounded_main_attributes import verify
    return verify(bundle)


def validate_anchor_bounded_main_batch(batch_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_anchor_bounded_main_batch import verify_output
    result=verify_output(batch_run)
    return dict(status='pending',native_anchor_bounded_batch_replay='passed',counts=result['counts'],attribute_fusion_performed=False,human_accepted=False,pending=['Unmatched regions, off-path branches, attribute fusion and HIL remain separate'])


def _cycle_guard_owner_paths():
    import sys
    for name in('build-cad-pipe-topology','visualize-cad-pipe-topology'):
        p=Path(__file__).resolve().parents[2]/name/'scripts'
        if str(p)not in sys.path:sys.path.insert(0,str(p))

def validate_riser_header_interval_application(application_run):
    _cycle_guard_owner_paths()
    from riser_header_interval_application import verify_output,MODE
    r=verify_output(application_run)
    if r.get('mode')!=MODE or any(r.get(k)is not True for k in('independent_gate_ancestry_replayed','member_and_origin_native_sources_replayed','old_graphs_unchanged','all_horizontal_values_from_plan'))or any(r.get(k)!=0 for k in('vertical_values_assigned','installed_lengths_assigned','lower_terminal_identities_assigned'))or r.get('human_accepted')is not False:raise ValueError('unsupported riser interval adoption')
    for row in r['member_records']:
        if row.get('member_kind')=='riser'and row.get('complete_horizontal_centerline_mm')is not None:raise ValueError('riser symbol connector became measured physical length')
    return dict(status='pending',native_riser_header_interval_application='passed',counts=r['counts'],unresolved=r['pending'],human_accepted=False,pending=['Versioned viewer, source comparison, actual UI/CSV and HIL remain separate'])

def reconstruct_riser_header_interval_application(manifest,output):
    _cycle_guard_owner_paths()
    from riser_header_interval_application import produce
    produce(manifest,output);return validate_riser_header_interval_application(output)

def validate_riser_header_attribute_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_riser_header_attributes import verify
    return verify(bundle)

def validate_riser_header_provider_inventory(inventory_run):
    _cycle_guard_owner_paths()
    from riser_header_provider_inventory import verify_output,MODE
    r=verify_output(inventory_run)
    if r.get('mode')!=MODE or r.get('current_viewer_and_original_provider_inventory_replayed')is not True or r.get('member_namespaces_preserved')is not True or r.get('old_member_observations_prefix_unchanged')is not True or r.get('new_correspondences_assigned')!=0 or r.get('DN_or_length_values_assigned')!=0 or r.get('human_accepted')is not False:raise ValueError('unsupported adopted riser provider inventory')
    return dict(status='pending',riser_header_provider_inventory='passed',counts=r['counts'],human_accepted=False,pending=['Apply inherited providers before new discovery; residual source/metric scopes and HIL remain separate'])

def reconstruct_riser_header_provider_inventory(manifest,output):
    _cycle_guard_owner_paths()
    from riser_header_provider_inventory import produce
    produce(manifest,output);return validate_riser_header_provider_inventory(output)

def validate_equivalent_member_bounded_batch(batch_run):
    _cycle_guard_owner_paths()
    from rebuild_equivalent_member_bounded_batch import verify_output,MODE
    r=verify_output(batch_run)
    if r.get('mode')!=MODE or any(r.get(k)is not True for k in('complete_parent_rechecked','old_provider_observations_preserved'))or any(r.get(k)is not False for k in('source_graphs_mutated','physical_pipe_count_inferred','DN_used_for_mapping','unknown_length_filled_with_zero','human_accepted')):raise ValueError('unsupported equivalent member bounded batch')
    for row in r['records']:
        if row.get('nominal_mm')is not None or row.get('installed_length_mm')is not None or row.get('net_pipe_cut_length_mm')is not None or row.get('human_accepted')is not False:raise ValueError('member correspondence promoted an unqualified physical value')
        if row.get('complete_horizontal_centerline_mm')is not None and row.get('incomplete_reasons'):raise ValueError('incomplete source metric promoted to a complete length')
    return dict(status='pending',native_equivalent_member_bounded_batch='passed',counts=r['counts'],human_accepted=False,pending=['Apply existing DN owners; publish new correspondence/metric context and complete provider inventory; actual UI/CSV and HIL remain separate'])

def reconstruct_equivalent_member_bounded_batch(manifest,output):
    _cycle_guard_owner_paths()
    from rebuild_equivalent_member_bounded_batch import produce
    produce(manifest,output);return validate_equivalent_member_bounded_batch(output)

def validate_equivalent_member_plan_attributes(attribute_run):
    _cycle_guard_owner_paths()
    from apply_equivalent_member_plan_attributes import verify_output,MODE
    r=verify_output(attribute_run)
    if r.get('mode')!=MODE or any(r.get(k)is not True for k in('complete_source_batch_replayed','existing_complete_DN_provider_retained','specific_calibrated_and_F_readers_reapplied','all_horizontal_values_from_plan'))or any(r.get(k)is not False for k in('source_graphs_mutated','DN_used_for_mapping','physical_pipe_count_inferred','unknown_length_filled_with_zero','human_accepted'))or any(r.get(k)!=0 for k in('vertical_values_assigned','installed_lengths_assigned')):raise ValueError('unsupported equivalent member plan attribute application')
    return dict(status='pending',native_equivalent_member_plan_attributes='passed',counts=r['counts'],human_accepted=False,pending=['Publish versioned viewer and complete provider inventory; actual UI/CSV and HIL remain separate'])

def reconstruct_equivalent_member_plan_attributes(manifest,output):
    _cycle_guard_owner_paths()
    from apply_equivalent_member_plan_attributes import produce
    produce(manifest,output);return validate_equivalent_member_plan_attributes(output)

def validate_cohort_member_attribute_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_cohort_member_attributes import verify
    return verify(bundle)

def validate_recovered_component_index(index_run):
    _cycle_guard_owner_paths()
    from rebuild_recovered_component_index import verify_output
    r=verify_output(index_run)
    if r.get('complete_parent_and_native_inventory_replayed')is not True or r.get('pipe_graph_restoration_exact')is not True or r.get('new_correspondences_assigned')!=0 or r.get('physical_parameters_assigned')!=0 or r.get('human_accepted')is not False:raise ValueError('unsupported native recovered component index')
    return dict(status='pending',native_recovered_component_index='passed',components_added=r['component_rows_added'],human_accepted=False,pending=['Publish viewer index, recheck actual UI/CSV and inherit complete providers; technical pass is not HIL'])

def reconstruct_recovered_component_index(manifest,output):
    _cycle_guard_owner_paths()
    from rebuild_recovered_component_index import produce
    produce(manifest,output);return validate_recovered_component_index(output)

def validate_recovered_component_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_recovered_component_index import verify
    return verify(bundle)

def validate_recovered_component_provider_inventory(inventory_run):
    _cycle_guard_owner_paths()
    from recovered_component_provider_inventory import verify_output,MODE
    r=verify_output(inventory_run)
    if r.get('mode')!=MODE or any(r.get(k)is not True for k in('current_viewer_and_complete_original_inventory_replayed','all_prior_provider_observations_exact','all_prior_member_and_ordinary_junction_namespaces_exact','all_prior_attribute_frontiers_exact','current_rendered_component_profiles_requalified'))or r.get('new_correspondences_assigned')!=0 or r.get('DN_or_length_values_assigned')!=0 or r.get('human_accepted')is not False:raise ValueError('unsupported complete recovered component provider inventory')
    return dict(status='pending',complete_recovered_component_provider_inventory='passed',counts=r['counts'],human_accepted=False,pending=['Keep source ambiguities and human acceptance distinct from technical provider inheritance'])

def reconstruct_recovered_component_provider_inventory(manifest,output):
    _cycle_guard_owner_paths()
    from recovered_component_provider_inventory import produce
    produce(manifest,output);return validate_recovered_component_provider_inventory(output)

def validate_cohort_member_provider_inventory(inventory_run):
    _cycle_guard_owner_paths()
    from cohort_member_provider_inventory import verify_output,MODE
    r=verify_output(inventory_run)
    if r.get('mode')!=MODE or any(r.get(k)is not True for k in('current_viewer_and_complete_original_inventory_replayed','all_old_provider_observations_preserved','member_namespaces_preserved'))or r.get('human_accepted')is not False or r.get('new_correspondences_assigned')!=0 or r.get('DN_or_length_values_assigned')!=0:raise ValueError('unsupported complete cohort provider inheritance')
    return dict(status='pending',complete_cohort_member_provider_inventory='passed',counts=r['counts'],human_accepted=False,pending=['Actual viewer and HIL acceptance remain distinct from technical provider inheritance'])

def reconstruct_cohort_member_provider_inventory(manifest,output):
    _cycle_guard_owner_paths()
    from cohort_member_provider_inventory import produce
    produce(manifest,output);return validate_cohort_member_provider_inventory(output)

def validate_compound_carrier_atom_origins(origin_run):
    _cycle_guard_owner_paths()
    from rebuild_compound_carrier_atom_origins import verify_output,MODE
    r=verify_output(origin_run)
    if r.get('mode')!=MODE or r.get('source_or_graph_mutated')is not False or r.get('physical_members_assigned')!=0 or r.get('DN_or_lengths_assigned')!=0 or r.get('human_accepted')is not False:raise ValueError('unsupported native atom origin evidence')
    return dict(status='pending',native_compound_atom_origins='passed',counts=r['counts'],human_accepted=False,pending=['Refined origins do not assign members, correspondence, DN or physical lengths'])

def reconstruct_compound_carrier_atom_origins(manifest,output):
    _cycle_guard_owner_paths()
    from rebuild_compound_carrier_atom_origins import produce
    produce(manifest,output);return validate_compound_carrier_atom_origins(output)

def validate_native_balancing_valves(valve_run):
    _cycle_guard_owner_paths()
    from rebuild_native_balancing_valves import verify_output,MODE
    r=verify_output(valve_run)
    if r.get('mode')!=MODE or r.get('prior_components_unchanged')is not True or r.get('source_graph_unchanged')is not True or r.get('resistance_parameters_assigned')!=0 or r.get('published_graph_changed')is not False or r.get('human_accepted')is not False:raise ValueError('unsupported native balancing recovery')
    if r['components'][:r['counts']['prior_components']]+r['added_components']!=r['components']:raise ValueError('old component prefix changed')
    return dict(status='pending',native_balancing_valves='passed',counts=r['counts'],human_accepted=False,pending=['Requalify component-aware mappings and versioned viewer; unresolved native instances remain explicit'])

def reconstruct_native_balancing_valves(manifest,output):
    _cycle_guard_owner_paths()
    from rebuild_native_balancing_valves import produce
    produce(manifest,output);return validate_native_balancing_valves(output)


def validate_native_flange_contact_ownership(flange_run):
    _cycle_guard_owner_paths()
    from rebuild_native_flange_contact_ownership import verify_output,MODE
    result=verify_output(flange_run)
    if result.get('mode')!=MODE or any(result.get(key)is not True for key in ('original_native_owner_replayed','flange_population_complete','prior_components_unchanged','source_graph_unchanged','source_symbol_geometry_unchanged')) or any(result.get(key)is not False for key in ('published_graph_changed','component_aware_mapping_requalified','viewer_index_adopted','human_accepted')) or result.get('unknown_physical_parameters_filled')!=0:raise ValueError('unsupported native flange ownership state')
    count=result['counts']['prior_components']
    if result['components'][:count]+result['added_components']!=result['components']:raise ValueError('flange fallback component prefix changed')
    return dict(status='pending',native_flange_ownership='passed',counts=result['counts'],human_accepted=False,pending=['Requalify the affected scoped component profile and adopt the versioned viewer index; native inventory success alone is not publication'])


def reconstruct_native_flange_contact_ownership(manifest,output):
    _cycle_guard_owner_paths()
    from rebuild_native_flange_contact_ownership import produce
    produce(manifest,output);return validate_native_flange_contact_ownership(output)


def validate_native_ball_contact_owners(owner_run):
    _cycle_guard_owner_paths()
    from rebuild_native_ball_contact_owners import verify_output,MODE
    result=verify_output(owner_run)
    if result.get('mode')!=MODE or any(result.get(key)is not True for key in ('original_native_inventory_replayed','complete_source_family_scanned','all_component_ids_and_counts_conserved','equipment_membership_retained','source_graph_and_symbol_geometry_unchanged')) or any(result.get(key)is not False for key in ('published_graph_changed','related_mapping_confirmations_inherited','component_aware_mapping_requalified','viewer_index_adopted','human_accepted')) or result.get('physical_parameters_assigned')!=0:raise ValueError('unsupported native ball owner correction state')
    return dict(status='pending',native_ball_contact_owners='passed',counts=result['counts'],human_accepted=False,pending=['Requalify all affected old ordinary/member scopes and newly available native paths before viewer or attribute adoption'])


def reconstruct_native_ball_contact_owners(manifest,output):
    _cycle_guard_owner_paths()
    from rebuild_native_ball_contact_owners import produce
    produce(manifest,output);return validate_native_ball_contact_owners(output)


def validate_native_contact_application(application_run):
    _cycle_guard_owner_paths()
    from rebuild_native_contact_application import verify_output,MODE
    result=verify_output(application_run)
    if result.get('mode')!=MODE or any(result.get(key)is not True for key in ('complete_current_parent_replayed','native_owner_inventory_replayed','all_affected_old_scopes_requalified','pipe_graph_restoration_exact'))or any(result.get(key)is not False for key in ('source_graphs_mutated','DN_used_for_mapping','physical_pipe_count_inferred','related_confirmation_inherited','human_accepted'))or result.get('unknown_physical_parameters_filled')!=0:raise ValueError('unsupported complete contact application')
    return dict(status='pending',native_contact_application='passed',counts=result['counts'],human_accepted=False,pending=['Actual viewer/CSV, complete provider adoption and human acceptance remain separate'])


def reconstruct_native_contact_application(manifest,output):
    _cycle_guard_owner_paths()
    from rebuild_native_contact_application import produce
    produce(manifest,output);return validate_native_contact_application(output)


def validate_native_contact_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_native_contact_application import verify
    return verify(bundle)


def validate_contact_owner_provider_inventory(inventory_run):
    _cycle_guard_owner_paths()
    from contact_owner_provider_inventory import verify_output,MODE
    result=verify_output(inventory_run)
    if result.get('mode')!=MODE or result.get('current_viewer_and_complete_original_provider_replayed')is not True or result.get('all_prior_providers_and_member_namespaces_preserved')is not True or result.get('all_affected_old_scopes_requalified')is not True or result.get('human_accepted')is not False:raise ValueError('unsupported contact provider inheritance')
    return dict(status='pending',native_contact_complete_provider='passed',counts=result['counts'],human_accepted=False)


def reconstruct_contact_owner_provider_inventory(manifest,output):
    _cycle_guard_owner_paths()
    from contact_owner_provider_inventory import produce
    produce(manifest,output);return validate_contact_owner_provider_inventory(output)

def validate_legacy_named_provider_inventory(inventory_run):
    _cycle_guard_owner_paths()
    from legacy_named_provider_inventory import verify_output,MODE
    result=verify_output(inventory_run)
    required=('complete_original_contact_provider_replayed','current_native_legacy_scopes_replayed','all_old_provider_observations_preserved','all_old_pipe_attributes_and_components_preserved','all_legacy_interfaces_and_member_namespaces_separate')
    if result.get('mode')!=MODE or any(result.get(k)is not True for k in required)or result.get('DN_or_length_values_assigned')!=0 or result.get('new_correspondences_assigned')!=0 or result.get('human_accepted')is not False:raise ValueError('unsupported legacy named provider inheritance')
    return dict(status='pending',native_legacy_named_complete_provider='passed',counts=result['counts'],human_accepted=False)

def reconstruct_legacy_named_provider_inventory(manifest,output):
    _cycle_guard_owner_paths()
    from legacy_named_provider_inventory import produce
    produce(manifest,output);return validate_legacy_named_provider_inventory(output)

def validate_current_two_arm_routes(batch_run):
    from rebuild_current_two_arm_circle_routes import verify_output,MODE
    proof,provider,local,outputs=verify_output(batch_run)
    if proof.get('mode')!=MODE or any(proof.get(k)is not True for k in('complete_original_adopted_provider_replayed','current_local_topology_parents_replayed','all_current_pipe_circles_screened','original_two_arm_rule_reused','old_source_graphs_unchanged','all_old_provider_observations_preserved'))or any(proof.get(k)!=0 for k in('new_pipe_attribute_values','physical_Ts_added'))or proof.get('human_accepted')is not False or proof.get('whole_goal_complete')is not False:raise ValueError('unsupported current two-arm circle route reconstruction')
    from two_arm_affected_junctions import replay as replay_junctions
    junctions=replay_junctions(proof,outputs)
    return dict(status='pending',native_current_two_arm_routes='passed',counts=proof['counts'],affected_junctions=junctions['count'],human_accepted=False)

def reconstruct_current_two_arm_routes(manifest,output):
    from rebuild_current_two_arm_circle_routes import produce
    produce(manifest,output);return validate_current_two_arm_routes(output)

def validate_native_two_arm_viewer(bundle):
    from refresh_native_two_arm_routes import verify
    return verify(bundle)

def validate_source_stable_junctions(batch_run):
    from source_stable_junction_reapplication import verify_output,MODE
    proof=verify_output(batch_run)
    if proof.get('mode')!=MODE or any(proof.get(k)is not True for k in('all_current_plan_Ts_screened','original_and_current_native_rays_replayed'))or any(proof.get(k)is not False for k in('source_graphs_changed','source_configuration_changed','human_accepted','whole_goal_complete'))or any(proof.get(k)!=0 for k in('DN_values_assigned','length_values_assigned','mapping_values_assigned')):raise ValueError('unsupported source-stable junction configuration replay')
    return dict(status='pending',native_source_stable_junctions='passed',counts=proof['counts'],human_accepted=False)

def reconstruct_source_stable_junctions(manifest,output):
    from source_stable_junction_reapplication import produce
    produce(manifest,output);return validate_source_stable_junctions(output)

def validate_anchored_plan_metrics(batch_run):
    from reapply_anchored_plan_metrics import verify_output,MODE
    proof=verify_output(batch_run)
    if proof.get('mode')!=MODE or any(proof.get(k)is not True for k in('complete_original_provider_replayed','all_pending_horizontal_length_scopes_screened','original_metric_readers_reused','native_T_paths_components_and_joint_origins_replayed'))or any(proof.get(k)is not False for k in('source_graphs_mutated','component_owners_changed','human_accepted'))or any(proof.get(k)!=0 for k in('DN_values_assigned','vertical_values_assigned','installed_lengths_assigned')):raise ValueError('unsupported anchored plan metric batch')
    return dict(status='pending',native_anchored_metrics='passed',counts=proof['counts'],human_accepted=False)

def reconstruct_anchored_plan_metrics(manifest,output):
    from reapply_anchored_plan_metrics import produce
    produce(manifest,output);return validate_anchored_plan_metrics(output)

def validate_anchored_native_metric_viewer(bundle):
    from refresh_anchored_native_plan_metrics import verify
    return verify(bundle)

def validate_member_external_routes(batch_run):
    from rebuild_member_external_routes import verify_output,MODE
    proof,provider,local=verify_output(batch_run)
    if proof.get('mode')!=MODE or any(proof.get(k)is not True for k in('complete_current_provider_natively_replayed','complete_external_port_cohort_screened','new_native_routes_and_junctions_replayed','all_old_provider_observations_preserved'))or any(proof.get(k)is not False for k in('source_graphs_mutated','component_owners_changed','DN_used_for_mapping','global_plan_topology_complete','human_accepted'))or proof.get('physical_values_assigned')!=0:raise ValueError('unsupported external member route qualification')
    return dict(status='pending',native_external_member_routes='passed',counts=proof['counts'],provider_counts=provider['counts'],member_nodes=len(local['nodes']),member_edges=len(local['edges']),human_accepted=False)

def reconstruct_member_external_routes(manifest,output):
    from rebuild_member_external_routes import produce
    produce(manifest,output);return validate_member_external_routes(output)

def validate_third_arm_crossview_batch(batch_run):
    _cycle_guard_owner_paths()
    from rebuild_third_arm_crossview_batch import verify_output,MODE
    proof,provider=verify_output(batch_run)
    if proof.get('mode')!=MODE or any(proof.get(k)is not True for k in('complete_original_provider_replayed','current_native_T_and_path_scopes_replayed','all_old_provider_observations_preserved'))or any(proof.get(k)is not False for k in('source_graphs_mutated','DN_used_for_matching','component_owners_or_counts_changed','global_cycle_equivalence_claimed','human_accepted'))or proof.get('physical_values_assigned')!=0:raise ValueError('unsupported source-checked third-arm topology batch')
    return dict(status='pending',native_third_arm_topology='passed',counts=proof['counts'],provider_counts=provider['counts'],human_accepted=False)

def reconstruct_third_arm_crossview_batch(manifest,output):
    _cycle_guard_owner_paths()
    from rebuild_third_arm_crossview_batch import produce
    produce(manifest,output);return validate_third_arm_crossview_batch(output)


def validate_complementary_anchor_chains(batch_run):
    _cycle_guard_owner_paths()
    from rebuild_complementary_anchor_chains import verify_output,MODE
    proof,provider=verify_output(batch_run)
    if proof.get('mode')!=MODE or any(proof.get(k)is not True for k in('complete_original_provider_replayed','all_current_floor_regions_screened','all_current_plans_known_exploded_ball_population_screened'))or any(proof.get(k)is not False for k in('source_graphs_mutated','DN_used_for_matching','off_chain_terminal_identities_assigned','human_accepted'))or proof.get('physical_values_assigned')!=0:raise ValueError('unsupported native complementary-chain extension')
    return dict(status='pending',native_complementary_chains='passed',counts=proof['counts'],provider_counts=provider['counts'],human_accepted=False)


def reconstruct_complementary_anchor_chains(manifest,output):
    _cycle_guard_owner_paths()
    from rebuild_complementary_anchor_chains import produce
    produce(manifest,output);return validate_complementary_anchor_chains(output)


def validate_complementary_plan_attributes(batch_run):
    _cycle_guard_owner_paths()
    from reapply_complementary_plan_attributes import verify_output,MODE
    proof,provider=verify_output(batch_run)
    if proof.get('mode')!=MODE or any(proof.get(k)is not True for k in('complete_corrected_parent_replayed','original_complete_DN_parent_replayed','current_T_and_original_metric_owners_reused','all_current_complementary_intervals_screened','all_original_known_plan_DN_preserved','all_historical_main_roles_reapplied'))or any(proof.get(k)is not False for k in('source_graphs_mutated','source_components_reassigned','axis_values_used_for_horizontal_DN','human_accepted'))or any(proof.get(k)!=0 for k in('vertical_values_assigned','installed_lengths_assigned')):raise ValueError('unsupported complementary plan attribute application')
    return dict(status='pending',native_complementary_plan_attributes='passed',counts=proof['counts'],human_accepted=False)


def reconstruct_complementary_plan_attributes(manifest,output):
    _cycle_guard_owner_paths()
    from reapply_complementary_plan_attributes import produce
    produce(manifest,output);return validate_complementary_plan_attributes(output)


def validate_anchored_terminal_branches(batch_run):
    _cycle_guard_owner_paths()
    from reapply_anchored_terminal_branches import verify_output,MODE
    proof=verify_output(batch_run)
    if proof.get('mode')!=MODE or any(proof.get(k)is not True for k in('complete_published_parent_replayed','all_current_independent_main_third_arms_screened'))or any(proof.get(k)is not False for k in('graph_mutated','old_providers_replaced','human_accepted'))or any(proof.get(k)!=0 for k in('remote_equipment_identities_assigned','physical_ports_created','whole_axis_DN_assigned','whole_axis_lengths_assigned','vertical_values_assigned')):raise ValueError('unsupported anchored drawing branch reapplication')
    return dict(status='pending',native_anchored_terminal_branches='passed',counts=proof['counts'],viewer_adopted=False,human_accepted=False)


def reconstruct_anchored_terminal_branches(manifest,output):
    _cycle_guard_owner_paths()
    from reapply_anchored_terminal_branches import produce
    proof=produce(manifest,output)
    return dict(status='pending',native_anchored_terminal_branches='produced_independent_validation_required',counts=proof['counts'],viewer_adopted=False,human_accepted=False)


def validate_inherited_terminal_geometry(batch_run):
    _cycle_guard_owner_paths()
    from reapply_inherited_terminal_geometry import verify_output
    from refresh_inherited_terminal_geometry import source_guard
    proof=verify_output(batch_run);source_guard(proof)
    return dict(status='pending',native_inherited_terminal_geometry='passed',counts=proof['counts'],viewer_adopted=False,human_accepted=False)


def reconstruct_inherited_terminal_geometry(manifest,output):
    _cycle_guard_owner_paths()
    from reapply_inherited_terminal_geometry import produce
    proof=produce(manifest,output)
    return dict(status='pending',native_inherited_terminal_geometry='produced_independent_validation_required',counts=proof['counts'],viewer_adopted=False,human_accepted=False)


def validate_inherited_terminal_geometry_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_inherited_terminal_geometry import verify
    return verify(bundle)


def diagnose_axis_attribute_failures(manifest,output):
    _cycle_guard_owner_paths()
    from diagnose_axis_attribute_failures import produce
    r=produce(manifest,output)
    return dict(status='pending',attribute_failure_diagnosis='produced_source_floor_elevations_reexecuted_prior_DN_evidence_hash_checked',vertical_failure_groups=r['vertical_DN_failure_groups'],horizontal_unmatched=r['horizontal_unmatched'],horizontal_mapped_incomplete=r['horizontal_mapped_but_attributes_incomplete'],physical_values_assigned=0,human_accepted=False)


def reconstruct_axis_omission_vertical_DN(manifest,output):
    _cycle_guard_owner_paths()
    from axis_omission_vertical_DN import produce
    r=produce(manifest,output)
    return dict(status='pending',native_omission_inheritance='produced',counts=r['counts'],published=False,human_accepted=False)


def validate_axis_omission_vertical_DN(output):
    _cycle_guard_owner_paths()
    from axis_omission_vertical_DN import verify_output
    r=verify_output(output)
    return dict(status='pending',native_omission_inheritance='independent_replay_passed',counts=r['counts'],published=False,human_accepted=False)


def refresh_axis_omission_DN_viewer(parent,output,proof,templates,port):
    _cycle_guard_owner_paths()
    from refresh_omission_vertical_DN import refresh
    r=refresh(parent,output,proof,templates,port)
    return dict(status='pending',viewer_source_adoption='passed',bundle_id=r['bundle_id'],delta=r['delta'],actual_browser='pending',human_accepted=False)


def validate_axis_omission_DN_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_omission_vertical_DN import verify
    return verify(bundle)


def reconstruct_axis_continuous_source_DN(manifest,output):
    _cycle_guard_owner_paths()
    from axis_continuous_source_vertical_DN import produce
    r=produce(manifest,output)
    return dict(status='pending',native_continuous_source_DN='produced',counts=r['counts'],published=False,human_accepted=False)


def validate_axis_continuous_source_DN(output):
    _cycle_guard_owner_paths()
    from axis_continuous_source_vertical_DN import verify_output
    r=verify_output(output)
    return dict(status='pending',native_continuous_source_DN='independent_replay_passed',counts=r['counts'],published=False,human_accepted=False)


def refresh_continuous_axis_DN_viewer(parent,output,proof,templates,port):
    _cycle_guard_owner_paths()
    from refresh_continuous_axis_DN import refresh
    r=refresh(parent,output,proof,templates,port)
    return dict(status='pending',viewer_source_adoption='passed',bundle_id=r['bundle_id'],delta=r['delta'],actual_browser='pending',human_accepted=False)


def validate_continuous_axis_DN_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_continuous_axis_DN import verify
    return verify(bundle)


def refresh_modelspace_pair_main_DN_viewer(parent,output,proof,templates,port):
    _cycle_guard_owner_paths()
    from refresh_modelspace_pair_main_DN import refresh
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=refresh(parent,output,proof,templates,port)
    return dict(status='pending',viewer_source_adoption='passed',bundle_id=r['bundle_id'],delta=r['delta'],actual_browser='pending',human_accepted=False)


def validate_modelspace_pair_main_DN_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_modelspace_pair_main_DN import verify
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):return verify(bundle)


def refresh_multiline_main_T_DN_viewer(parent,output,proof,templates,port):
    _cycle_guard_owner_paths()
    from refresh_multiline_main_T_DN import refresh
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=refresh(parent,output,proof,templates,port)
    return dict(status='pending',viewer_source_adoption='passed',bundle_id=r['bundle_id'],delta=r['delta'],actual_browser='pending',human_accepted=False)


def validate_multiline_main_T_DN_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_multiline_main_T_DN import verify
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):return verify(bundle)


def refresh_typed_inline_attribute_DN_viewer(parent,output,proof,templates,port):
    _cycle_guard_owner_paths()
    from refresh_typed_inline_attribute_DN import refresh
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=refresh(parent,output,proof,templates,port)
    return dict(status='pending',viewer_source_adoption='passed',bundle_id=r['bundle_id'],delta=r['delta'],actual_browser='pending',human_accepted=False)


def validate_typed_inline_attribute_DN_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_typed_inline_attribute_DN import verify
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):return verify(bundle)


def refresh_plan_crossover_centreline_viewer(parent,output,proof,templates,port):
    _cycle_guard_owner_paths()
    from refresh_plan_crossover_centrelines import refresh
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=refresh(parent,output,proof,templates,port)
    return dict(status='pending',viewer_source_adoption='passed',bundle_id=r['bundle_id'],delta=r['delta'],actual_browser='pending',human_accepted=False)


def validate_plan_crossover_centreline_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_plan_crossover_centrelines import verify
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):return verify(bundle)


def refresh_axis_rule_vertical_DN_viewer(parent,output,proof,templates,port):
    _cycle_guard_owner_paths()
    from refresh_axis_rule_vertical_DN import refresh
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=refresh(parent,output,proof,templates,port)
    return dict(status='pending',viewer_source_adoption='passed',bundle_id=r['bundle_id'],delta=r['delta'],actual_browser='pending',human_accepted=False)


def validate_axis_rule_vertical_DN_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_axis_rule_vertical_DN import verify
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):return verify(bundle)


def refresh_nested_direct_axis_DN_viewer(parent,output,proof,templates,port):
    _cycle_guard_owner_paths()
    from refresh_nested_direct_axis_DN import refresh
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=refresh(parent,output,proof,templates,port)
    return dict(status='pending',viewer_source_adoption='passed',bundle_id=r['bundle_id'],delta=r['delta'],actual_browser='pending',human_accepted=False)


def validate_nested_direct_axis_DN_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_nested_direct_axis_DN import verify
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):return verify(bundle)


def refresh_nested_paired_axis_DN_viewer(parent,output,proof,templates,port):
    _cycle_guard_owner_paths()
    from refresh_nested_paired_axis_DN import refresh
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=refresh(parent,output,proof,templates,port)
    return dict(status='pending',viewer_source_adoption='passed',bundle_id=r['bundle_id'],delta=r['delta'],actual_browser='pending',human_accepted=False)


def validate_nested_paired_axis_DN_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_nested_paired_axis_DN import verify
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):return verify(bundle)


def reconstruct_inherited_air_vent_attributes(manifest,output):
    _cycle_guard_owner_paths()
    from reapply_air_vent_attribute_normalization import produce
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=produce(manifest,output)
    return dict(status='pending',inherited_air_vent_attributes='produced',counts=r['counts'],old_graph_and_components_preserved=True,physical_lengths_assigned=0,human_accepted=False)


def validate_inherited_air_vent_attributes(output):
    _cycle_guard_owner_paths()
    from reapply_air_vent_attribute_normalization import verify_output
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify_output(output)
    return dict(status='pending',inherited_air_vent_attributes='independent_replay_passed',counts=r['counts'],old_graph_and_components_preserved=True,physical_lengths_assigned=0,human_accepted=False)


def reconstruct_plan_crossover_centrelines(manifest,output):
    _cycle_guard_owner_paths()
    from reapply_plan_crossover_centerlines import produce
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=produce(manifest,output)
    return dict(status='pending',plan_crossover_centrelines='produced',counts=r['counts'],installed_lengths_assigned=0,human_accepted=False)

def validate_plan_crossover_centrelines(output):
    _cycle_guard_owner_paths()
    from reapply_plan_crossover_centerlines import verify_output
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify_output(output)
    return dict(status='pending',plan_crossover_centrelines='independent_native_replay_passed',counts=r['counts'],installed_lengths_assigned=0,human_accepted=False)

def reconstruct_modelspace_pair_main_DN(manifest,output):
    _cycle_guard_owner_paths()
    from reapply_modelspace_pair_main_DN import produce
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=produce(manifest,output)
    return dict(status='pending',modelspace_pair_main_DN='produced',counts=r['counts'],physical_lengths_assigned=0,human_accepted=False)


def validate_modelspace_pair_main_DN(output):
    _cycle_guard_owner_paths()
    from reapply_modelspace_pair_main_DN import verify_output
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify_output(output)
    return dict(status='pending',modelspace_pair_main_DN='independent_native_replay_passed',counts=r['counts'],physical_lengths_assigned=0,human_accepted=False)


def reconstruct_multiline_main_T_DN(manifest,output):
    _cycle_guard_owner_paths()
    from reapply_multiline_main_T_DN import produce
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=produce(manifest,output)
    return dict(status='pending',multiline_main_T_DN='produced',counts=r['counts'],physical_lengths_assigned=0,human_accepted=False)


def validate_multiline_main_T_DN(output):
    _cycle_guard_owner_paths()
    from reapply_multiline_main_T_DN import verify_output
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify_output(output)
    return dict(status='pending',multiline_main_T_DN='independent_native_replay_passed',counts=r['counts'],physical_lengths_assigned=0,human_accepted=False)


def reconstruct_typed_inline_attribute_DN(manifest,output):
    _cycle_guard_owner_paths()
    from reapply_typed_inline_attribute_DN import produce
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=produce(manifest,output)
    return dict(status='pending',typed_inline_attribute_DN='produced',counts=r['counts'],physical_lengths_assigned=0,human_accepted=False)


def validate_typed_inline_attribute_DN(output):
    _cycle_guard_owner_paths()
    from reapply_typed_inline_attribute_DN import verify_output
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify_output(output)
    return dict(status='pending',typed_inline_attribute_DN='independent_native_replay_passed',counts=r['counts'],physical_lengths_assigned=0,human_accepted=False)


def reconstruct_axis_main_T_DN(manifest,output):
    _cycle_guard_owner_paths()
    from reapply_axis_main_T_DN import produce
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=produce(manifest,output)
    return dict(status='pending',axis_main_T_DN='produced',counts=r['counts'],old_graph_and_components_preserved=True,physical_lengths_assigned=0,human_accepted=False)


def validate_axis_main_T_DN(output):
    _cycle_guard_owner_paths()
    from reapply_axis_main_T_DN import verify_output
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify_output(output)
    return dict(status='pending',axis_main_T_DN='independent_replay_passed',counts=r['counts'],old_graph_and_components_preserved=True,physical_lengths_assigned=0,human_accepted=False)


def reconstruct_nested_direct_axis_DN(manifest,output):
    _cycle_guard_owner_paths()
    from reapply_nested_direct_caption_DN import produce
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=produce(manifest,output)
    return dict(status='pending',nested_direct_axis_DN='produced',counts=r['counts'],old_graph_and_components_preserved=True,physical_lengths_assigned=0,human_accepted=False)


def validate_nested_direct_axis_DN(output):
    _cycle_guard_owner_paths()
    from reapply_nested_direct_caption_DN import verify_output
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify_output(output)
    return dict(status='pending',nested_direct_axis_DN='independent_replay_passed',counts=r['counts'],old_graph_and_components_preserved=True,physical_lengths_assigned=0,human_accepted=False)


def reconstruct_nested_paired_axis_DN(manifest,output):
    _cycle_guard_owner_paths()
    from reapply_nested_paired_caption_DN import produce
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=produce(manifest,output)
    return dict(status='pending',nested_paired_axis_DN='produced',counts=r['counts'],old_graph_and_components_preserved=True,physical_lengths_assigned=0,human_accepted=False)


def validate_nested_paired_axis_DN(output):
    _cycle_guard_owner_paths()
    from reapply_nested_paired_caption_DN import verify_output
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify_output(output)
    return dict(status='pending',nested_paired_axis_DN='independent_replay_passed',counts=r['counts'],old_graph_and_components_preserved=True,physical_lengths_assigned=0,human_accepted=False)


def validate_complementary_attribute_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_complementary_plan_attributes import verify
    return verify(bundle)

def validate_anchored_terminal_branch_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_anchored_terminal_branches import verify
    return verify(bundle)


def validate_compound_riser_header_members(member_run):
    _cycle_guard_owner_paths()
    from rebuild_compound_riser_header_members import verify_output,MODE
    r=verify_output(member_run)
    if r.get('mode')!=MODE or r.get('raw_graphs_unchanged')is not True or r.get('component_duplicated')is not False or r.get('whole_axis_values_assigned')!=0 or r.get('human_accepted')is not False:raise ValueError('unsupported riser member reconstruction')
    if r.get('scoped_member_edges')!=3*len(r['records'])or r.get('conditional_interval_candidates')!=2*len(r['records']):raise ValueError('incomplete reconstructed member graph')
    for row in r['records']:
        ids=[c for e in row['scoped_graph']['edges']for c in e['component_ids']]
        if len(ids)!=len(set(ids))or sorted(ids)!=row['component_ids_conserved']or row.get('gate_mapping_revalidation_required')is not True or row.get('lower_terminal_identity_selected')is not False:raise ValueError('member reconstruction escaped its conditional domain')
    return dict(status='pending',native_compound_riser_members='passed',scoped_member_edges=r['scoped_member_edges'],conditional_interval_candidates=r['conditional_interval_candidates'],unresolved=r['pending'],human_accepted=False,pending=['Revalidate independent gate anchors before adopting conditional intervals; lower terminal, attributes and publication remain separate'])

def reconstruct_compound_riser_header_members(manifest,output):
    _cycle_guard_owner_paths()
    from rebuild_compound_riser_header_members import produce
    produce(manifest,output);return validate_compound_riser_header_members(output)

def validate_cycle_carrier_guards(guard_run):
    _cycle_guard_owner_paths()
    from cycle_carrier_guards import verify_output,MODE
    r=verify_output(guard_run)
    if r.get('mode')!=MODE or r.get('original_compound_carrier_reader_reused')is not True or r.get('original_provider_and_riser_sources_independently_replayed')is not True or r.get('physical_lengths_assigned')!=0 or r.get('physical_member_ids_assigned')!=0 or r.get('human_accepted')is not False:raise ValueError('unsupported cycle carrier guards')
    if any(x.get('complete_physical_horizontal_length_mm')is not None or x.get('physical_correspondence_confirmed')is not False for x in r['records']):raise ValueError('carrier guard promoted physical values')
    return dict(status='pending',native_cycle_carrier_guards='passed',held_cycle_lengths=r['held_cycle_lengths'],held_riser_roles=r['held_riser_roles'],human_accepted=False,pending=['Prove member topology before applying physical mapping or lengths'])

def reconstruct_cycle_carrier_guards(manifest,output):
    _cycle_guard_owner_paths()
    from cycle_carrier_guards import produce
    produce(manifest,output);return validate_cycle_carrier_guards(output)

def validate_cycle_carrier_correction_viewer(bundle):
    _cycle_guard_owner_paths()
    from refresh_cycle_carrier_guards import verify
    return verify(bundle)

def validate_guarded_cycle_provider_inventory(inventory_run):
    _cycle_guard_owner_paths()
    from guarded_cycle_provider_inventory import verify_output,MODE
    r=verify_output(inventory_run)
    if r.get('mode')!=MODE or r.get('corrected_viewer_and_all_original_providers_replayed')is not True or r.get('physical_member_identity_required_before_reapplication')is not True or r.get('human_accepted')is not False:raise ValueError('unsupported guarded cycle providers')
    return dict(status='pending',guarded_cycle_provider_inventory='passed',counts=r['counts'],human_accepted=False,pending=['Use guarded physical anchors; retain graphic candidates for member reconstruction'])

def reconstruct_guarded_cycle_provider_inventory(manifest,output):
    _cycle_guard_owner_paths()
    from guarded_cycle_provider_inventory import produce
    produce(manifest,output);return validate_guarded_cycle_provider_inventory(output)

def validate_typed_cycle_riser_batch(riser_run):
    import sys
    p=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
    from rebuild_typed_cycle_riser_batch import verify_output,MODE
    r=verify_output(riser_run)
    if r.get('mode')!=MODE or r.get('current_complete_provider_inventory_independently_replayed')is not True or r.get('raw_graphs_unchanged')is not True or r.get('ordinary_and_riser_port_domains_separate')is not True or any(r.get(k)is not False for k in('DN_used_for_matching','coordinates_used_for_matching','ordinal_identities_assigned','human_accepted'))or r.get('physical_values_assigned')!=0:raise ValueError('unsupported typed cycle riser evidence')
    for floor in r.get('floors',{}).values():
        if any(x.get('individual_mapping_pending')is not True or x.get('attributes_assigned')is not False for x in floor.get('bounded_route_differences',[])):raise ValueError('bounded route promoted unresolved individual attributes')
    return dict(status='pending',native_typed_cycle_riser_batch='passed',counts=r['counts'],identity_scope='graphic_role_candidates_not_physical_member_confirmation',human_accepted=False,pending=['Apply compound member guards before physical mapping; unequal terminal routes, attributes, publication and HIL remain separate'])

def reconstruct_typed_cycle_riser_batch(manifest,output):
    import sys
    p=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
    from rebuild_typed_cycle_riser_batch import produce
    produce(manifest,output);return validate_typed_cycle_riser_batch(output)

def validate_cycle_gate_plan_lengths(metric_run):
    import sys
    scripts=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(scripts)not in sys.path:sys.path.insert(0,str(scripts))
    from cycle_gate_plan_lengths import verify_output,MODE
    r=verify_output(metric_run)
    if r.get('mode')!=MODE or r.get('cycle_correspondences_independently_replayed')is not True or r.get('original_metric_readers_reused')is not True or r.get('local_graphs_changed')is not False or any(r.get(k)!=0 for k in('DN_values_assigned','vertical_values_assigned','installed_lengths_assigned'))or r.get('human_accepted')is not False:raise ValueError('cycle metrics exceed their source scope')
    return dict(status='pending',native_cycle_gate_plan_lengths='passed',counts=r['counts'],human_accepted=False,pending=['DN conflicts, installed lengths, publication and HIL remain separate'])

def reconstruct_cycle_gate_plan_lengths(manifest,output):
    import sys
    scripts=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(scripts)not in sys.path:sys.path.insert(0,str(scripts))
    from cycle_gate_plan_lengths import produce
    produce(manifest,output);return validate_cycle_gate_plan_lengths(output)

def validate_graph_first_attribute_viewer(bundle):
    import sys
    scripts=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(scripts)not in sys.path:sys.path.insert(0,str(scripts))
    from refresh_graph_first_attributes import verify
    r=verify(bundle)
    if r.get('artifact_replay')!='passed'or r.get('human_accepted')is not False:raise ValueError('graph-first viewer did not independently replay')
    return r

def validate_graph_first_provider_inventory(inventory_run):
    import sys
    scripts=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(scripts)not in sys.path:sys.path.insert(0,str(scripts))
    from graph_first_provider_inventory import verify_output,MODE
    r=verify_output(inventory_run)
    if r.get('mode')!=MODE or r.get('current_viewer_and_complete_original_inventory_replayed')is not True or r.get('member_namespaces_preserved')is not True or r.get('new_correspondences_assigned')!=0 or r.get('DN_or_length_values_assigned')!=0 or r.get('human_accepted')is not False:raise ValueError('graph-first inventory changed qualified values or topology')
    return dict(status='pending',graph_first_provider_inventory='passed',counts=r['counts'],human_accepted=False,pending=['Apply inherited anchors to remaining scopes; source conflicts and HIL remain separate'])

def reconstruct_graph_first_provider_inventory(manifest,output):
    import sys
    scripts=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(scripts)not in sys.path:sys.path.insert(0,str(scripts))
    from graph_first_provider_inventory import produce
    produce(manifest,output);return validate_graph_first_provider_inventory(output)


def validate_anchored_cycle_gate_batch(cycle_run):
    import sys
    scripts=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(scripts)not in sys.path:sys.path.insert(0,str(scripts))
    from rebuild_anchored_cycle_gate_batch import verify_output,MODE
    r=verify_output(cycle_run)
    if r.get('mode')!=MODE or r.get('current_provider_inventory_independently_replayed')is not True or r.get('raw_graphs_unchanged')is not True or r.get('member_namespaces_preserved')is not True or r.get('interior_node_identities_assigned')is not False or r.get('DN_used_for_matching')is not False or r.get('coordinates_used_for_matching')is not False or r.get('shortest_path_used')is not False or r.get('physical_values_assigned')!=0 or r.get('human_accepted')is not False:raise ValueError('cycle gate batch exceeds its qualified topology scope')
    return dict(status='pending',native_anchored_cycle_gate_batch='passed',counts=r['counts'],human_accepted=False,pending=['Apply existing attribute owners only after source qualification; unpaired cycle interiors, viewer publication and HIL remain separate'])


def reconstruct_anchored_cycle_gate_batch(manifest,output):
    import sys
    scripts=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(scripts)not in sys.path:sys.path.insert(0,str(scripts))
    from rebuild_anchored_cycle_gate_batch import produce
    produce(manifest,output)
    return validate_anchored_cycle_gate_batch(output)


def validate_axis_unbranched_vertical_DN(dn_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_axis_unbranched_vertical_DN import verify_output,MODE
    r=verify_output(dn_run)
    if r.get('mode')!=MODE or any(r.get(k)is not True for k in('original_native_annotations_independently_replayed','original_direction_routing_independently_replayed','original_annotation_records_preserved','original_axis_graphs_unchanged','all_vertical_values_from11'))or r.get('horizontal_plan_attributes_changed')is not False or r.get('crossed_physical_Ts')!=0 or r.get('whole_edge_DN_assigned')!=0 or r.get('physical_lengths_assigned')!=0 or r.get('human_accepted')is not False:raise ValueError('unsupported native unbranched vertical DN proof')
    return dict(status='pending',native_axis_unbranched_vertical_DN='passed',counts=r['counts'],human_accepted=False,pending=['Publish only source-qualified vertical domains; ambiguous annotations, other source paths, physical lengths and HIL remain separate'])


def reconstruct_axis_unbranched_vertical_DN(manifest,output):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_axis_unbranched_vertical_DN import produce
    produce(manifest,output)
    return validate_axis_unbranched_vertical_DN(output)


def validate_alias_member_bridge_viewer(bundle):
    import sys
    viewer=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(viewer)not in sys.path:sys.path.insert(0,str(viewer))
    from refresh_alias_member_bridge_attributes import verify
    return verify(bundle)


def validate_bridge_aware_provider_inventory(inventory_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from bridge_aware_provider_inventory import verify_output,MODE
    r=verify_output(inventory_run)
    if r.get('mode')!=MODE or any(r.get(k)is not True for k in('current_bridge_viewer_native_replayed','complete_original_alias_inventory_replayed','ordinary_junction_mappings_unchanged'))or r.get('vertical_segments_routed_to_plan')!=0 or r.get('DN_or_length_values_assigned')!=0 or r.get('human_accepted')is not False:raise ValueError('unsupported complete bridge provider inventory')
    return dict(status='pending',native_bridge_aware_provider_inventory='passed',counts=r['counts'],human_accepted=False,pending=['All providers inherited; unresolved paths, physical inline length and HIL remain separate'])


def reconstruct_bridge_aware_provider_inventory(manifest,output):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from bridge_aware_provider_inventory import produce
    produce(manifest,output)
    return validate_bridge_aware_provider_inventory(output)


def validate_alias_member_inline_bridges(bridge_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_alias_member_inline_bridges import verify_output,MODE
    r=verify_output(bridge_run)
    if r.get('mode')!=MODE or any(r.get(k)is not True for k in('parent_alias_interfaces_independently_replayed','old_interface_records_retained','all_vertical_attributes_from11','source_drawing_graphs_unchanged','member_topology_rebuilt'))or r.get('original_component_assignments_mutated')is not False or r.get('whole_centerline_lengths_assigned')!=0 or r.get('installed_lengths_assigned')!=0 or r.get('human_accepted')is not False:raise ValueError('unsupported alias member inline bridge proof')
    return dict(status='pending',native_alias_member_inline_bridges='passed',counts=r['counts'],source_pending=r['pending'],human_accepted=False,pending=['Publish independently qualified bridge DN and pipe-only projections; inline physical lengths, external routes and HIL remain separate'])


def reconstruct_alias_member_inline_bridges(manifest,output):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_alias_member_inline_bridges import produce
    produce(manifest,output)
    return validate_alias_member_inline_bridges(output)


def validate_alias_member_interface_viewer(bundle):
    import sys
    viewer=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(viewer)not in sys.path:sys.path.insert(0,str(viewer))
    from refresh_alias_member_interface_attributes import verify
    return verify(bundle)


def validate_alias_aware_provider_inventory(inventory_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from alias_aware_provider_inventory import verify_output,MODE
    r=verify_output(inventory_run)
    if r.get('mode')!=MODE or r.get('current_alias_viewer_native_replayed')is not True or r.get('ordinary_junction_mappings_unchanged')is not True or r.get('vertical_segments_routed_to_plan')!=0 or r.get('DN_or_length_values_assigned')!=0 or r.get('human_accepted')is not False:raise ValueError('unsupported alias provider inventory')
    return dict(status='pending',native_alias_aware_provider_inventory='passed',counts=r['counts'],human_accepted=False,pending=['Inventory inherits proved members; unmatched paths and HIL remain separate'])


def reconstruct_alias_aware_provider_inventory(manifest,output):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from alias_aware_provider_inventory import produce
    produce(manifest,output)
    return validate_alias_aware_provider_inventory(output)


def validate_alias_member_circle_interfaces(interface_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_alias_member_circle_interfaces import verify_output,MODE
    r=verify_output(interface_run)
    if r.get('mode')!=MODE or r.get('confirmed_alias_member_cohort_native_replayed')is not True or r.get('original_local_graphs_mutated')is not False or r.get('ordinary_junction_mapping_extended')is not False or r.get('vertical_attributes_assigned_from_plan')!=0 or r.get('installed_lengths_assigned')!=0 or r.get('human_accepted')is not False:raise ValueError('unsupported confirmed alias member interface proof')
    return dict(status='pending',native_alias_member_interfaces='passed',counts=r['counts'],source_pending=r['pending'],human_accepted=False,pending=['Publish only qualified directional scopes; source drawing ends, external ports and HIL stay separate'])


def reconstruct_alias_member_circle_interfaces(manifest,output):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_alias_member_circle_interfaces import produce
    produce(manifest,output)
    return validate_alias_member_circle_interfaces(output)


def validate_bounded_main_complete_extents(extent_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_bounded_main_complete_extents import verify_output,MODE
    r=verify_output(extent_run)
    if r.get('mode')!=MODE or any(r.get(k)is not True for k in('current_provider_inventory_replayed','bounded_ancestor_native_replayed','selected_old_and_current_plan_scopes_exact','existing_correspondences_unchanged','DN_observations_preserved'))or r.get('local_graphs_mutated')is not False or r.get('installed_lengths_assigned')!=0 or r.get('human_accepted')is not False:raise ValueError('unsupported bounded complete extent proof')
    return dict(status='pending',native_bounded_complete_extents='passed',counts=r['counts'],DN_observations_preserved=True,human_accepted=False,pending=['Publish only qualified horizontal centrelines; other extents and HIL remain separate'])


def reconstruct_bounded_main_complete_extents(manifest,output):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_bounded_main_complete_extents import produce
    produce(manifest,output)
    return validate_bounded_main_complete_extents(output)


def validate_bounded_main_complete_extent_refresh(bundle):
    import sys
    owner=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from refresh_bounded_main_complete_extents import verify
    return verify(bundle)


def validate_qualified_crossview_provider_inventory(inventory_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from qualified_crossview_provider_inventory import verify_output,MODE
    r=verify_output(inventory_run)
    if r.get('mode')!=MODE or r.get('current_provider_artifact_replayed')is not True or r.get('ordered_owner_native_replayed')is not True or r.get('original_CAD_direction_replayed')is not True or r.get('local_graphs_mutated')is not False or r.get('new_correspondences_assigned')!=0 or r.get('DN_or_length_values_assigned')!=0 or r.get('vertical_segments_routed_to_plan')!=0 or r.get('human_accepted')is not False:raise ValueError('provider inventory exceeds its source-qualified discovery scope')
    return dict(status='pending',qualified_provider_inventory='passed',counts=r['counts'],new_correspondences_assigned=0,human_accepted=False,pending=['New candidate paths require native qualification; unknown DN, lengths and HIL remain separate'])


def reconstruct_qualified_crossview_provider_inventory(manifest,output):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from qualified_crossview_provider_inventory import produce
    produce(manifest,output)
    return validate_qualified_crossview_provider_inventory(output)


def validate_qualified_plan_scope_extension(scope_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_qualified_plan_scope_extension import verify_output,MODE
    result=verify_output(scope_run)
    if result.get('mode')!=MODE or result.get('specific_provider_reconstructed')is not True or result.get('source_graphs_mutated')is not False or result.get('axis_values_fused')is not False or result.get('physical_pipe_count_inferred')is not False or result.get('human_accepted')is not False or result['native_provider'].get('old_provider_receipt_accepted')is not False:raise ValueError('specific native source provider not reconstructed')
    return dict(status='pending',native_specific_plan_provider='passed',counts=result['counts'],axis_values_fused=False,human_accepted=False,pending=['Publish only qualified horizontal main scopes;branch and vertical attributes,conflicts and HIL remain separate'])


def reconstruct_qualified_plan_scope_extension(manifest,output):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_qualified_plan_scope_extension import produce
    produce(manifest,output)
    return validate_qualified_plan_scope_extension(output)


def validate_qualified_plan_scope_refresh(bundle):
    import sys
    owner=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from refresh_qualified_plan_scope_attributes import verify
    return verify(bundle)


def validate_ordered_owner_crossview(mapping_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_ordered_owner_crossview import verify_output,MODE
    result=verify_output(mapping_run)
    if result.get('mode')!=MODE or result.get('DN_used_for_mapping')is not False or result.get('local_graphs_mutated')is not False or result.get('attributes_fused')is not False or result.get('human_accepted')is not False:raise ValueError('unsupported new owner crossview evidence')
    return dict(status='pending',native_ordered_owner_crossview='passed',counts=result['counts'],attributes_fused=False,human_accepted=False,pending=['Publish qualified new plan runs on the axis;remaining mappings,vertical lengths and HIL stay separate'])


def reconstruct_ordered_owner_crossview(manifest,output):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_ordered_owner_crossview import produce
    produce(manifest,output)
    return validate_ordered_owner_crossview(output)


def validate_ordered_owner_plan_refresh(bundle):
    import sys
    owner=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from refresh_ordered_owner_plan_attributes import verify
    return verify(bundle)


def validate_ordered_sideview_owners(owner_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_ordered_sideview_owners import verify_output,MODE
    result=verify_output(owner_run)
    if result.get('mode')!=MODE or result.get('physical_lengths_assigned')!=0 or result.get('human_accepted')is not False or result.get('crossview_mapping_recomputed')is not False:raise ValueError('unsupported ordered sideview owner output')
    return dict(status='pending',native_ordered_sideview_owners='passed',counts=result['counts'],crossview_mapping_recomputed=False,human_accepted=False,pending=['Recompute affected mappings,DN and length fusion before new axis attributes;HIL remains separate'])


def reconstruct_ordered_sideview_owners(manifest,output):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_ordered_sideview_owners import produce
    produce(manifest,output)
    return validate_ordered_sideview_owners(output)


def validate_compound_member_bridges(bridge_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_compound_member_bridges import verify_output,MODE
    result=verify_output(bridge_run)
    if result.get('mode')!=MODE or result.get('DN_used_for_mapping')is not False or result.get('source_drawing_graphs_unchanged')is not True or result.get('member_topology_rebuilt')is not True or result.get('installed_lengths_assigned')!=0 or result.get('human_accepted')is not False:raise ValueError('unsupported native member bridge result')
    return dict(status='pending',native_member_bridges='passed',counts=result['counts'],human_accepted=False,pending=['Remaining external ports,inline physical lengths,complete SH16 mapping and HIL remain separate'])


def validate_compound_bridge_attribute_refresh(bundle):
    import sys
    owner=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from refresh_compound_bridge_attributes import verify
    return verify(bundle)


def validate_axis_vertical_DN_batch(batch_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from axis_vertical_DN_batch import verify_output,MODE
    result=verify_output(batch_run)
    if result.get('mode')!=MODE or result.get('graph_mutated')is not False or result.get('horizontal_plan_attributes_changed')is not False or result.get('whole_edge_DN_assigned')!=0 or result.get('physical_lengths_assigned')!=0 or result.get('human_accepted')is not False:raise ValueError('unsupported vertical DN batch result')
    return dict(status='pending',native_axis_vertical_DN_batch='passed',counts=result['counts'],whole_edge_attributes_complete=False,human_accepted=False,pending=['Unannotated/ambiguous vertical spans,axis physical lengths,full mapping and HIL remain separate'])


def validate_axis_vertical_DN_attribute_refresh(bundle):
    import sys
    owner=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from refresh_axis_vertical_DN_attributes import verify
    return verify(bundle)


def validate_axis_attribute_source_routing(routing_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from axis_attribute_source_routing import verify_output,MODE
    result=verify_output(routing_run)
    if result.get('mode')!=MODE or result.get('graph_mutated')is not False or result.get('physical_lengths_assigned')!=0 or result.get('whole_edge_DN_assigned')!=0 or result.get('human_accepted')is not False:raise ValueError('unsupported axis attribute-source routing result')
    return dict(status='pending',native_segment_source_routing='passed',edge_counts=result['edge_counts'],segment_counts=result['segment_counts'],native_source_status_counts=result['native_segment_status_counts'],
        mapping_or_attribute_completion_claimed=False,human_accepted=False,pending=['Horizontal mapping extent, native vertical attributes, unsupported source spans and HIL remain separate'])


def validate_compound_member_interfaces(interface_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_compound_member_interfaces import verify_output,MODE
    result=verify_output(interface_run)
    if result.get('mode')!=MODE or result.get('member_topology_rebuilt')is not True or result.get('source_drawing_graphs_unchanged')is not True or result.get('installed_lengths_assigned')!=0 or result.get('human_accepted')is not False:raise ValueError('unsupported compound member interface result')
    return dict(status='pending',native_member_interface_reconstruction='passed',counts=result['counts'],
        original_parent_qualification=result['parent_qualification']['qualification_policy'],original_axis_graph_mutated=False,member_topology_rebuilt=True,
        attribute_composition_performed=False,installed_lengths_assigned=0,human_accepted=False,pending=['External member routes, plan component allocation, global topology, viewer/source comparison and HIL remain separate'])

def validate_compound_interface_attribute_refresh(bundle):
    import sys
    owner=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from refresh_compound_interface_attributes import verify
    return verify(bundle)

def validate_noncompound_main_extents(extent_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_noncompound_main_extents import verify_output
    result=verify_output(extent_run)
    return dict(status='pending',native_noncompound_main_replay='passed',counts=result['counts'],
        existing_correspondences_unchanged=True,local_topology_changed=False,installed_lengths_assigned=0,
        attribute_fusion_performed=False,human_accepted=False,
        pending=['Noncompound plan T-to-T centreline only; installation/net lengths, unresolved regions and HIL remain separate'])


def validate_noncompound_main_attribute_refresh(bundle):
    import sys
    owner=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from refresh_noncompound_main_attributes import verify
    return verify(bundle)


def validate_compound_member_projections(member_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_compound_member_projections import verify_output
    result=verify_output(member_run)
    return dict(status='pending',native_compound_member_replay='passed',counts=result['counts'],
        source_drawing_graphs_unchanged=True,global_plan_topology_complete=False,attribute_fusion_performed=False,human_accepted=False,
        pending=['Scoped member topology and plan DN/centreline only; other members, unshown lengths, attribute publication and HIL remain separate'])


def validate_compound_member_attribute_refresh(bundle):
    import sys
    owner=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from refresh_compound_member_attributes import verify
    return verify(bundle)


def validate_ordered_anchor_branches(branch_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from ordered_anchor_branch_paths import verify_output
    result=verify_output(branch_run)
    return dict(status='pending',ordered_anchor_branch_native_replay='passed',counts=result['counts'],unresolved=result['pending'],
        remote_connections_added=0,physical_ports_created=0,whole_axis_values_assigned=False,human_accepted=False,
        pending=['Drawn branch context and plan DN/XY only; remote equipment/ports, unknown whole-axis extents and HIL remain separate'])


def validate_ordered_branch_attribute_refresh(bundle):
    import sys
    owner=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from refresh_ordered_branch_attributes import verify
    return verify(bundle)


def validate_ordered_group_plan_lengths(length_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from ordered_group_plan_lengths import verify_output
    result=verify_output(length_run)
    return dict(status='pending',ordered_group_native_length_replay='passed',counts=result['counts'],unresolved_groups=result['pending'],human_accepted=False,
        pending=['Native child pipe XY and complete run extents are separate; unknown inline interiors, net pipe lengths, actual browser and HIL remain separate'])


def validate_ordered_group_attribute_refresh(bundle):
    import sys
    owner=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from refresh_ordered_group_attributes import verify
    return verify(bundle)


def validate_confirmed_member_plan_paths(member_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from confirmed_member_plan_paths import verify_output
    result=verify_output(member_run)
    return dict(status='pending',member_native_plan_path_replay='passed',counts=result['counts'],human_accepted=False,
        pending=['Member plan run centreline is proved; net pipe cut length, omitted connectors, axis attribute publication and HIL remain separate'])


def validate_confirmed_member_attribute_refresh(bundle):
    import sys
    owner=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from refresh_confirmed_member_attributes import verify
    return verify(bundle)


def validate_confirmed_compound_lanes(lane_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from confirmed_compound_pipe_lanes import verify_output
    r=verify_output(lane_run)
    return dict(status='pending',expert_lane_semantics_native_replay='passed',confirmed_declarations=r['confirmed_declarations'],declaration_slots=r['confirmed_declaration_slots'],
        physical_pipe_instances_created=0,source_LINE_assignments=0,scalar_DN_assignments=0,physical_lengths_assigned=0,human_accepted=False,
        pending=['Two-pipe meaning and sideview200 confirmed; source-LINE membership, member topology reconstruction and dual-view fusion remain technical work'])


def validate_native_projection_batch(projection_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from native_projection_batch import verify_output
    r=verify_output(projection_run)
    return dict(status='pending',parallel_native_projection_replay='passed',edges=r['edges'],geometry_kernels_unchanged=True,
        topology_connections_assigned=0,physical_values_assigned=0,human_accepted=False,pending=['Native source projections only; local topology, correspondence, attribute fusion and HIL remain separate'])


def validate_native_named_axis_columns(column_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from native_named_axis_columns import verify_output
    result=verify_output(column_run)
    return dict(status='pending',native_column_source_replay='passed',counts=result['counts'],source_geometry_replayed=True,
        graph_mutated=False,crossview_mappings_assigned=0,whole_edge_DN_assigned=0,physical_lengths_assigned=0,human_accepted=False,
        pending=['Local column source identity only; independent floor network/path anchors, horizontal attribute fusion and HIL remain separate'])


def validate_native_named_interface_batch(batch_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from batch_native_named_interfaces import verify_output
    result=verify_output(batch_run)
    return dict(status='pending',source_annotation_replay='passed',counts=result['counts'],
        by_drawing={k:r['counts']for k,r in result['drawings'].items()},topology_owner_stage_reexecuted=False,
        graph_mutated=False,whole_edge_DN_assigned=0,physical_lengths_assigned=0,crossview_mappings_assigned=0,human_accepted=False,
        pending=['Native named-interface roles and local observed DN only; checked local topology, correspondence, horizontal attributes and HIL remain separate'])

def validate_projected_circle_full_plan_DN(batch_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_projected_circle_full_plan_DN import verify_output
    result=verify_output(batch_run)
    return dict(status='pending',source_replay='passed',counts=result['counts'],projected_circle_nodes={f:r['native_projected_circle_nodes']for f,r in result['floors'].items()},
        source_T_exceptions={f:r['source_T_exceptions']for f,r in result['floors'].items()},graph_mutated=False,physical_lengths_assigned=0,human_accepted=False,
        pending=['Only explicit marked source extents qualify projected branch roles; other connections, axis fusion and HIL remain separate'])

def validate_plan_DN_readiness_trace(trace_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from plan_DN_readiness_trace import verify
    return verify(trace_run)

def validate_attribute_template_refresh(bundle):
    import sys
    owner=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
    if str(owner)not in sys.path:sys.path.insert(0,str(owner))
    from refresh_attribute_templates import verify
    return verify(bundle)


def validate_full_plan_DN(batch_run):
    from full_plan_DN_gate import validate
    return validate(batch_run)


def validate_inherited_full_plan_DN(batch_run):
    from inherited_full_plan_DN_gate import validate
    return validate(batch_run)


def validate_current_circle_full_plan_DN(batch_run):
    from current_circle_full_plan_DN_gate import validate
    return validate(batch_run)


def validate_user_circle_full_plan_DN(batch_run):
    from user_circle_full_plan_DN_gate import validate
    return validate(batch_run)


def validate_confirmed_overlap_full_plan_DN(batch_run):
    from confirmed_overlap_full_plan_DN_gate import validate
    return validate(batch_run)


def validate_native_level_discovery(batch_run):
    from native_level_discovery_gate import validate
    return validate(batch_run)

def validate_local_detail_full_plan_DN(batch_run):
    from local_detail_full_plan_DN_gate import validate
    return validate(batch_run)

def validate_main_continuity_full_plan_DN(batch_run):
    from main_continuity_full_plan_DN_gate import validate
    return validate(batch_run)


def validate_native_main_chain_batch(batch_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from extend_native_main_chain_batch import verify_output,MODE
    data=verify_output(batch_run)
    if (data.get('mode')!=MODE or any(data.get(k) is not False for k in ('attributes_fused','human_accepted','hil_ready'))):
        raise ValueError('native main-chain batch cannot promote attribute or human acceptance')
    return dict(status='pending',source_replay='whole_parent_and_native_main_chains_replayed',
        processed_axis_edges=data['all_axis_edges']['total_edges'],states=data['all_axis_edges']['states'],
        additional_native_paths=sum(len(v['records']) for v in data['native_main_chain_extension'].values()),
        additional_axis_edge_candidates=sum(len(r['iso_edges']) for v in data['native_main_chain_extension'].values() for r in v['records']),
        per_axis_edge_metric_allocation_known=False,attributes_fused=False,human_accepted=False,hil_ready=False,
        pending=['Main/detail aliases, per-edge DN/length allocation, complete-parent fusion and HIL'])


def validate_wave_main_crossview_batch(batch_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from rebuild_wave_cohort_crossview_batch import verify_output,MODE
    data=verify_output(batch_run)
    if (data.get('mode')!=MODE or data.get('attributes_fused') is not False
        or data.get('human_accepted') is not False or data.get('hil_ready') is not False):
        raise ValueError('wave cohort batch cannot claim attribute or human acceptance')
    return dict(status='pending',source_replay='wave_cohort_current_floor_and_complete_parent_replayed',
        processed_axis_edges=data['all_axis_edges']['total_edges'],states=data['all_axis_edges']['states'],
        changed_floor=data['current_wave_cohort']['floor'],current_floor_equipment=data['inventories'][str(data['current_wave_cohort']['floor'])]['counts'],
        unchanged_floor_results_preserved=data['current_wave_cohort']['unchanged_floor_results_preserved'],
        attributes_fused=False,human_accepted=False,hil_ready=False,pending=['Attribute fusion, remaining view aliases, whole-drawing source comparison and HIL'])


def validate_known_rule_batch(batch_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from apply_crossview_rule_batch import verify_output
    from batch_apply_crossview_rules import MODE
    data=verify_output(batch_run)
    if (data.get('mode')!=MODE or data.get('attributes_fused') is not False
        or data.get('human_accepted') is not False or data.get('hil_ready') is not False):
        raise ValueError('batch correspondence cannot claim fusion or HIL')
    rows=data['all_axis_edges']['records'];ids=[r['edge_id'] for r in rows]
    if len(ids)!=len(set(ids)) or len(ids)!=data['all_axis_edges']['total_edges']:
        raise ValueError('batch lost or duplicated an axis edge')
    return dict(status='pending',source_replay='complete_known_rule_batch_independently_replayed',
        processed_axis_edges=len(rows),states=data['all_axis_edges']['states'],
        attributes_fused=False,human_accepted=False,hil_ready=False,
        pending=['Apply source-qualified attributes, consume main/detail exceptions, compare original CAD and submit remaining ambiguities to HIL'])


def validate_crossview_inventory(inventory_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from crossview_equipment_branch_inventory import verify_output
    receipt_path=Path(inventory_run)/'inventory-receipt.json';mode=None
    if receipt_path.exists():
        mode=json.loads(receipt_path.read_text(encoding='utf-8')).get('mode')
        if mode=='source_endpoint_branch_inventory_v2':
            from crossview_equipment_branch_inventory_v2 import verify_output
        elif mode=='inherited_circle_endpoint_branch_inventory_v3':
            from inherited_circle_branch_inventory import verify_output
        elif mode=='wave_rebased_plan_branch_inventory_v4':
            from wave_rebased_branch_inventory import verify_output
        elif mode=='two_arm_circle_rebased_branch_inventory_v1':
            from two_arm_circle_branch_inventory import verify_output
        elif mode=='pending_native_junction_rebased_branch_inventory_v1':
            from pending_junction_branch_inventory import verify_output
        elif mode is not None:raise ValueError('unsupported branch inventory entry mode')
    inventory=verify_output(inventory_run)
    if (inventory.get('status')!='source_comparison_inventory_not_mapping'
        or inventory.get('local_graphs_mutated') is not False or inventory.get('mapped_paths')!=0
        or inventory.get('human_accepted') is not False or inventory.get('hil_ready') is not False):
        raise ValueError('unsupported branch inventory state')
    if mode=='inherited_circle_endpoint_branch_inventory_v3':
        extension=inventory.get('inherited_circle_branch_extension',{})
        if (extension.get('mode')!=mode or not extension.get('records') or extension.get('local_graphs_mutated') is not False
            or extension.get('mapped_paths')!=0 or extension.get('physical_ports_verified') is not False or extension.get('human_accepted') is not False):
            raise ValueError('unsupported inherited circle inventory scope')
    if mode=='wave_rebased_plan_branch_inventory_v4':
        rebase=inventory.get('wave_reconstruction_inventory_rebase',{})
        if (inventory.get('inventory_mode')!=mode or rebase.get('mode')!=mode
            or rebase.get('axis_evidence_preserved_on_identical_inputs') is not True
            or rebase.get('transition',{}).get('equipment_and_owner_roots_preserved') is not True
            or rebase.get('old_plan_graph_sha256')==rebase.get('plan_graph_sha256') or not rebase.get('plan_graph_sha256')
            or any(rebase.get(k) is not False for k in ('local_graphs_mutated','physical_ports_verified','human_accepted'))
            or rebase.get('mapped_paths')!=0 or rebase.get('physical_values_assigned')!=0):
            raise ValueError('unsupported wave-rebased inventory scope')
    if mode in ('two_arm_circle_rebased_branch_inventory_v1','pending_native_junction_rebased_branch_inventory_v1'):
        key='two_arm_circle_inventory_rebase' if mode=='two_arm_circle_rebased_branch_inventory_v1' else 'pending_native_junction_inventory_rebase'
        rebase=inventory.get(key,{})
        checks=rebase.get('fresh_plan_service_checks',[])
        expected={(row['equipment_id'],s) for row in inventory['records'] for s in ('supply','return')}
        if (inventory.get('inventory_mode')!=mode or rebase.get('mode')!=mode
            or rebase.get('preserved_axis_evidence_on_identical_inputs') is not True or not rebase.get('plan_graph_sha256')
            or rebase.get('mapped_paths')!=0 or rebase.get('physical_values_assigned')!=0
            or rebase.get('physical_ports_verified') is not False or rebase.get('human_accepted') is not False
            or len(checks)!=len(expected) or {(c['equipment_id'],c['system']) for c in checks}!=expected
            or any(type(c.get('ready')) is not bool for c in checks)):
            raise ValueError('unsupported circle/junction-rebased inventory scope')
        if mode=='pending_native_junction_rebased_branch_inventory_v1' and (not rebase.get('resolved_native_T_ids')
            or len(set(rebase['resolved_native_T_ids']))!=len(rebase['resolved_native_T_ids'])):
            raise ValueError('missing or repeated resolved native T scope')
    rows=inventory['records'];ready=sum(r['ready_for_mapping_comparison'] for r in rows)
    if inventory['counts']!={'equipment':len(rows),'ready_for_mapping_comparison':ready}:raise ValueError('branch inventory counts differ')
    result=dict(status='pending',source_comparison='native_branch_inventory_replayed',equipment=len(rows),
        ready_for_mapping_comparison=ready,mapped_paths=0,technical_followup_equipment=len(rows)-ready,
        pending=['Resolve grouped local source defects before mapping; comparison-ready candidates still need cross-view correspondence checks'],
        human_accepted=False,hil_ready=False)
    if mode=='wave_rebased_plan_branch_inventory_v4':result.update(source_comparison='native_wave_rebased_branch_inventory_replayed',plan_graph_sha256=rebase['plan_graph_sha256'])
    if mode in ('two_arm_circle_rebased_branch_inventory_v1','pending_native_junction_rebased_branch_inventory_v1'):
        result.update(source_comparison='native_circle_or_junction_rebased_branch_inventory_replayed',plan_graph_sha256=rebase['plan_graph_sha256'],plan_service_checks=len(rebase['fresh_plan_service_checks']))
    return result

def validate_native_block_branches(reconstruction_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from reconstruct_native_block_branches import verify_output
    directory=Path(reconstruction_run);audit=verify_output(directory);graph=read(directory/'graph_with_edges.json');state=graph['sourceNativeBlockBranchReconstruction']
    return dict(status='pending',source_replay='passed',graph_sha256=audit['output_graph_sha256'],reconstructed_edges=len(state['records']),
        unresolved_edges=state['pending'],pending=['Recompute affected source comparison, DN and mapping after local source path reconstruction'],
        components_conserved=True,physical_ports_verified=False,human_accepted=False,hil_ready=False)


def _check_inherited_circle_mapping_scope(mapping):
    rows=mapping['records'];equipment=mapping['equipment_scope'];n=len(equipment)
    if (mapping.get('status')!='source_checked_path_correspondence_attributes_pending' or mapping.get('local_graphs_mutated') is not False
        or mapping.get('expert_confirmation_claimed') is not False or mapping.get('physical_source_identity_resolved') is not False
        or mapping.get('physical_values_assigned')!=0 or mapping.get('human_accepted') is not False or mapping.get('hil_ready') is not False
        or n<3 or len(set(equipment))!=n or len(rows)!=4*n-2 or len({r['mapping_id'] for r in rows})!=len(rows)
        or any(r.get('physical_source_identity_resolved') is not False or r.get('physical_ports_verified') is not False or r.get('human_accepted') is not False for r in rows)
        or {(r.get('equipment_id'),r.get('system')) for r in rows if r.get('kind')=='equipment_branch'}!={(e,s) for e in equipment for s in ('supply','return')}
        or sum(r.get('kind')=='main_between_equipment_branches' for r in rows)!=2*(n-1)):
        raise ValueError('unsupported inherited circle correspondence state or extent')


def _validate_anchored_floor_main_scope(mapping):
    rows=mapping.get('records',[]);proof=mapping.get('evidence',{});structure=proof.get('structure',{});nodes=structure.get('node_mapping',{})
    equipment=mapping.get('equipment_scope',[]);anchors=structure.get('anchors',[]);pairs=structure.get('pairs',[])
    if (mapping.get('status')!='source_checked_full_floor_main_correspondence_attributes_pending'
        or any(mapping.get(k) is not False for k in ('local_graphs_mutated','expert_confirmation_claimed','physical_source_identity_resolved','human_accepted','hil_ready'))
        or mapping.get('physical_values_assigned')!=0 or len(equipment)<3 or len(equipment)!=len(set(equipment))
        or structure.get('unique_full_floor_T_network') is not True or structure.get('physical_direction_inferred') is not False
        or structure.get('floor')!=mapping.get('floor') or not nodes or len(set(nodes.values()))!=len(nodes)):
        raise ValueError('unsupported full-floor main network correspondence state')
    if (len(anchors)!=2*len(equipment) or {(r.get('equipment_id'),r.get('system')) for r in anchors}!={(d,s) for d in equipment for s in ('supply','return')}
        or any(nodes.get(r.get('plan_T'))!=r.get('iso_T') for r in anchors)):
        raise ValueError('independent paired service anchors differ')
    if not rows or len(pairs)!=len(rows) or len({r['mapping_id'] for r in rows})!=len(rows):raise ValueError('full-floor main path records missing or duplicated')
    for view,selected in [('plan',set(nodes)),('iso',set(nodes.values()))]:
        if set(proof.get('native_T_proofs',{}).get(view,{}))!=selected:raise ValueError('full native floor T coverage missing')
        ids=[r[view+'_edges'][0] for r in rows if len(r.get(view+'_edges',[]))==1]
        if len(ids)!=len(rows) or len(ids)!=len(set(ids)) or set(proof.get('main_path_coverage',{}).get(view,{}))!=set(ids):raise ValueError('main source coverage or edge uniqueness differs')
    for row in rows:
        if (row.get('kind')!='anchored_same_floor_T_to_T_main' or row.get('floor')!=mapping['floor'] or row.get('physical_ports_verified') is not False
            or row.get('physical_length_mm') is not None or row.get('human_accepted') is not False
            or nodes.get(row.get('plan_start'))!=row.get('iso_start') or nodes.get(row.get('plan_end'))!=row.get('iso_end')):
            raise ValueError('main path endpoint or unknown physical scope differs')
    actual={(r['plan_edges'][0],r['iso_edges'][0],r['system'],r['plan_start'],r['plan_end'],r['iso_start'],r['iso_end']) for r in rows}
    expected={(r['plan_edge'],r['iso_edge'],r['system'],r['plan_start'],r['plan_end'],r['iso_start'],r['iso_end']) for r in pairs}
    if actual!=expected:raise ValueError('declared main paths differ from complete network correspondence')
    lineage=proof.get('historical_scope_lineage',[]);protected=proof.get('preserved_floor_attributes')
    if (len({(r['group_id'],r['previous_mapping_id']) for r in lineage})!=len(lineage)
        or any(r.get('local_path_semantics_preserved') is not True or r.get('human_confirmation_transferred') is not False for r in lineage)):
        raise ValueError('historical correspondence scope changed')
    known={r['current_main_mapping_id'] for r in lineage if r.get('current_main_mapping_id') is not None}
    if protected:
        if (protected.get('history_only_not_a_mapping_seed') is not True or protected.get('attributes_rewritten') is not False
            or protected.get('human_confirmation_transferred') is not False or protected.get('values_assigned')!=0
            or protected.get('old_group_attributes_preserved')!=len(lineage)):raise ValueError('prior named/floor attribute protection differs')
        known.update(protected['named_main_mapping_ids'])
    if (not known<={r['mapping_id'] for r in rows} or mapping.get('historical_main_paths')!=len(known)
        or mapping.get('additional_main_paths')!=len(rows)-len(known)):raise ValueError('new main scopes duplicate or replace old ones')
    return dict(status='pending',path_correspondence='native_anchored_full_floor_main_network_replayed',mapped_main_paths=len(rows),native_T_nodes=len(nodes),
        equipment=len(equipment),historical_scopes_retained=len(lineage),historical_main_paths=len(known),additional_main_paths=mapping['additional_main_paths'],
        named_segment_snapshots_retained=len(protected['named_segment_snapshots']) if protected else 0,plan_graph_sha256=mapping['plan_graph_sha256'],
        physical_values_assigned=0,expert_confirmation_claimed=False,human_accepted=False,hil_ready=False,
        pending=['Reconstruct floor-plan DN and physical-length scopes; preserve all previous values before source comparison, publication and human acceptance'])


def validate_source_crossview(mapping_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from match_source_checked_crossview_paths import verify_output
    paired=False;refined=False;inherited=False;mode=None;receipt_path=Path(mapping_run)/'source-mapping-receipt.json'
    if receipt_path.exists():
        mode=read(receipt_path).get('mode')
        if mode=='source_checked_paired_service_paths_v1':
            from match_paired_service_crossview_paths import verify_output
            paired=True
        elif mode=='paired_service_junction_refined_paths_v1':
            from refine_paired_service_path_correspondence import verify_output
            paired=True;refined=True
        elif mode=='source_checked_inherited_circle_main_order_paths_v1':
            from match_inherited_circle_crossview_paths import verify_output
            inherited=True
        elif mode=='source_checked_wave_rebased_inherited_circle_paths_v2':
            from match_wave_rebased_circle_paths import verify_output
            inherited=True
        elif mode=='source_checked_anchored_floor_main_network_v1':
            from match_anchored_floor_main_network import verify_output
        elif mode=='source_checked_junction_rebased_corridor_groups_v1':
            from match_junction_rebased_corridors import verify_output
        elif mode=='junction_rebased_paired_native_paths_v1':
            from match_junction_rebased_paired_paths import verify_output
        elif mode=='source_checked_known_junction_direct_mains_v1':
            from match_known_junction_direct_mains import verify_output
        elif mode is not None:raise ValueError('unsupported source correspondence entry mode')
    mapping=verify_output(mapping_run)
    if mode=='source_checked_known_junction_direct_mains_v1':
        from match_known_junction_direct_mains import check_result
        return check_result(mapping)
    if mode=='junction_rebased_paired_native_paths_v1':
        from match_junction_rebased_paired_paths import check_result
        return check_result(mapping)
    if mode=='source_checked_anchored_floor_main_network_v1':return _validate_anchored_floor_main_scope(mapping)
    if mode=='source_checked_junction_rebased_corridor_groups_v1':
        from junction_rebased_corridor_gate import validate
        return validate(mapping)
    if mode=='source_checked_wave_rebased_inherited_circle_paths_v2':
        groups=mapping.get('groups',[]);rebase=mapping.get('evidence',{}).get('native_wave_inventory_rebase',{});rows=[];equipment=[]
        if (mapping.get('mode')!='independent_native_common_anchor_mapping_groups_v1' or not groups
            or len({g['group_id'] for g in groups})!=len(groups)
            or rebase.get('mode')!='wave_rebased_plan_branch_inventory_v4' or rebase.get('plan_graph_sha256')!=mapping.get('plan_graph_sha256')
            or rebase.get('axis_evidence_preserved_on_identical_inputs') is not True
            or any(rebase.get(k) is not False for k in ('local_graphs_mutated','human_accepted'))
            or rebase.get('mapped_paths')!=0 or rebase.get('physical_values_assigned')!=0
            or any(mapping.get(k) is not False for k in ('local_graphs_mutated','expert_confirmation_claimed','physical_source_identity_resolved','human_accepted','hil_ready'))
            or mapping.get('physical_values_assigned')!=0):raise ValueError('wave correspondence refers to stale or promoted inventory evidence')
        for group in groups:
            _check_inherited_circle_mapping_scope(group)
            if (any(group.get(k)!=mapping.get(k) for k in ('plan_graph_sha256','iso_graph_sha256','source_sha256'))
                or len(group.get('historical_mapping_lineage',[]))!=len(group['records'])
                or any(r.get('local_path_semantics_preserved') is not True or r.get('human_confirmation_transferred') is not False for r in group['historical_mapping_lineage'])):
                raise ValueError('wave mapping group lost historical paths or changed its local version')
            rows.extend(dict(row,group_id=group['group_id']) for row in group['records']);equipment.extend(group['equipment_scope'])
        if rows!=mapping['records'] or equipment!=mapping['equipment_scope'] or len(set(equipment))!=len(equipment) or len({r['mapping_id'] for r in rows})!=len(rows):
            raise ValueError('wave mapping batch repeats or loses an independent group')
        return dict(status='pending',path_correspondence='native_wave_rebased_inherited_circle_main_order_replayed',mapped_paths=len(rows),
            equipment=len(equipment),independent_groups=len(groups),plan_graph_sha256=mapping['plan_graph_sha256'],
            expert_confirmation_claimed=False,human_accepted=False,hil_ready=False,
            pending=['Rebuild plan DN/metrics and fusion on the new local version; preserve unresolved native DN differences and HIL'])
    if inherited:
        _check_inherited_circle_mapping_scope(mapping)
    if paired and (mapping.get('status')!=('source_checked_junction_refined_correspondence_attributes_pending' if refined else 'source_checked_paired_service_correspondence_attributes_pending')
        or mapping.get('local_graphs_mutated') is not False or mapping.get('expert_confirmation_claimed') is not False
        or mapping.get('human_accepted') is not False or mapping.get('hil_ready') is not False):raise ValueError('unsupported paired correspondence state')
    return dict(status='pending',path_correspondence='native_wave_rebased_inherited_circle_main_order_replayed' if mode=='source_checked_wave_rebased_inherited_circle_paths_v2' else 'native_inherited_circle_main_order_replayed' if inherited else 'native_branch_target_junction_refinement_replayed' if refined else 'native_paired_service_corridors_replayed' if paired else 'native_branch_and_main_order_replayed',mapped_paths=len(mapping['records']),
        equipment=len(mapping['equipment_scope']),expert_confirmation_claimed=False,human_accepted=False,hil_ready=False,
        pending=['Scoped correspondence does not accept DN, installed lengths or the rest of either local drawing'])


def validate_plan_DN(diameter_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from plan_pipe_diameter_scopes import verify_output
    receipt_path=Path(diameter_run)/'plan-DN-scope-receipt.json';refined=False
    if receipt_path.exists():
        mode=read(receipt_path).get('mode')
        if mode=='paired_service_plan_DN_scopes_v1':
            from paired_plan_DN_scopes import verify_output
        elif mode=='paired_service_junction_refined_plan_DN_scopes_v1':
            from refined_paired_plan_DN_scopes import verify_output
            refined=True
        elif mode=='junction_rebased_calibrated_plan_DN_scopes_v1':
            from junction_rebased_plan_DN_scopes import verify_output
        elif mode not in (None,'calibrated_plan_DN_scopes'):raise ValueError('unsupported plan DN entry mode')
    data=verify_output(diameter_run)
    expected='source_checked_junction_refined_plan_DN_scopes_human_pending' if refined else 'source_checked_plan_DN_scopes_human_pending'
    if data.get('status')!=expected or data.get('local_graph_mutated') is not False or data.get('human_accepted') is not False:raise ValueError('unsupported plan DN scope state')
    if refined and (data.get('previous_checked_records_preserved') is not True or data.get('physical_values_fused') is not False):raise ValueError('unsupported refined plan DN preservation state')
    if data.get('mode')=='junction_rebased_calibrated_plan_DN_scopes_v1':
        calibration=data.get('calibrated_direct_binding',{}).get('native_calibration_control_rebase',{})
        if (data.get('physical_values_fused') is not False or not calibration.get('controls')
            or calibration.get('current_graph_sha256')!=data.get('graph_sha256')
            or calibration.get('original_graph_sha256')!=data.get('original_graph_sha256')
            or any(calibration.get(k) is not True for k in ('source_controls_replayed','current_targets_replayed','target_annotation_guards_unchanged'))
            or any(calibration.get(k) is not False for k in ('original_policy_or_graph_mutated','collector_globals_changed','human_accepted'))
            or calibration.get('current_whole_edge_DN_assigned')!=0):raise ValueError('current DN calibration scopes were widened or promoted')
    rows=data['records']
    return dict(status='pending',source_replay='passed',plan_graph_sha256=data['graph_sha256'],source_sha256=data['source_sha256'],
        plan_drawn_pipe_scopes=len(rows),known_DN_scopes=sum(r['nominal_mm'] is not None for r in rows),
        scope='native_plan_drawn_pipe_paths_only',local_graph_mutated=False,human_accepted=False,hil_ready=False,
        pending=['Cross-view allocation, unshown equipment connections, whole drawing correctness and human acceptance are separate checks'])


def validate_axis_segment_DN(diameter_run):
    """Replay qualified source-segment observations, not whole-riser metrics."""
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from native_segment_dn_candidates_v2 import verify_output
    data=verify_output(diameter_run)
    if (data.get('status')!='segment_candidates_not_accepted' or data.get('local_graph_mutated') is not False
        or data.get('graph_mutated') is not False or data.get('physical_values_fused') is not False or data.get('human_accepted') is not False
        or data.get('original_native_document_unchanged') is not True or data.get('all_other_native_competitors_retained') is not True):
        raise ValueError('unsupported qualified axis segment-DN state')
    return dict(status='pending',source_replay='passed',source_sha256=data['source_sha256'],graph_sha256=data['graph_sha256'],
        segment_DN_observations=len(data['observations']),qualified_display_stems=len(data['excluded_competing_source_chains']),
        whole_edge_DN_assigned=0,physical_values_fused=False,human_accepted=False,hil_ready=False,
        pending=['Local segment observations do not accept whole riser DN, vertical length, horizontal source correspondence or the complete drawing'])


def validate_axis_riser_DN(diameter_run):
    """Replay native segment cuts, annotation inventory and through-T DN scopes."""
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from native_axis_riser_DN_scopes import verify_output
    data=verify_output(diameter_run)
    if (data.get('status')!='source_checked_axis_through_riser_segment_DN_human_pending'
        or any(data.get(k) is not False for k in ('local_graph_mutated','physical_values_fused','floor_interface_correspondence_confirmed','human_accepted'))
        or data.get('installed_lengths_assigned')!=0 or data.get('whole_edge_DN_assigned')!=0):raise ValueError('unsupported native riser segment scope state')
    rows=data['records']
    if not rows or any(r.get('whole_local_edge_DN_assigned') is not False or r.get('physical_length_mm') is not None
        or r.get('scope')!='native_axis_through_riser_drawn_vertical_segment_only' for r in rows):raise ValueError('riser segment scope cannot claim mixed-edge values')
    return dict(status='pending',source_replay='passed',source_sha256=data['source_sha256'],graph_sha256=data['graph_sha256'],
        source_checked_riser_segment_DN_scopes=len(rows),known_DN_scopes=sum(r['nominal_mm'] is not None for r in rows),
        whole_edge_DN_assigned=0,installed_lengths_assigned=0,local_graph_mutated=False,human_accepted=False,hil_ready=False,
        pending=['Riser floor-interface correspondence, explicit axis length evidence, attribute composition and whole drawing acceptance remain separate checks'])


def validate_named_floor_segments(mapping_run,*,lower=False):
    """Replay named correspondence with explicit upper/lower mixed-edge limits."""
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    if lower:
        from match_named_riser_lower_floor_segments import verify_output
    else:
        from match_named_riser_floor_segments import verify_output
    data=verify_output(mapping_run)
    expected='source_checked_named_lower_floor_segment_correspondence_attributes_pending' if lower else 'source_checked_named_upper_floor_segment_correspondence_attributes_pending'
    if (data.get('status')!=expected
        or any(data.get(k) is not False for k in ('local_graphs_mutated','physical_values_fused','physical_ports_verified','human_accepted'))
        or data.get('DN_values_assigned')!=0 or data.get('physical_lengths_assigned')!=0):raise ValueError('unsupported named segment correspondence state')
    records=data['records'];interfaces=data['floor_interface_correspondences']
    if len(interfaces)!=2 or {r['system'] for r in interfaces}!={'supply','return'} or len(records)!=4 or len(data['junction_correspondences'])!=4:
        raise ValueError('two paired named interfaces and their existing junctions required')
    for row in records:
        scopes=row['iso_segment_scopes'];kind=row['kind']
        prefix='named_riser_lower_floor_segment_' if lower else 'named_riser_floor_segment_'
        if (kind not in (prefix+'approach',prefix+'network_link')
            or row.get('physical_port_verified') is not False or row.get('physical_length_mm') is not None
            or row.get('whole_axis_DN_assigned') is not False or row.get('whole_axis_length_assigned') is not False
            or row.get('axis_bend_is_attribute_limit_not_new_physical_node') is not True
            or len(scopes)!=1 or not scopes[0]['segment_indices']
            or (kind.endswith('approach') and (scopes[0].get('whole_local_edge') is not False
                or (lower and scopes[0]['segment_indices'][0]!=0)))):
            raise ValueError('named mixed-edge correspondence escaped its segment limits')
    return dict(status='pending',source_replay='passed',source_sha256=data['source_sha256'],graph_sha256=data['graph_sha256'],
        floor=data['floor'],floor_interface_correspondences=2,segment_correspondence_records=4,existing_junction_correspondences=4,
        local_graphs_mutated=False,physical_values_fused=False,physical_ports_verified=False,human_accepted=False,hil_ready=False,
        pending=['Segment-aware plan DN/metric fusion, other interfaces and whole source/human acceptance remain separate checks'])


def validate_inherited_wave_continuity(repair_run):
    """Replay same-pipe wave reconstruction before any new mapping or HIL."""
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from inherited_wave_pair_continuity import verify_output,MODE
    receipt=verify_output(repair_run);graph=json.loads((Path(repair_run)/'graph_with_edges.json').read_text('utf8'))
    stage=graph.get('sourceInheritedWavePairContinuity',{});proof=receipt['proof'];count=proof['pairs']
    if (receipt.get('mode')!=MODE or stage.get('mode')!=MODE or isinstance(count,bool) or not isinstance(count,int) or count<1
        or proof['nodes_before']-proof['nodes_after']!=2*count or proof['edges_before']-proof['edges_after']!=count
        or len(graph['nodes'])!=proof['nodes_after'] or len(graph['edges'])!=proof['edges_after']
        or len(stage.get('records',[]))!=count or len(stage.get('edge_id_mapping',{}))!=count
        or len(stage.get('retired_node_snapshots',[]))!=2*count
        or stage.get('dependent_mapping_attributes_and_HIL_invalidated') is not True
        or stage.get('unpaired_continuations_inferred') is not False or stage.get('physical_lengths_assigned')!=0
        or stage.get('human_accepted') is not False or graph.get('metadata',{}).get('hil_ready') is not False):
        raise ValueError('inherited wave reconstruction escaped its topology/unknown-length scope')
    return dict(status='pending',source_replay='passed',wave_pairs=count,nodes=proof['nodes_after'],edges=proof['edges_after'],
        components=proof['components'],source_sha256=receipt['inputs']['source']['sha256'],graph_sha256=receipt['output_graph_sha256'],
        physical_lengths_assigned=0,dependent_mapping_attributes_and_HIL_invalidated=True,human_accepted=False,hil_ready=False,
        pending=['Adopt the new local graph through inventories/mapping/attributes; complete full native comparison and HIL'])


def validate_wave_plan_scope_adoption(adoption_run):
    """Independently replay current-scope adoption without granting HIL."""
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from adopt_wave_rebased_plan_scopes import verify_output,MODE
    audit=verify_output(adoption_run);proof=audit['proof'];rows=proof['records']
    if (audit.get('mode')!=MODE or audit.get('human_accepted') is not False or audit.get('hil_ready') is not False
        or proof.get('prior_topology_components_and_other_attributes_preserved') is not True or proof.get('whole_DN_or_lengths_added')!=0
        or proof.get('related_HIL_confirmation_inherited') is not False or proof.get('human_accepted') is not False
        or not rows or len({r['edge_id'] for r in rows})!=len(rows)
        or proof['retained_historical_attributes']+proof['added_partial_attributes']!=len(rows)
        or sum(r['added_attribute'] is True for r in rows)!=proof['added_partial_attributes']
        or any(r.get('related_HIL_confirmation_inherited') is not False or r.get('human_accepted') is not False or r.get('equal_plan_axis_segment_extents_proved') is not False for r in rows)):
        raise ValueError('current plan scope adoption escaped its preserved/partial domain')
    return dict(status='pending',source_replay='passed',current_scope_edges=len(rows),retained_historical_attributes=proof['retained_historical_attributes'],
        added_partial_attributes=proof['added_partial_attributes'],output_graph_sha256=audit['output_graph_sha256'],whole_DN_or_lengths_added=0,
        human_accepted=False,hil_ready=False,pending=['Integrate source comparison and viewer; preserve unknown whole extents, annotation history and separate human acceptance'])


def validate_mapped_native_DN_comparison(comparison_run):
    """Replay both current view dependencies and native local DN ownership."""
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from compare_mapped_plan_axis_diameters import verify_output,check_result
    return check_result(verify_output(comparison_run))


def validate_wave_rebased_plan_attributes(attribute_run):
    """Replay the current batch owner before validating source-only DN/XY."""
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from wave_rebased_plan_attributes import verify_output,check_result
    return check_result(verify_output(attribute_run))


def validate_current_remaining_plan_scopes(scope_run):
    """Replay current context branches, named approaches and local candidates."""
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from current_remaining_floor_plan_scopes import verify_output,check_result
    return check_result(verify_output(scope_run))


def validate_known_junction_main_fusion(fusion_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from attach_known_junction_main_plan_attributes import verify_output
    from native_replay_session import verify_once
    audit=verify_once(Path(fusion_run),verify_output)
    if (audit.get('hil_ready') is not False or audit.get('human_accepted') is not False
        or audit['stage'].get('prior_topology_components_and_all_attributes_preserved') is not True
        or audit['stage'].get('new_connections_added')!=0):
        raise ValueError('Known-junction fusion cannot promote HIL')
    return dict(status='pending',source_replay='passed',added_main_attributes=audit['stage']['added_main_attributes'],
        prior_topology_components_and_all_attributes_preserved=True,human_accepted=False,hil_ready=False)


def validate_known_junction_main_plan_attributes(attribute_run):
    """Replay source-checked direct-main pipe DN and plan XY."""
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from known_junction_main_plan_attributes import verify_output,check_result
    return check_result(verify_output(attribute_run))


def validate_current_paired_plan_attributes(attribute_run):
    """Replay current paired native through/branch DN and floor-plan XY."""
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from junction_rebased_paired_plan_attributes import verify_output,check_result
    return check_result(verify_output(attribute_run))


def validate_junction_rebased_plan_attributes(attribute_run):
    """Replay current native DN/XY, preserving unmeasured detail domains."""
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from junction_rebased_plan_attributes import verify_output,check_result
    return check_result(verify_output(attribute_run))


def validate_inherited_circle_plan_attributes(attribute_run):
    """Independently replay mapped plan DN/XY; keep composition and HIL separate."""
    import math,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from inherited_circle_plan_attributes import verify_output,MODE
    data=verify_output(attribute_run)
    if (data.get('mode')!=MODE or data.get('status')!='source_checked_inherited_circle_plan_DN_and_XY_not_fused'
        or any(data.get(k) is not False for k in ('local_graphs_mutated','physical_values_fused','physical_ports_verified','physical_source_identity_resolved','human_accepted'))
        or data.get('whole_axis_DN_assigned')!=0 or data.get('installed_lengths_assigned')!=0):raise ValueError('unsupported inherited-circle attribute state')
    equipment=data['equipment_scope'];rows=data['records'];ids=[r['mapping_id'] for r in rows]
    if len(equipment)<3 or len(set(equipment))!=len(equipment) or len(rows)!=4*len(equipment)-2 or len(ids)!=len(set(ids)):
        raise ValueError('complete paired mapped plan attribute scope required')
    for system in ('supply','return'):
        selected=[r for r in rows if r['system']==system]
        if (sum(r['kind']=='equipment_branch' for r in selected)!=len(equipment)
            or sum(r['kind']=='main_between_equipment_branches' for r in selected)!=len(equipment)-1):raise ValueError('inherited-circle service or path extent differs')
    for row in rows:
        diameter=row['diameter'];metric=row['horizontal_projection']
        if (row.get('floor')!=data['floor'] or len(row['plan_edges'])!=1 or not row['iso_edges']
            or diameter['edge_id']!=row['plan_edges'][0] or diameter['system']!=row['system'] or not diameter.get('lineage')
            or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in (diameter['nominal_mm'],metric['value_mm']))
            or any(row.get(k) is not False for k in ('physical_source_identity_resolved','physical_ports_verified','whole_axis_DN_selected','human_accepted'))
            or row.get('whole_axis_physical_length_mm') is not None or metric.get('installed_whole_edge_length_mm') is not None
            or metric.get('unshown_connection_length_mm') is not None or not metric.get('pieces')):
            raise ValueError('inherited-circle plan evidence escaped its DN/XY domain')
    return dict(status='pending',source_replay='passed',mapped_DN_XY_scopes=len(rows),equipment=len(equipment),
        source_sha256=data['source_sha256'],graph_sha256=data['graph_sha256'],mapping_sha256=data['mapping_sha256'],
        local_graphs_mutated=False,physical_values_fused=False,physical_source_identity_resolved=False,
        installed_lengths_assigned=0,human_accepted=False,hil_ready=False,
        pending=['Compose with all prior plan/vertical attributes, compare native views, rebuild viewer and complete scoped HIL'])


def validate_upper_floor_plan_attributes(attribute_run,*,lower=False):
    """Replay plan-only DN/XY evidence within unchanged axis segment scopes."""
    import math,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    if lower:
        from named_lower_floor_plan_attributes import verify_output
    else:
        from named_upper_floor_plan_attributes import verify_output
    data=verify_output(attribute_run)
    expected_status='source_checked_lower_floor_plan_DN_and_XY_scopes_not_fused' if lower else 'source_checked_upper_floor_plan_DN_and_XY_scopes_not_fused'
    if (data.get('status')!=expected_status
        or any(data.get(k) is not False for k in ('local_graphs_mutated','physical_values_fused','physical_ports_verified','human_accepted'))
        or data.get('whole_axis_DN_assigned')!=0 or data.get('installed_lengths_assigned')!=0):
        raise ValueError('unsupported upper-floor plan attribute state')
    prefix='named_riser_lower_floor_segment_' if lower else 'named_riser_floor_segment_'
    rows=data['records'];expected={(s,prefix+k) for s in ('supply','return') for k in ('approach','network_link')}
    if len(rows)!=4 or {(r['system'],r['kind']) for r in rows}!=expected or len({r['mapping_id'] for r in rows})!=4:
        raise ValueError('four separate mapped approach/main attribute scopes required')
    for row in rows:
        diameter=row['diameter'];metric=row['horizontal_projection'];scopes=row['iso_segment_scopes']
        if (any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0
                for v in (diameter['nominal_mm'],metric['value_mm']))
            or len(row['plan_edges'])!=1 or diameter['edge_id']!=row['plan_edges'][0] or diameter['system']!=row['system']
            or not diameter.get('lineage') or len(scopes)!=1 or not scopes[0]['segment_indices']
            or row['iso_edges']!=[scopes[0]['edge_id']] or not scopes[0]['scope_paths']
            or (row['kind'].endswith('approach') and scopes[0].get('whole_local_edge') is not False)
            or (lower and row['kind'].endswith('approach') and scopes[0]['segment_indices'][0]!=0)
            or row.get('whole_axis_DN_selected') is not False or row.get('whole_axis_physical_length_mm') is not None
            or any(row.get(k) is not False for k in ('physical_port_verified','human_accepted'))
            or metric.get('installed_whole_edge_length_mm') is not None
            or metric.get('unshown_connection_length_mm') is not None or not metric.get('pieces')):
            raise ValueError('upper-floor plan evidence escaped its native DN/XY scope')
    return dict(status='pending',source_replay='passed',source_sha256=data['source_sha256'],graph_sha256=data['graph_sha256'],
        mapping_sha256=data['mapping_sha256'],mapped_DN_XY_scopes=4,physical_values_fused=False,
        whole_axis_DN_assigned=0,installed_lengths_assigned=0,local_graphs_mutated=False,human_accepted=False,hil_ready=False,
        pending=['Segment-aware composition, unchanged parent preservation, source comparison, viewer and HIL remain separate checks'])


def validate_touching_plan_chunks(scope_run):
    """Replay zero-gap path reading without inferring new connections."""
    import math,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from native_touching_plan_path_chunks import verify_output
    data=verify_output(scope_run)
    if (data.get('status')!='native_touching_chunks_read_only_geometry_replayed_not_connectivity_acceptance'
        or data.get('local_graph_mutated') is not False or data.get('human_accepted') is not False
        or data.get('physical_connections_added')!=0 or data.get('installed_lengths_assigned')!=0):raise ValueError('unsupported touching-path scope state')
    normalized=data.get('normalizations',[]);measured=data.get('measured_scopes',[])
    if not normalized or not measured or any(any(row.get(k)!=0 for k in ('added_span_units','physical_nodes_added','physical_edges_added')) for row in normalized):
        raise ValueError('touching paths cannot add graph connections or spans')
    for row in measured:
        metric=row['horizontal_projection'];value=metric['value_mm']
        if (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0
            or row.get('installed_whole_edge_length_mm') is not None or row.get('human_accepted') is not False
            or metric.get('installed_whole_edge_length_mm') is not None):raise ValueError('touching-path projection cannot claim installed length')
    return dict(status='pending',source_replay='passed',source_sha256=data['source_sha256'],graph_sha256=data['graph_sha256'],
        measured_plan_path_scopes=len(measured),exact_join_edges=[r['edge_id'] for r in normalized if r['join_points']],
        local_graph_mutated=False,physical_connections_added=0,installed_lengths_assigned=0,human_accepted=False,hil_ready=False,
        pending=['Local topology acceptance, cross-view correspondence, DN and attribute fusion remain separate stages'])


def validate_named_riser_plan_attributes(attribute_run):
    """Replay floor-plan attribute scopes without accepting physical ports."""
    import math,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from named_riser_plan_attributes import verify_output
    data=verify_output(attribute_run)
    if (data.get('status')!='source_checked_named_floor_approach_DN_and_XY_projection_not_fused'
        or any(data.get(k) is not False for k in ('local_graphs_mutated','physical_ports_verified','physical_values_fused','human_accepted'))
        or data.get('installed_lengths_assigned')!=0):raise ValueError('unsupported named plan attribute state')
    rows=data['records']
    if len(rows)!=2 or {r['system'] for r in rows}!={'supply','return'}:raise ValueError('separate supply and return plan approaches required')
    for row in rows:
        dn=row['diameter']['nominal_mm'];length=row['horizontal_projection']['value_mm']
        if (any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in (dn,length))
            or row.get('plan_glyph_radius_added_to_length') is not False or row.get('physical_port_verified') is not False
            or row.get('installed_whole_edge_length_mm') is not None or row.get('human_accepted') is not False
            or row['horizontal_projection'].get('installed_whole_edge_length_mm') is not None):raise ValueError('named plan scopes cannot claim unknown connector or installed length')
    return dict(status='pending',source_replay='passed',source_sha256=data['source_sha256'],graph_sha256=data['graph_sha256'],
        named_floor_approach_DN_and_plan_projection_scopes=len(rows),installed_lengths_assigned=0,
        physical_ports_verified=False,physical_values_fused=False,human_accepted=False,hil_ready=False,
        pending=['Attribute fusion and preservation, other floor interfaces, explicit axis vertical lengths and human acceptance remain separate checks'])


def validate_named_floor_riser_paths(mapping_run):
    """Replay named interface and independent device-service path anchors."""
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from match_named_riser_floor_paths import verify_output
    data=verify_output(mapping_run)
    if (data.get('status')!='source_checked_named_floor_riser_paths_attributes_pending'
        or any(data.get(k) is not False for k in ('local_graphs_mutated','physical_values_fused','physical_ports_verified','human_accepted'))
        or data.get('DN_values_assigned')!=0 or data.get('physical_lengths_assigned')!=0):raise ValueError('unsupported named floor-riser correspondence state')
    rows=data['records']
    if len(rows)!=2 or {r['system'] for r in rows}!={'supply','return'} or any(r.get('physical_port_verified') is not False or r.get('physical_length_mm') is not None
        or r.get('plan_glyph_radius_added_to_length') is not False for r in rows):raise ValueError('named floor-riser correspondence cannot claim physical ports or lengths')
    return dict(status='pending',source_replay='passed',source_sha256=data['source_sha256'],graph_sha256=data['graph_sha256'],
        named_floor_riser_path_correspondences=len(rows),physical_values_fused=False,physical_ports_verified=False,human_accepted=False,hil_ready=False,
        pending=['Other floors and named riser interfaces, horizontal attributes, explicit axis vertical lengths and human acceptance remain separate checks'])


def validate_named_risers(source,graph,policy,evidence):
    """Re-read explicit riser leader evidence; never approve a path mapping."""
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from native_named_riser_evidence import collect
    from source_readability import read_source
    source,graph,policy,evidence=map(Path,(source,graph,policy,evidence))
    actual=read(evidence);expected_code={name:sha(owner/name) for name in ('native_named_riser_evidence.py','native_dn_text_position.py','native_line_path_evidence.py','source_readability.py')}
    if actual.get('implementation_sha256')!=expected_code or actual.get('policy_sha256')!=sha(policy):raise ValueError('named riser implementation/policy binding changed')
    if actual.get('source_sha256')!=sha(source) or actual.get('graph_sha256')!=sha(graph):raise ValueError('named riser source/graph binding changed')
    doc,preflight=read_source(source);fresh=collect(doc,read(graph),read(policy),sha(source),sha(graph))
    fresh.update(policy_sha256=sha(policy),source_preflight=preflight,implementation_sha256=expected_code)
    if actual!=fresh:raise ValueError('named riser evidence does not replay exactly')
    rows=fresh['records']
    return dict(status='pending',source_replay='passed',source_sha256=sha(source),graph_sha256=sha(graph),native_named_annotations=len(rows),
        uncovered_axis_target_labels=[r['source_text']['handle'] for r in rows if r['target_kind'].startswith('axis_source_') and not r['target']['target_graph_coverage']],
        native_three_endpoint_contacts_requiring_normalization=[r['source_text']['handle'] for r in rows if r['target_kind']=='axis_source_junction'],
        graph_mutated=False,physical_values_fused=False,human_accepted=False,hil_ready=False,
        pending=['Replay historical display-leg normalization before diagnosing uncovered source targets or native three-ray contacts','Scoped identifiers and source leader targets do not accept cross-view port/path mapping or physical DN/length fusion'])


def validate_external_feed_plan_attributes(attribute_run):
    import math,sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from named_external_feed_plan_attributes import verify_output,MODE
    data=verify_output(attribute_run);rows=data['records'];known=0
    if (data.get('mode')!=MODE or data.get('status')!='source_checked_external_plan_DN_XY_attributes_not_fused'
        or not rows or len({r['mapping_id'] for r in rows})!=len(rows) or data.get('installed_whole_lengths_assigned')!=0
        or any(data.get(k) is not False for k in ('local_graphs_mutated','physical_values_fused','human_accepted','hil_ready'))):raise ValueError('unsupported external plan attribute state')
    for row in rows:
        value=row['diameter']['nominal_mm'];metric=row['horizontal_projection']
        if value is not None:
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:raise ValueError('invalid external pipe DN')
            known+=1
        if (row.get('inline_interiors_unknown') is not True or row.get('complete_horizontal_centerline_route_mm') is not None
            or row.get('installed_whole_edge_length_mm') is not None or not math.isfinite(metric['value_mm']) or metric['value_mm']<=0
            or metric.get('joint_graphic_spans_added') is not False or metric.get('inline_joint_interior_length_mm') is not None
            or any(row.get(k) is not False for k in ('whole_axis_edge_DN_selected','axis_named_DN_used_as_plan_seed','physical_ports_verified','external_ports_connected_to_each_other','physical_external_connection_verified','human_accepted'))):raise ValueError('external attributes claim unverified whole values')
    if data.get('known_DN_records')!=known or data.get('inline_length_incomplete_records')!=len(rows):raise ValueError('external attribute summary differs')
    return dict(status='pending',source_replay='passed',external_attribute_records=len(rows),known_DN_records=known,inline_length_incomplete_records=len(rows),
        hil_ready=False,human_accepted=False,pending=['Source pipe DN and XY exclude joint interiors and marker spans; complete-parent fusion, graph semantics, viewer and HIL remain separate'])


def validate_native_external_port_destinations(evidence_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from native_external_port_destination import verify_output,MODE
    data=verify_output(evidence_run);rows=data['records']
    if (data.get('mode')!=MODE or len(rows)<2 or len({r['port_id'] for r in rows})!=len(rows)
        or len({r['identifier'] for r in rows})!=len(rows) or data.get('physical_values_assigned')!=0 or data.get('new_connections_added')!=0
        or any(data.get(k) is not False for k in ('graph_mutated','common_marker_creates_pipe_connection','human_accepted','hil_ready'))
        or any(r.get('physical_port_verified') is not False or r.get('whole_edge_DN_verified') is not False or r.get('physical_length_mm') is not None for r in rows)):raise ValueError('unsupported native external port evidence')
    return dict(status='pending',source_replay='passed',separate_named_ports=len(rows),destination=data['destination'],new_connections_added=0,physical_values_assigned=0,
        hil_ready=False,human_accepted=False,pending=['Source-labelled separate boundary ports; cross-view paths, graph semantic adoption and HIL remain separate'])


def validate_named_external_boundary_paths(mapping_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from match_named_external_boundary_paths import verify_output,MODE
    data=verify_output(mapping_run);rows=data['records']
    if (data.get('mode')!=MODE or len(rows)<2 or len({r['mapping_id'] for r in rows})!=len(rows) or len({r['axis_port_id'] for r in rows})!=len(rows)
        or any(data.get(k) is not False for k in ('local_graphs_mutated','human_accepted','hil_ready')) or data.get('new_connections_added')!=0 or data.get('physical_values_assigned')!=0
        or any(r.get('external_ports_connected_to_each_other') is not False or r.get('physical_external_connection_verified') is not False
            or r.get('physical_port_verified') is not False or r.get('whole_edge_DN_assigned') is not False or r.get('physical_length_mm') is not None for r in rows)):raise ValueError('unsupported external boundary correspondence')
    return dict(status='pending',source_replay='passed',external_paths=len(rows),local_graphs_mutated=False,new_connections_added=0,physical_values_assigned=0,
        hil_ready=False,human_accepted=False,pending=['Matched original boundary routes only; graph semantic adoption, plan attributes, physical external connectivity and HIL remain separate'])


def validate_network_named_lower_plan_fusion(fusion_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from attach_network_named_lower_plan_attributes import verify_output,MODE
    audit=verify_output(fusion_run);stage=audit['stage']
    if (audit.get('mode')!=MODE or audit.get('hil_ready') is not False or audit.get('human_accepted') is not False
        or stage.get('added_prefix_scopes')!=2 or stage.get('whole_mixed_edge_values_assigned')!=0
        or stage.get('prior_topology_components_and_attributes_preserved') is not True
        or stage.get('related_HIL_confirmation_inherited') is not False):raise ValueError('unsupported named prefix fusion state')
    return dict(status='pending',source_replay='passed',prefix_scopes=2,graph_sha256=audit['output_graph_sha256'],
        hil_ready=False,human_accepted=False,pending=['Source comparison, viewer and HIL; mixed-edge and vertical physical lengths remain unknown'])


def validate_native_detail_corner_context(context_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from native_detail_corner_context import verify_output,MODE
    data=verify_output(context_run)
    frames=data.get('frames')
    if (data.get('mode')!=MODE or not isinstance(frames,list) or not frames
        or len({f.get('frame_id') for f in frames})!=len(frames)
        or any(data.get(key) is not False for key in ('graph_mutated','mapping_ready','coordinate_offsets_are_physical_lengths','human_accepted','hil_ready'))
        or any(type(data.get(key)) is not int or data[key]!=0 for key in ('connections_added','pipe_values_assigned'))):
        raise ValueError('Native frame context cannot claim pipe mapping, physical values or HIL acceptance')
    return dict(status='pending',source_replay='passed',source_annotation_frames=len(frames),
        individual_mapping_confirmed=False,new_connections_added=0,physical_values_assigned=0,
        hil_ready=False,human_accepted=False,pending=['Regional annotation context only; individual source correspondence, local topology, downstream mapping and HIL remain separate'])


def validate_named_prefix_version_bridge(bridge_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from native_named_prefix_version_bridge import verify_output,check_result
    return check_result(verify_output(bridge_run))


def validate_current_named_prefix_evidence_fusion(fusion_run):
    import sys
    owner=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
    if str(owner) not in sys.path:sys.path.insert(0,str(owner))
    from adopt_current_named_prefix_evidence import verify_output,MODE
    audit=verify_output(fusion_run);stage=audit.get('stage',{})
    if (audit.get('mode')!=MODE or stage.get('mode')!=MODE
        or stage.get('current_source_scopes')!=4
        or stage.get('prior_topology_components_and_all_attributes_preserved') is not True
        or any(stage.get(k) is not False for k in ('related_HIL_confirmation_inherited','human_accepted'))
        or any(type(stage.get(k)) is not int or stage[k]!=0 for k in ('new_mappings','new_physical_values_assigned'))):
        raise ValueError('Unsupported current named prefix fusion or changed old values')
    return dict(status='pending',source_replay='passed',current_named_prefix_source_scopes=4,
        graph_sha256=audit['output_graph_sha256'],prior_values_and_components_preserved=True,
        new_mappings=0,new_physical_values_assigned=0,hil_ready=False,human_accepted=False,
        pending=['Current source comparison, viewer and HIL; original physical unknowns remain unknown'])


def _main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('actions',help='Bounded command, feature and current-project discovery; actions --help')
    sub.add_parser('batch',help='Hash-bound plan/run/start/status/wait execution; batch --help')
    sub.add_parser('batch-release',help='Source-backed rule batch through verified publication; batch-release --help')
    sub.add_parser('hil-feedback',help='Apply confirmed HIL replies through native reconstruction, regression and publication; hil-feedback --help')
    q=sub.add_parser('plan');q.add_argument('--config',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate');q.add_argument('--run',type=Path,required=True)
    q=sub.add_parser('validate-crossview');q.add_argument('--mapping-run',type=Path,required=True);q.add_argument('--plan-graph',type=Path,required=True);q.add_argument('--iso-graph',type=Path,required=True)
    q=sub.add_parser('validate-crossview-inventory');q.add_argument('--inventory-run',type=Path,required=True)
    q=sub.add_parser('validate-anchored-floor-main-attributes');q.add_argument('--attribute-run',type=Path,required=True)
    q=sub.add_parser('validate-network-named-lower-approaches');q.add_argument('--mapping-run',type=Path,required=True)
    q=sub.add_parser('validate-native-external-destinations');q.add_argument('--evidence-run',type=Path,required=True)
    q=sub.add_parser('validate-network-named-lower-plan-attributes');q.add_argument('--attribute-run',type=Path,required=True)
    q=sub.add_parser('validate-network-named-lower-plan-fusion');q.add_argument('--fusion-run',type=Path,required=True)
    q=sub.add_parser('validate-native-external-port-destinations');q.add_argument('--evidence-run',type=Path,required=True)
    q=sub.add_parser('validate-named-external-boundary-paths');q.add_argument('--mapping-run',type=Path,required=True)
    q=sub.add_parser('validate-external-feed-plan-attributes');q.add_argument('--attribute-run',type=Path,required=True)
    q=sub.add_parser('validate-inline-joint-path-coverage');q.add_argument('--coverage-run',type=Path,required=True)
    q=sub.add_parser('validate-native-block-branches');q.add_argument('--reconstruction-run',type=Path,required=True)
    q=sub.add_parser('validate-known-rule-batch');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-wave-main-crossview-batch');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-native-main-chain-batch');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-full-plan-DN');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-attribute-template-refresh');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('validate-compound-pipe-labels');q.add_argument('--evidence-run',type=Path,required=True)
    q=sub.add_parser('validate-noncompound-main-attribute-refresh');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-cycle-gate-plan-lengths');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-cycle-gate-plan-lengths');q.add_argument('--metric-run',type=Path,required=True)
    q=sub.add_parser('validate-graph-first-attribute-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-graph-first-provider-inventory');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-graph-first-provider-inventory');q.add_argument('--inventory-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-compound-carrier-atom-origins');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('reconstruct-recovered-component-index');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-recovered-component-index');q.add_argument('--index-run',type=Path,required=True)
    q=sub.add_parser('validate-recovered-component-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-recovered-component-provider-inventory');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-recovered-component-provider-inventory');q.add_argument('--inventory-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-cohort-member-provider-inventory');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-cohort-member-provider-inventory');q.add_argument('--inventory-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-equivalent-member-plan-attributes');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-equivalent-member-plan-attributes');q.add_argument('--attribute-run',type=Path,required=True)
    q=sub.add_parser('validate-cohort-member-attribute-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-equivalent-member-bounded-batch');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-equivalent-member-bounded-batch');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-riser-header-interval-application');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('reconstruct-riser-header-provider-inventory');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-riser-header-provider-inventory');q.add_argument('--inventory-run',type=Path,required=True)
    q=sub.add_parser('validate-riser-header-interval-application');q.add_argument('--application-run',type=Path,required=True)
    q=sub.add_parser('validate-riser-header-attribute-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-compound-riser-header-members');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-compound-riser-header-members');q.add_argument('--member-run',type=Path,required=True)
    q=sub.add_parser('validate-compound-carrier-atom-origins');q.add_argument('--origin-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-native-balancing-valves');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-native-balancing-valves');q.add_argument('--valve-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-native-flange-contact-ownership');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-native-flange-contact-ownership');q.add_argument('--flange-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-native-ball-contact-owners');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-native-ball-contact-owners');q.add_argument('--owner-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-native-contact-application');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-native-contact-application');q.add_argument('--application-run',type=Path,required=True)
    q=sub.add_parser('validate-native-contact-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-contact-owner-provider-inventory');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-contact-owner-provider-inventory');q.add_argument('--inventory-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-legacy-named-provider-inventory');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-legacy-named-provider-inventory');q.add_argument('--inventory-run',type=Path,required=True)
    q=sub.add_parser('validate-native-two-arm-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-current-two-arm-routes');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-current-two-arm-routes');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-source-stable-junctions');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-source-stable-junctions');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-anchored-plan-metrics');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-anchored-plan-metrics');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-anchored-native-metric-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-member-external-routes');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-member-external-routes');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-third-arm-crossview-batch');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-third-arm-crossview-batch');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-complementary-anchor-chains');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-complementary-anchor-chains');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-anchored-terminal-branch-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-anchored-terminal-branches');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-anchored-terminal-branches');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-inherited-terminal-geometry');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-inherited-terminal-geometry');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-inherited-terminal-geometry-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('diagnose-axis-attribute-failures');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('reconstruct-axis-omission-vertical-DN');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-axis-omission-vertical-DN');q.add_argument('--dn-run',type=Path,required=True)
    q=sub.add_parser('refresh-axis-omission-DN-viewer')
    for name in ('parent','output','proof','templates'):q.add_argument('--'+name,type=Path,required=True)
    q.add_argument('--port',type=int,required=True)
    q=sub.add_parser('validate-axis-omission-DN-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-axis-continuous-source-DN');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-axis-continuous-source-DN');q.add_argument('--dn-run',type=Path,required=True)
    q=sub.add_parser('refresh-continuous-axis-DN-viewer')
    for name in ('parent','output','proof','templates'):q.add_argument('--'+name,type=Path,required=True)
    q.add_argument('--port',type=int,required=True)
    q=sub.add_parser('validate-continuous-axis-DN-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-inherited-air-vent-attributes');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-inherited-air-vent-attributes');q.add_argument('--attribute-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-multiline-main-T-DN');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('reconstruct-modelspace-pair-main-DN');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-multiline-main-T-DN');q.add_argument('--native-run',type=Path,required=True)
    q=sub.add_parser('validate-modelspace-pair-main-DN');q.add_argument('--native-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-typed-inline-attribute-DN');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-typed-inline-attribute-DN');q.add_argument('--native-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-axis-main-T-DN');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('reconstruct-plan-crossover-centrelines');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-axis-main-T-DN');q.add_argument('--native-run',type=Path,required=True)
    q=sub.add_parser('validate-plan-crossover-centrelines');q.add_argument('--native-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-nested-direct-axis-DN');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-nested-direct-axis-DN');q.add_argument('--native-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-nested-paired-axis-DN');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-nested-paired-axis-DN');q.add_argument('--native-run',type=Path,required=True)
    q=sub.add_parser('refresh-nested-direct-axis-DN-viewer');q.add_argument('--parent',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q.add_argument('--proof',type=Path,required=True);q.add_argument('--templates',type=Path,required=True);q.add_argument('--port',type=int,default=10379)
    q=sub.add_parser('refresh-axis-rule-vertical-DN-viewer');q.add_argument('--parent',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q.add_argument('--proof',type=Path,required=True);q.add_argument('--templates',type=Path,required=True);q.add_argument('--port',type=int,default=10380)
    q=sub.add_parser('refresh-typed-inline-attribute-DN-viewer');q.add_argument('--parent',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q.add_argument('--proof',type=Path,required=True);q.add_argument('--templates',type=Path,required=True);q.add_argument('--port',type=int,default=10382)
    q=sub.add_parser('refresh-multiline-main-T-DN-viewer');q.add_argument('--parent',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q.add_argument('--proof',type=Path,required=True);q.add_argument('--templates',type=Path,required=True);q.add_argument('--port',type=int,default=10383)
    q=sub.add_parser('refresh-modelspace-pair-main-DN-viewer');q.add_argument('--parent',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q.add_argument('--proof',type=Path,required=True);q.add_argument('--templates',type=Path,required=True);q.add_argument('--port',type=int,default=10384)
    q=sub.add_parser('validate-typed-inline-attribute-DN-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('validate-multiline-main-T-DN-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('validate-modelspace-pair-main-DN-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('refresh-plan-crossover-centreline-viewer');q.add_argument('--parent',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q.add_argument('--proof',type=Path,required=True);q.add_argument('--templates',type=Path,required=True);q.add_argument('--port',type=int,default=10381)
    q=sub.add_parser('validate-nested-direct-axis-DN-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('validate-axis-rule-vertical-DN-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('validate-plan-crossover-centreline-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('refresh-nested-paired-axis-DN-viewer');q.add_argument('--parent',type=Path,required=True);q.add_argument('--output',type=Path,required=True);q.add_argument('--proof',type=Path,required=True);q.add_argument('--templates',type=Path,required=True);q.add_argument('--port',type=int,default=10378)
    q=sub.add_parser('validate-nested-paired-axis-DN-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-complementary-plan-attributes');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-complementary-plan-attributes');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-complementary-attribute-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-cycle-carrier-guards');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-cycle-carrier-guards');q.add_argument('--guard-run',type=Path,required=True)
    q=sub.add_parser('validate-cycle-carrier-correction-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-guarded-cycle-provider-inventory');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-guarded-cycle-provider-inventory');q.add_argument('--inventory-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-typed-cycle-riser-batch');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-typed-cycle-riser-batch');q.add_argument('--riser-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-anchored-cycle-gate-batch');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-anchored-cycle-gate-batch');q.add_argument('--cycle-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-axis-unbranched-vertical-DN');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-axis-unbranched-vertical-DN');q.add_argument('--dn-run',type=Path,required=True)
    q=sub.add_parser('validate-alias-member-bridge-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-bridge-aware-provider-inventory');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-bridge-aware-provider-inventory');q.add_argument('--inventory-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-alias-member-inline-bridges');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-alias-member-inline-bridges');q.add_argument('--bridge-run',type=Path,required=True)
    q=sub.add_parser('validate-alias-member-interface-viewer');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-alias-aware-provider-inventory');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-alias-aware-provider-inventory');q.add_argument('--inventory-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-alias-member-circle-interfaces');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-alias-member-circle-interfaces');q.add_argument('--interface-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-bounded-main-complete-extents');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-bounded-main-complete-extents');q.add_argument('--extent-run',type=Path,required=True)
    q=sub.add_parser('validate-bounded-main-complete-extent-refresh');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-qualified-crossview-provider-inventory');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-qualified-crossview-provider-inventory');q.add_argument('--inventory-run',type=Path,required=True)
    q=sub.add_parser('reconstruct-qualified-plan-scope-extension');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-qualified-plan-scope-extension');q.add_argument('--scope-run',type=Path,required=True)
    q=sub.add_parser('validate-qualified-plan-scope-refresh');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-ordered-owner-crossview');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-ordered-owner-crossview');q.add_argument('--mapping-run',type=Path,required=True)
    q=sub.add_parser('validate-ordered-owner-plan-refresh');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('reconstruct-ordered-sideview-owners');q.add_argument('--manifest',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate-ordered-sideview-owners');q.add_argument('--owner-run',type=Path,required=True)
    q=sub.add_parser('validate-compound-member-bridges');q.add_argument('--bridge-run',type=Path,required=True)
    q=sub.add_parser('validate-compound-bridge-attribute-refresh');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('validate-axis-vertical-DN-batch');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-axis-vertical-DN-attribute-refresh');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('validate-axis-attribute-source-routing');q.add_argument('--routing-run',type=Path,required=True)
    q=sub.add_parser('validate-compound-member-interfaces');q.add_argument('--interface-run',type=Path,required=True)
    q=sub.add_parser('validate-compound-interface-attribute-refresh');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('validate-noncompound-main-extents');q.add_argument('--extent-run',type=Path,required=True)
    q=sub.add_parser('validate-compound-member-attribute-refresh');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('validate-compound-member-projections');q.add_argument('--member-run',type=Path,required=True)
    q=sub.add_parser('validate-anchor-bounded-main-batch');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-anchor-bounded-main-attribute-refresh');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('validate-ordered-anchor-branches');q.add_argument('--branch-run',type=Path,required=True)
    q=sub.add_parser('validate-ordered-branch-attribute-refresh');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('validate-ordered-group-plan-lengths');q.add_argument('--length-run',type=Path,required=True)
    q=sub.add_parser('validate-ordered-group-attribute-refresh');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('validate-confirmed-member-plan-paths');q.add_argument('--member-run',type=Path,required=True)
    q=sub.add_parser('validate-confirmed-member-attribute-refresh');q.add_argument('--bundle',type=Path,required=True)
    q=sub.add_parser('validate-confirmed-compound-lanes');q.add_argument('--lane-run',type=Path,required=True)
    q=sub.add_parser('validate-native-projection-batch');q.add_argument('--projection-run',type=Path,required=True)
    q=sub.add_parser('validate-native-named-axis-columns');q.add_argument('--column-run',type=Path,required=True)
    q=sub.add_parser('validate-native-named-interface-batch');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-projected-circle-full-plan-DN');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-plan-DN-readiness-trace');q.add_argument('--trace-run',type=Path,required=True)
    q=sub.add_parser('validate-full-batch-plan-fusion');q.add_argument('--fusion-run',type=Path,required=True)
    q=sub.add_parser('validate-inherited-full-plan-DN');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-current-circle-full-plan-DN');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-user-circle-full-plan-DN');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-confirmed-overlap-full-plan-DN');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-native-level-discovery');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-local-detail-full-plan-DN');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-main-continuity-full-plan-DN');q.add_argument('--batch-run',type=Path,required=True)
    q=sub.add_parser('validate-capped-marker-context');q.add_argument('--context-run',type=Path,required=True)
    q=sub.add_parser('validate-source-crossview');q.add_argument('--mapping-run',type=Path,required=True)
    q=sub.add_parser('validate-plan-DN');q.add_argument('--diameter-run',type=Path,required=True)
    q=sub.add_parser('validate-axis-segment-DN');q.add_argument('--diameter-run',type=Path,required=True)
    q=sub.add_parser('validate-axis-riser-DN');q.add_argument('--diameter-run',type=Path,required=True)
    q=sub.add_parser('validate-named-floor-riser-paths');q.add_argument('--mapping-run',type=Path,required=True)
    q=sub.add_parser('validate-named-riser-plan-attributes');q.add_argument('--attribute-run',type=Path,required=True)
    q=sub.add_parser('validate-touching-plan-chunks');q.add_argument('--scope-run',type=Path,required=True)
    q=sub.add_parser('validate-named-floor-segments');q.add_argument('--mapping-run',type=Path,required=True)
    q=sub.add_parser('validate-lower-floor-segments');q.add_argument('--mapping-run',type=Path,required=True)
    q=sub.add_parser('validate-upper-floor-plan-attributes');q.add_argument('--attribute-run',type=Path,required=True)
    q=sub.add_parser('validate-lower-floor-plan-attributes');q.add_argument('--attribute-run',type=Path,required=True)
    q=sub.add_parser('validate-inherited-circle-plan-attributes');q.add_argument('--attribute-run',type=Path,required=True)
    q=sub.add_parser('validate-junction-rebased-plan-attributes');q.add_argument('--attribute-run',type=Path,required=True)
    q=sub.add_parser('validate-current-paired-plan-attributes');q.add_argument('--attribute-run',type=Path,required=True)
    q=sub.add_parser('validate-known-junction-main-plan-attributes');q.add_argument('--attribute-run',type=Path,required=True)
    q=sub.add_parser('validate-known-junction-main-fusion');q.add_argument('--fusion-run',type=Path,required=True)
    q=sub.add_parser('validate-native-detail-corner-context');q.add_argument('--context-run',type=Path,required=True)
    q=sub.add_parser('validate-named-prefix-version-bridge');q.add_argument('--bridge-run',type=Path,required=True)
    q=sub.add_parser('validate-current-named-prefix-evidence-fusion');q.add_argument('--fusion-run',type=Path,required=True)
    q=sub.add_parser('validate-current-remaining-plan-scopes');q.add_argument('--scope-run',type=Path,required=True)
    q=sub.add_parser('validate-wave-rebased-plan-attributes');q.add_argument('--attribute-run',type=Path,required=True)
    q=sub.add_parser('validate-mapped-native-DN-comparison');q.add_argument('--comparison-run',type=Path,required=True)
    q=sub.add_parser('validate-wave-plan-scope-adoption');q.add_argument('--adoption-run',type=Path,required=True)
    q=sub.add_parser('validate-inherited-wave-continuity');q.add_argument('--repair-run',type=Path,required=True)
    q=sub.add_parser('validate-named-risers')
    for key in ('source','graph','policy','evidence'):q.add_argument('--'+key,type=Path,required=True)
    args=p.parse_args()
    try:
        if args.command=='reconstruct-compound-carrier-atom-origins':result=reconstruct_compound_carrier_atom_origins(args.manifest,args.output)
        elif args.command=='reconstruct-recovered-component-index':result=reconstruct_recovered_component_index(args.manifest,args.output)
        elif args.command=='validate-recovered-component-index':result=validate_recovered_component_index(args.index_run)
        elif args.command=='validate-recovered-component-viewer':result=validate_recovered_component_viewer(args.bundle)
        elif args.command=='reconstruct-recovered-component-provider-inventory':result=reconstruct_recovered_component_provider_inventory(args.manifest,args.output)
        elif args.command=='validate-recovered-component-provider-inventory':result=validate_recovered_component_provider_inventory(args.inventory_run)
        elif args.command=='reconstruct-cohort-member-provider-inventory':result=reconstruct_cohort_member_provider_inventory(args.manifest,args.output)
        elif args.command=='validate-cohort-member-provider-inventory':result=validate_cohort_member_provider_inventory(args.inventory_run)
        elif args.command=='reconstruct-equivalent-member-plan-attributes':result=reconstruct_equivalent_member_plan_attributes(args.manifest,args.output)
        elif args.command=='validate-equivalent-member-plan-attributes':result=validate_equivalent_member_plan_attributes(args.attribute_run)
        elif args.command=='validate-cohort-member-attribute-viewer':result=validate_cohort_member_attribute_viewer(args.bundle)
        elif args.command=='reconstruct-equivalent-member-bounded-batch':result=reconstruct_equivalent_member_bounded_batch(args.manifest,args.output)
        elif args.command=='validate-equivalent-member-bounded-batch':result=validate_equivalent_member_bounded_batch(args.batch_run)
        elif args.command=='reconstruct-riser-header-interval-application':result=reconstruct_riser_header_interval_application(args.manifest,args.output)
        elif args.command=='reconstruct-riser-header-provider-inventory':result=reconstruct_riser_header_provider_inventory(args.manifest,args.output)
        elif args.command=='validate-riser-header-provider-inventory':result=validate_riser_header_provider_inventory(args.inventory_run)
        elif args.command=='validate-riser-header-interval-application':result=validate_riser_header_interval_application(args.application_run)
        elif args.command=='validate-riser-header-attribute-viewer':result=validate_riser_header_attribute_viewer(args.bundle)
        elif args.command=='reconstruct-compound-riser-header-members':result=reconstruct_compound_riser_header_members(args.manifest,args.output)
        elif args.command=='validate-compound-riser-header-members':result=validate_compound_riser_header_members(args.member_run)
        elif args.command=='validate-compound-carrier-atom-origins':result=validate_compound_carrier_atom_origins(args.origin_run)
        elif args.command=='reconstruct-native-balancing-valves':result=reconstruct_native_balancing_valves(args.manifest,args.output)
        elif args.command=='validate-native-balancing-valves':result=validate_native_balancing_valves(args.valve_run)
        elif args.command=='reconstruct-native-flange-contact-ownership':result=reconstruct_native_flange_contact_ownership(args.manifest,args.output)
        elif args.command=='validate-native-flange-contact-ownership':result=validate_native_flange_contact_ownership(args.flange_run)
        elif args.command=='reconstruct-native-ball-contact-owners':result=reconstruct_native_ball_contact_owners(args.manifest,args.output)
        elif args.command=='validate-native-ball-contact-owners':result=validate_native_ball_contact_owners(args.owner_run)
        elif args.command=='reconstruct-native-contact-application':result=reconstruct_native_contact_application(args.manifest,args.output)
        elif args.command=='validate-native-contact-application':result=validate_native_contact_application(args.application_run)
        elif args.command=='validate-native-contact-viewer':result=validate_native_contact_viewer(args.bundle)
        elif args.command=='reconstruct-contact-owner-provider-inventory':result=reconstruct_contact_owner_provider_inventory(args.manifest,args.output)
        elif args.command=='validate-contact-owner-provider-inventory':result=validate_contact_owner_provider_inventory(args.inventory_run)
        elif args.command=='reconstruct-legacy-named-provider-inventory':result=reconstruct_legacy_named_provider_inventory(args.manifest,args.output)
        elif args.command=='validate-legacy-named-provider-inventory':result=validate_legacy_named_provider_inventory(args.inventory_run)
        elif args.command=='validate-native-two-arm-viewer':result=validate_native_two_arm_viewer(args.bundle)
        elif args.command=='reconstruct-current-two-arm-routes':result=reconstruct_current_two_arm_routes(args.manifest,args.output)
        elif args.command=='validate-current-two-arm-routes':result=validate_current_two_arm_routes(args.batch_run)
        elif args.command=='reconstruct-source-stable-junctions':result=reconstruct_source_stable_junctions(args.manifest,args.output)
        elif args.command=='validate-source-stable-junctions':result=validate_source_stable_junctions(args.batch_run)
        elif args.command=='reconstruct-anchored-plan-metrics':result=reconstruct_anchored_plan_metrics(args.manifest,args.output)
        elif args.command=='validate-anchored-plan-metrics':result=validate_anchored_plan_metrics(args.batch_run)
        elif args.command=='validate-anchored-native-metric-viewer':result=validate_anchored_native_metric_viewer(args.bundle)
        elif args.command=='reconstruct-member-external-routes':result=reconstruct_member_external_routes(args.manifest,args.output)
        elif args.command=='validate-member-external-routes':result=validate_member_external_routes(args.batch_run)
        elif args.command=='reconstruct-third-arm-crossview-batch':result=reconstruct_third_arm_crossview_batch(args.manifest,args.output)
        elif args.command=='validate-third-arm-crossview-batch':result=validate_third_arm_crossview_batch(args.batch_run)
        elif args.command=='reconstruct-complementary-anchor-chains':result=reconstruct_complementary_anchor_chains(args.manifest,args.output)
        elif args.command=='validate-complementary-anchor-chains':result=validate_complementary_anchor_chains(args.batch_run)
        elif args.command=='validate-anchored-terminal-branch-viewer':result=validate_anchored_terminal_branch_viewer(args.bundle)
        elif args.command=='reconstruct-anchored-terminal-branches':result=reconstruct_anchored_terminal_branches(args.manifest,args.output)
        elif args.command=='validate-anchored-terminal-branches':result=validate_anchored_terminal_branches(args.batch_run)
        elif args.command=='reconstruct-inherited-terminal-geometry':result=reconstruct_inherited_terminal_geometry(args.manifest,args.output)
        elif args.command=='validate-inherited-terminal-geometry':result=validate_inherited_terminal_geometry(args.batch_run)
        elif args.command=='validate-inherited-terminal-geometry-viewer':result=validate_inherited_terminal_geometry_viewer(args.bundle)
        elif args.command=='diagnose-axis-attribute-failures':result=diagnose_axis_attribute_failures(args.manifest,args.output)
        elif args.command=='reconstruct-axis-omission-vertical-DN':result=reconstruct_axis_omission_vertical_DN(args.manifest,args.output)
        elif args.command=='validate-axis-omission-vertical-DN':result=validate_axis_omission_vertical_DN(args.dn_run)
        elif args.command=='refresh-axis-omission-DN-viewer':result=refresh_axis_omission_DN_viewer(args.parent,args.output,args.proof,args.templates,args.port)
        elif args.command=='validate-axis-omission-DN-viewer':result=validate_axis_omission_DN_viewer(args.bundle)
        elif args.command=='reconstruct-axis-continuous-source-DN':result=reconstruct_axis_continuous_source_DN(args.manifest,args.output)
        elif args.command=='validate-axis-continuous-source-DN':result=validate_axis_continuous_source_DN(args.dn_run)
        elif args.command=='refresh-continuous-axis-DN-viewer':result=refresh_continuous_axis_DN_viewer(args.parent,args.output,args.proof,args.templates,args.port)
        elif args.command=='validate-continuous-axis-DN-viewer':result=validate_continuous_axis_DN_viewer(args.bundle)
        elif args.command=='reconstruct-inherited-air-vent-attributes':result=reconstruct_inherited_air_vent_attributes(args.manifest,args.output)
        elif args.command=='validate-inherited-air-vent-attributes':result=validate_inherited_air_vent_attributes(args.attribute_run)
        elif args.command=='reconstruct-multiline-main-T-DN':result=reconstruct_multiline_main_T_DN(args.manifest,args.output)
        elif args.command=='reconstruct-modelspace-pair-main-DN':result=reconstruct_modelspace_pair_main_DN(args.manifest,args.output)
        elif args.command=='validate-multiline-main-T-DN':result=validate_multiline_main_T_DN(args.native_run)
        elif args.command=='validate-modelspace-pair-main-DN':result=validate_modelspace_pair_main_DN(args.native_run)
        elif args.command=='reconstruct-typed-inline-attribute-DN':result=reconstruct_typed_inline_attribute_DN(args.manifest,args.output)
        elif args.command=='validate-typed-inline-attribute-DN':result=validate_typed_inline_attribute_DN(args.native_run)
        elif args.command=='reconstruct-axis-main-T-DN':result=reconstruct_axis_main_T_DN(args.manifest,args.output)
        elif args.command=='reconstruct-plan-crossover-centrelines':result=reconstruct_plan_crossover_centrelines(args.manifest,args.output)
        elif args.command=='validate-axis-main-T-DN':result=validate_axis_main_T_DN(args.native_run)
        elif args.command=='validate-plan-crossover-centrelines':result=validate_plan_crossover_centrelines(args.native_run)
        elif args.command=='reconstruct-nested-direct-axis-DN':result=reconstruct_nested_direct_axis_DN(args.manifest,args.output)
        elif args.command=='validate-nested-direct-axis-DN':result=validate_nested_direct_axis_DN(args.native_run)
        elif args.command=='reconstruct-nested-paired-axis-DN':result=reconstruct_nested_paired_axis_DN(args.manifest,args.output)
        elif args.command=='validate-nested-paired-axis-DN':result=validate_nested_paired_axis_DN(args.native_run)
        elif args.command=='refresh-nested-direct-axis-DN-viewer':result=refresh_nested_direct_axis_DN_viewer(args.parent,args.output,args.proof,args.templates,args.port)
        elif args.command=='refresh-axis-rule-vertical-DN-viewer':result=refresh_axis_rule_vertical_DN_viewer(args.parent,args.output,args.proof,args.templates,args.port)
        elif args.command=='refresh-typed-inline-attribute-DN-viewer':result=refresh_typed_inline_attribute_DN_viewer(args.parent,args.output,args.proof,args.templates,args.port)
        elif args.command=='refresh-multiline-main-T-DN-viewer':result=refresh_multiline_main_T_DN_viewer(args.parent,args.output,args.proof,args.templates,args.port)
        elif args.command=='refresh-modelspace-pair-main-DN-viewer':result=refresh_modelspace_pair_main_DN_viewer(args.parent,args.output,args.proof,args.templates,args.port)
        elif args.command=='validate-typed-inline-attribute-DN-viewer':result=validate_typed_inline_attribute_DN_viewer(args.bundle)
        elif args.command=='validate-multiline-main-T-DN-viewer':result=validate_multiline_main_T_DN_viewer(args.bundle)
        elif args.command=='validate-modelspace-pair-main-DN-viewer':result=validate_modelspace_pair_main_DN_viewer(args.bundle)
        elif args.command=='refresh-plan-crossover-centreline-viewer':result=refresh_plan_crossover_centreline_viewer(args.parent,args.output,args.proof,args.templates,args.port)
        elif args.command=='validate-nested-direct-axis-DN-viewer':result=validate_nested_direct_axis_DN_viewer(args.bundle)
        elif args.command=='validate-axis-rule-vertical-DN-viewer':result=validate_axis_rule_vertical_DN_viewer(args.bundle)
        elif args.command=='validate-plan-crossover-centreline-viewer':result=validate_plan_crossover_centreline_viewer(args.bundle)
        elif args.command=='refresh-nested-paired-axis-DN-viewer':result=refresh_nested_paired_axis_DN_viewer(args.parent,args.output,args.proof,args.templates,args.port)
        elif args.command=='validate-nested-paired-axis-DN-viewer':result=validate_nested_paired_axis_DN_viewer(args.bundle)
        elif args.command=='reconstruct-complementary-plan-attributes':result=reconstruct_complementary_plan_attributes(args.manifest,args.output)
        elif args.command=='validate-complementary-plan-attributes':result=validate_complementary_plan_attributes(args.batch_run)
        elif args.command=='validate-complementary-attribute-viewer':result=validate_complementary_attribute_viewer(args.bundle)
        elif args.command=='reconstruct-cycle-carrier-guards':result=reconstruct_cycle_carrier_guards(args.manifest,args.output)
        elif args.command=='validate-cycle-carrier-guards':result=validate_cycle_carrier_guards(args.guard_run)
        elif args.command=='validate-cycle-carrier-correction-viewer':result=validate_cycle_carrier_correction_viewer(args.bundle)
        elif args.command=='reconstruct-guarded-cycle-provider-inventory':result=reconstruct_guarded_cycle_provider_inventory(args.manifest,args.output)
        elif args.command=='validate-guarded-cycle-provider-inventory':result=validate_guarded_cycle_provider_inventory(args.inventory_run)
        elif args.command=='reconstruct-typed-cycle-riser-batch':result=reconstruct_typed_cycle_riser_batch(args.manifest,args.output)
        elif args.command=='validate-typed-cycle-riser-batch':result=validate_typed_cycle_riser_batch(args.riser_run)
        elif args.command=='reconstruct-cycle-gate-plan-lengths':result=reconstruct_cycle_gate_plan_lengths(args.manifest,args.output)
        elif args.command=='validate-cycle-gate-plan-lengths':result=validate_cycle_gate_plan_lengths(args.metric_run)
        elif args.command=='validate-graph-first-attribute-viewer':result=validate_graph_first_attribute_viewer(args.bundle)
        elif args.command=='reconstruct-graph-first-provider-inventory':result=reconstruct_graph_first_provider_inventory(args.manifest,args.output)
        elif args.command=='validate-graph-first-provider-inventory':result=validate_graph_first_provider_inventory(args.inventory_run)
        elif args.command=='reconstruct-anchored-cycle-gate-batch':result=reconstruct_anchored_cycle_gate_batch(args.manifest,args.output)
        elif args.command=='validate-anchored-cycle-gate-batch':result=validate_anchored_cycle_gate_batch(args.cycle_run)
        elif args.command=='reconstruct-axis-unbranched-vertical-DN':result=reconstruct_axis_unbranched_vertical_DN(args.manifest,args.output)
        elif args.command=='validate-axis-unbranched-vertical-DN':result=validate_axis_unbranched_vertical_DN(args.dn_run)
        elif args.command=='validate-alias-member-bridge-viewer':result=validate_alias_member_bridge_viewer(args.bundle)
        elif args.command=='reconstruct-bridge-aware-provider-inventory':result=reconstruct_bridge_aware_provider_inventory(args.manifest,args.output)
        elif args.command=='validate-bridge-aware-provider-inventory':result=validate_bridge_aware_provider_inventory(args.inventory_run)
        elif args.command=='reconstruct-alias-member-inline-bridges':result=reconstruct_alias_member_inline_bridges(args.manifest,args.output)
        elif args.command=='validate-alias-member-inline-bridges':result=validate_alias_member_inline_bridges(args.bridge_run)
        elif args.command=='validate-alias-member-interface-viewer':result=validate_alias_member_interface_viewer(args.bundle)
        elif args.command=='reconstruct-alias-aware-provider-inventory':result=reconstruct_alias_aware_provider_inventory(args.manifest,args.output)
        elif args.command=='validate-alias-aware-provider-inventory':result=validate_alias_aware_provider_inventory(args.inventory_run)
        elif args.command=='reconstruct-alias-member-circle-interfaces':result=reconstruct_alias_member_circle_interfaces(args.manifest,args.output)
        elif args.command=='validate-alias-member-circle-interfaces':result=validate_alias_member_circle_interfaces(args.interface_run)
        elif args.command=='reconstruct-bounded-main-complete-extents':result=reconstruct_bounded_main_complete_extents(args.manifest,args.output)
        elif args.command=='validate-bounded-main-complete-extents':result=validate_bounded_main_complete_extents(args.extent_run)
        elif args.command=='validate-bounded-main-complete-extent-refresh':result=validate_bounded_main_complete_extent_refresh(args.bundle)
        elif args.command=='reconstruct-qualified-crossview-provider-inventory':result=reconstruct_qualified_crossview_provider_inventory(args.manifest,args.output)
        elif args.command=='validate-qualified-crossview-provider-inventory':result=validate_qualified_crossview_provider_inventory(args.inventory_run)
        elif args.command=='reconstruct-qualified-plan-scope-extension':result=reconstruct_qualified_plan_scope_extension(args.manifest,args.output)
        elif args.command=='validate-qualified-plan-scope-extension':result=validate_qualified_plan_scope_extension(args.scope_run)
        elif args.command=='validate-qualified-plan-scope-refresh':result=validate_qualified_plan_scope_refresh(args.bundle)
        elif args.command=='reconstruct-ordered-owner-crossview':result=reconstruct_ordered_owner_crossview(args.manifest,args.output)
        elif args.command=='validate-ordered-owner-crossview':result=validate_ordered_owner_crossview(args.mapping_run)
        elif args.command=='validate-ordered-owner-plan-refresh':result=validate_ordered_owner_plan_refresh(args.bundle)
        elif args.command=='reconstruct-ordered-sideview-owners':result=reconstruct_ordered_sideview_owners(args.manifest,args.output)
        elif args.command=='validate-ordered-sideview-owners':result=validate_ordered_sideview_owners(args.owner_run)
        elif args.command=='validate-compound-member-bridges':result=validate_compound_member_bridges(args.bridge_run)
        elif args.command=='validate-compound-bridge-attribute-refresh':result=validate_compound_bridge_attribute_refresh(args.bundle)
        elif args.command=='validate-axis-vertical-DN-batch':result=validate_axis_vertical_DN_batch(args.batch_run)
        elif args.command=='validate-axis-vertical-DN-attribute-refresh':result=validate_axis_vertical_DN_attribute_refresh(args.bundle)
        elif args.command=='validate-axis-attribute-source-routing':result=validate_axis_attribute_source_routing(args.routing_run)
        elif args.command=='validate-compound-member-interfaces':result=validate_compound_member_interfaces(args.interface_run)
        elif args.command=='validate-compound-interface-attribute-refresh':result=validate_compound_interface_attribute_refresh(args.bundle)
        elif args.command=='validate-noncompound-main-attribute-refresh':result=validate_noncompound_main_attribute_refresh(args.bundle)
        elif args.command=='validate-noncompound-main-extents':result=validate_noncompound_main_extents(args.extent_run)
        elif args.command=='validate-compound-member-attribute-refresh':result=validate_compound_member_attribute_refresh(args.bundle)
        elif args.command=='validate-compound-member-projections':result=validate_compound_member_projections(args.member_run)
        elif args.command=='validate-anchor-bounded-main-attribute-refresh':result=validate_anchor_bounded_main_attribute_refresh(args.bundle)
        elif args.command=='validate-anchor-bounded-main-batch':result=validate_anchor_bounded_main_batch(args.batch_run)
        elif args.command=='validate-ordered-anchor-branches':result=validate_ordered_anchor_branches(args.branch_run)
        elif args.command=='validate-ordered-branch-attribute-refresh':result=validate_ordered_branch_attribute_refresh(args.bundle)
        elif args.command=='validate-ordered-group-plan-lengths':result=validate_ordered_group_plan_lengths(args.length_run)
        elif args.command=='validate-ordered-group-attribute-refresh':result=validate_ordered_group_attribute_refresh(args.bundle)
        elif args.command=='validate-confirmed-member-plan-paths':result=validate_confirmed_member_plan_paths(args.member_run)
        elif args.command=='validate-confirmed-member-attribute-refresh':result=validate_confirmed_member_attribute_refresh(args.bundle)
        elif args.command=='validate-confirmed-compound-lanes':result=validate_confirmed_compound_lanes(args.lane_run)
        elif args.command=='validate-native-projection-batch':result=validate_native_projection_batch(args.projection_run)
        elif args.command=='validate-native-named-axis-columns':result=validate_native_named_axis_columns(args.column_run)
        elif args.command=='validate-native-named-interface-batch':result=validate_native_named_interface_batch(args.batch_run)
        elif args.command=='validate-projected-circle-full-plan-DN':result=validate_projected_circle_full_plan_DN(args.batch_run)
        elif args.command=='validate-plan-DN-readiness-trace':
            result=validate_plan_DN_readiness_trace(args.trace_run)
        elif args.command=='plan':result=plan(args.config,args.output)
        elif args.command=='validate-crossview':result=validate_crossview(args.mapping_run,args.plan_graph,args.iso_graph)
        elif args.command=='validate-crossview-inventory':result=validate_crossview_inventory(args.inventory_run)
        elif args.command=='validate-known-rule-batch':result=validate_known_rule_batch(args.batch_run)
        elif args.command=='validate-wave-main-crossview-batch':result=validate_wave_main_crossview_batch(args.batch_run)
        elif args.command=='validate-native-main-chain-batch':result=validate_native_main_chain_batch(args.batch_run)
        elif args.command=='validate-full-plan-DN':result=validate_full_plan_DN(args.batch_run)
        elif args.command=='validate-attribute-template-refresh':result=validate_attribute_template_refresh(args.bundle)
        elif args.command=='validate-compound-pipe-labels':result=validate_compound_pipe_labels(args.evidence_run)
        elif args.command=='validate-full-batch-plan-fusion':result=validate_full_batch_plan_fusion(args.fusion_run)
        elif args.command=='validate-inherited-full-plan-DN':result=validate_inherited_full_plan_DN(args.batch_run)
        elif args.command=='validate-current-circle-full-plan-DN':result=validate_current_circle_full_plan_DN(args.batch_run)
        elif args.command=='validate-user-circle-full-plan-DN':result=validate_user_circle_full_plan_DN(args.batch_run)
        elif args.command=='validate-confirmed-overlap-full-plan-DN':result=validate_confirmed_overlap_full_plan_DN(args.batch_run)
        elif args.command=='validate-native-level-discovery':result=validate_native_level_discovery(args.batch_run)
        elif args.command=='validate-local-detail-full-plan-DN':result=validate_local_detail_full_plan_DN(args.batch_run)
        elif args.command=='validate-main-continuity-full-plan-DN':result=validate_main_continuity_full_plan_DN(args.batch_run)
        elif args.command=='validate-capped-marker-context':result=validate_capped_marker_context(args.context_run)
        elif args.command=='validate-anchored-floor-main-attributes':result=validate_anchored_floor_main_attributes(args.attribute_run)
        elif args.command=='validate-network-named-lower-approaches':result=validate_network_named_lower_approaches(args.mapping_run)
        elif args.command=='validate-native-external-destinations':result=validate_native_external_destinations(args.evidence_run)
        elif args.command=='validate-network-named-lower-plan-attributes':result=validate_network_named_lower_plan_attributes(args.attribute_run)
        elif args.command=='validate-network-named-lower-plan-fusion':result=validate_network_named_lower_plan_fusion(args.fusion_run)
        elif args.command=='validate-native-external-port-destinations':result=validate_native_external_port_destinations(args.evidence_run)
        elif args.command=='validate-named-external-boundary-paths':result=validate_named_external_boundary_paths(args.mapping_run)
        elif args.command=='validate-external-feed-plan-attributes':result=validate_external_feed_plan_attributes(args.attribute_run)
        elif args.command=='validate-inline-joint-path-coverage':result=validate_inline_joint_path_coverage(args.coverage_run)
        elif args.command=='validate-native-block-branches':result=validate_native_block_branches(args.reconstruction_run)
        elif args.command=='validate-source-crossview':result=validate_source_crossview(args.mapping_run)
        elif args.command=='validate-plan-DN':result=validate_plan_DN(args.diameter_run)
        elif args.command=='validate-axis-segment-DN':result=validate_axis_segment_DN(args.diameter_run)
        elif args.command=='validate-axis-riser-DN':result=validate_axis_riser_DN(args.diameter_run)
        elif args.command=='validate-named-floor-riser-paths':result=validate_named_floor_riser_paths(args.mapping_run)
        elif args.command=='validate-named-riser-plan-attributes':result=validate_named_riser_plan_attributes(args.attribute_run)
        elif args.command=='validate-touching-plan-chunks':result=validate_touching_plan_chunks(args.scope_run)
        elif args.command=='validate-named-floor-segments':result=validate_named_floor_segments(args.mapping_run)
        elif args.command=='validate-lower-floor-segments':result=validate_named_floor_segments(args.mapping_run,lower=True)
        elif args.command=='validate-upper-floor-plan-attributes':result=validate_upper_floor_plan_attributes(args.attribute_run)
        elif args.command=='validate-lower-floor-plan-attributes':result=validate_upper_floor_plan_attributes(args.attribute_run,lower=True)
        elif args.command=='validate-inherited-circle-plan-attributes':result=validate_inherited_circle_plan_attributes(args.attribute_run)
        elif args.command=='validate-junction-rebased-plan-attributes':result=validate_junction_rebased_plan_attributes(args.attribute_run)
        elif args.command=='validate-current-paired-plan-attributes':result=validate_current_paired_plan_attributes(args.attribute_run)
        elif args.command=='validate-known-junction-main-plan-attributes':result=validate_known_junction_main_plan_attributes(args.attribute_run)
        elif args.command=='validate-known-junction-main-fusion':result=validate_known_junction_main_fusion(args.fusion_run)
        elif args.command=='validate-native-detail-corner-context':result=validate_native_detail_corner_context(args.context_run)
        elif args.command=='validate-named-prefix-version-bridge':result=validate_named_prefix_version_bridge(args.bridge_run)
        elif args.command=='validate-current-named-prefix-evidence-fusion':result=validate_current_named_prefix_evidence_fusion(args.fusion_run)
        elif args.command=='validate-current-remaining-plan-scopes':result=validate_current_remaining_plan_scopes(args.scope_run)
        elif args.command=='validate-wave-rebased-plan-attributes':result=validate_wave_rebased_plan_attributes(args.attribute_run)
        elif args.command=='validate-mapped-native-DN-comparison':result=validate_mapped_native_DN_comparison(args.comparison_run)
        elif args.command=='validate-wave-plan-scope-adoption':result=validate_wave_plan_scope_adoption(args.adoption_run)
        elif args.command=='validate-inherited-wave-continuity':result=validate_inherited_wave_continuity(args.repair_run)
        elif args.command=='validate-named-risers':result=validate_named_risers(args.source,args.graph,args.policy,args.evidence)
        else:result=validate(args.run)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return {'failed':1,'pending':2}.get(result.get('status'),0)
    except (ValueError,KeyError,TypeError,OSError)as exc:print(json.dumps({'status':'failed','error':str(exc)},ensure_ascii=False));return 1
def main():
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='actions':
        from pipeline_actions import main as actions_main
        return actions_main(sys.argv[2:])
    if len(sys.argv)>1 and sys.argv[1]=='batch':
        from pipeline_batch_runtime import main as batch_main
        return batch_main(sys.argv[2:])
    if len(sys.argv)>1 and sys.argv[1]=='batch-release':
        from integration_batch_release import main as release_main
        return release_main(sys.argv[2:])
    if len(sys.argv)>1 and sys.argv[1]=='hil-feedback':
        from hil_feedback_pipeline import main as feedback_main
        return feedback_main(sys.argv[2:])
    if len(sys.argv)>1 and sys.argv[1]in('refresh-plan-member-contact-viewer','validate-plan-member-contact-viewer'):
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory));previous=sys.argv
        try:
            from refresh_plan_member_contacts import main as member_contact_viewer_main
            sys.argv=[previous[0],*previous[2:]]
            return member_contact_viewer_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]in('reconstruct-plan-member-contact-context','validate-plan-member-contact-context'):
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory));previous=sys.argv
        try:
            from reconstruct_plan_member_contact_context import main as member_contact_main
            sys.argv=[previous[0],*previous[2:]]
            return member_contact_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]in('refresh-inherited-branch-attribute-viewer','validate-inherited-branch-attribute-viewer'):
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory));previous=sys.argv
        try:
            from refresh_inherited_branch_attribute_entries import main as inherited_entry_viewer_main
            sys.argv=[previous[0],*previous[2:]]
            return inherited_entry_viewer_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]in('reconstruct-inherited-branch-attributes','validate-inherited-branch-attributes'):
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory));previous=sys.argv
        try:
            from reapply_inherited_branch_attribute_entries import main as inherited_branch_main
            sys.argv=[previous[0],*previous[2:]]
            return inherited_branch_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]in('refresh-plan-seeded-branch-DN-viewer','validate-plan-seeded-branch-DN-viewer'):
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory));previous=sys.argv
        try:
            from refresh_plan_seeded_axis_branch_DN import main as branch_viewer_main
            sys.argv=[previous[0],*previous[2:]]
            return branch_viewer_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]in('reconstruct-plan-seeded-axis-branch-DN','validate-plan-seeded-axis-branch-DN'):
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory));previous=sys.argv
        try:
            from reapply_plan_seeded_axis_branch_DN import main as branch_DN_main
            sys.argv=[previous[0],*previous[2:]]
            return branch_DN_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]in('reconstruct-nonnode-boundary-branches','validate-nonnode-boundary-branches','refresh-nonnode-boundary-viewer','validate-nonnode-boundary-viewer'):
        viewer='viewer'in sys.argv[1]
        directory=Path(__file__).resolve().parents[2]/('visualize-cad-pipe-topology'if viewer else'build-cad-pipe-topology')/'scripts'
        sys.path.insert(0,str(directory))
        if viewer:
            from refresh_nonnode_boundary_branches import main as boundary_main
        else:
            from reapply_nonnode_boundary_branches import main as boundary_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return boundary_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]in('reconstruct-capped-branch-correspondence','validate-capped-branch-correspondence','refresh-capped-branch-viewer','validate-capped-branch-viewer'):
        viewer='viewer'in sys.argv[1]
        directory=Path(__file__).resolve().parents[2]/('visualize-cad-pipe-topology'if viewer else'build-cad-pipe-topology')/'scripts'
        sys.path.insert(0,str(directory))
        if viewer:
            from refresh_capped_branch_correspondence import main as capped_main
        else:
            from reapply_capped_branch_correspondence import main as capped_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return capped_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]=='replay-family-source-backtest':
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory));previous=sys.argv
        try:
            from replay_family_source_backtest import main as family_backtest_main
            sys.argv=[previous[0],*previous[2:]]
            return family_backtest_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]=='build-parent-receipt-producer-policy':
        from build_parent_receipt_producer_policy import main as receipt_policy_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return receipt_policy_main()
        finally:sys.argv=previous
    if len(sys.argv)>1 and sys.argv[1] in ('refresh-received-scope-attribute-viewer','validate-received-scope-attribute-viewer'):
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from refresh_received_scope_attributes import main as received_scope_viewer_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return received_scope_viewer_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1] in ('reconstruct-received-scope-attributes','validate-received-scope-attributes'):
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from reapply_received_scope_attributes import main as received_attributes_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return received_attributes_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1] in ('refresh-reviewed-fragment-detail-viewer','validate-reviewed-fragment-detail-viewer'):
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from refresh_reviewed_fragment_detail import main as reviewed_detail_viewer_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return reviewed_detail_viewer_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1] in ('reconstruct-reviewed-fragment-detail-index','validate-reviewed-fragment-detail-index'):
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from reviewed_fragment_detail_index import main as reviewed_fragment_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return reviewed_fragment_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1] in ('reconstruct-received-circle-expression-scopes','validate-received-circle-expression-scopes'):
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from rebuild_received_circle_expression_scopes import main as received_circle_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return received_circle_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1] in ('refresh-candidate-ring-DN-viewer','validate-candidate-ring-DN-viewer'):
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from refresh_candidate_ring_DN import main as candidate_viewer_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return candidate_viewer_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1] in ('reconstruct-candidate-ring-crossview-DN','validate-candidate-ring-crossview-DN'):
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from reapply_candidate_ring_crossview_DN import main as candidate_crossview_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return candidate_crossview_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1] in ('reconstruct-alternative-ring-plan-DN','validate-alternative-ring-plan-DN'):
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from reviewed_ring_partition_candidates import main as ring_candidates_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return ring_candidates_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1] in ('reconstruct-normalized-native-junctions','validate-normalized-native-junctions','reconstruct-normalized-expression-scopes','validate-normalized-expression-scopes'):
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        if sys.argv[1].endswith('native-junctions'):
            from normalized_native_junction_evidence import main as normalized_main
        else:
            from normalized_reviewed_expression_scope import main as normalized_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return normalized_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]=='project-producer-policy':
        from project_producer_policy import main as project_policy_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return project_policy_main()
        finally:sys.argv=previous
    if len(sys.argv)>1 and sys.argv[1]=='build-producer-input-policy':
        from build_producer_input_policy import main as producer_policy_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return producer_policy_main()
        finally:sys.argv=previous
    if len(sys.argv)>1 and sys.argv[1]=='package-current-review':
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from package_current_review import main as current_review_package_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return current_review_package_main()
        finally:sys.argv=previous
    if len(sys.argv)>1 and sys.argv[1]=='restore-sealed-review-runtime':
        from restore_sealed_review_runtime import main as sealed_review_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return sealed_review_main()
        finally:sys.argv=previous
    if len(sys.argv)>1 and sys.argv[1]=='reconstruct-profiled-schematic':
        import sys
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from rebuild_profiled_schematic import main as profiled_schematic_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return profiled_schematic_main()
        finally:sys.argv=previous
    if len(sys.argv)>1 and sys.argv[1]=='build-current-attribute-reader-policy':
        from build_current_attribute_reader_policy import main as reader_policy_main
        sys.argv.pop(1);reader_policy_main();return
    if len(sys.argv)>1 and sys.argv[1]=='capture-current-readonly-inputs':
        from capture_current_readonly_inputs import main as readonly_input_main
        sys.argv.pop(1);readonly_input_main();return
    if len(sys.argv)>1 and sys.argv[1]=='capture-current-delivery-inputs':
        from capture_current_delivery_inputs import main as delivery_input_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return delivery_input_main()
        finally:sys.argv=previous
    if len(sys.argv)>1 and sys.argv[1] in ('refresh-effective-provider-viewer','validate-effective-provider-viewer'):
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from refresh_effective_provider import main as effective_provider_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return effective_provider_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]=='audit-bounded-parent-inheritance':
        from audit_bounded_parent_inheritance import main as inherited_asset_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return inherited_asset_main()
        finally:sys.argv=previous
    if len(sys.argv)>1 and sys.argv[1] in ('refresh-uniform-subroute-DN-viewer','validate-uniform-subroute-DN-viewer'):
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from refresh_uniform_subroute_DN import main as uniform_viewer_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return uniform_viewer_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1] in ('reconstruct-reviewed-uniform-subroute-DN','validate-reviewed-uniform-subroute-DN'):
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from reviewed_uniform_subroute_DN import main as uniform_subroute_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return uniform_subroute_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1] in ('refresh-reviewed-expression-group-metric-viewer','validate-reviewed-expression-group-metric-viewer'):
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from refresh_reviewed_expression_group_metrics import main as expression_group_viewer_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return expression_group_viewer_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1] in ('reconstruct-reviewed-expression-metrics','validate-reviewed-expression-metrics'):
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from reviewed_expression_metrics import main as group_metric_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return group_metric_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1] in ('reconstruct-expanded-main-seed-bend-DN','validate-expanded-main-seed-bend-DN','refresh-expanded-main-seed-bend-DN-viewer','validate-expanded-main-seed-bend-DN-viewer'):
        owner='visualize-cad-pipe-topology' if 'viewer' in sys.argv[1] else 'build-cad-pipe-topology'
        directory=Path(__file__).resolve().parents[2]/owner/'scripts'
        sys.path.insert(0,str(directory))
        if owner=='visualize-cad-pipe-topology':
            from refresh_expanded_main_seed_bend_DN import main as expanded_bend_main
        else:
            from expanded_main_seed_bend_DN import main as expanded_bend_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return expanded_bend_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1] in ('reconstruct-fragment-component-index','validate-fragment-component-index','refresh-fragment-component-viewer','validate-fragment-component-viewer'):
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        if sys.argv[1] in ('reconstruct-fragment-component-index','validate-fragment-component-index'):
            from rebuild_fragment_component_index import main as fragment_index_main
        else:
            from refresh_fragment_component_index import main as fragment_index_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return fragment_index_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1] in ('reconstruct-native-fragment-ball-contacts','validate-native-fragment-ball-contacts'):
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from rebuild_native_fragment_ball_contacts import main as fragment_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return fragment_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]in('refresh-ambiguous-layout-DN-viewer','validate-ambiguous-layout-DN-viewer'):
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from refresh_ambiguous_layout_DN import main as layout_viewer_main
        from native_projection_runtime_v1 import default_native_runtime
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            with default_native_runtime(Path(__file__).resolve().parents[2]):
                return layout_viewer_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]in('reconstruct-ambiguous-layout-DN','validate-ambiguous-layout-DN'):
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from reapply_ambiguous_layout_DN import main as layout_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return layout_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]in('reconstruct-reviewed-expression-scopes','validate-reviewed-expression-scopes'):
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from reviewed_expression_scope import main as expression_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return expression_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]in('reconstruct-reviewed-ring-plan-DN','validate-reviewed-ring-plan-DN','reconstruct-reviewed-ring-crossview-DN','validate-reviewed-ring-crossview-DN'):
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        if 'crossview'in sys.argv[1]:
            from reapply_reviewed_ring_crossview_DN import main as ring_main
        else:
            from reviewed_ring_main_partition import main as ring_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return ring_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]in('refresh-reviewed-ring-DN-viewer','validate-reviewed-ring-DN-viewer'):
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from refresh_reviewed_ring_partition_DN import main as ring_viewer_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return ring_viewer_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]in('refresh-reviewed-detail-metric-viewer','validate-reviewed-detail-metric-viewer'):
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from refresh_reviewed_detail_metrics import main as refresh_detail_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return refresh_detail_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]in('reconstruct-reviewed-source-detail-metrics','validate-reviewed-source-detail-metrics'):
        directory=Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from reviewed_source_detail_metrics import main as detail_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return detail_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]=='receive-current-review-answers':
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from receive_current_review_answers import main as receive_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return receive_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]=='merge-current-source-review-queue':
        directory=Path(__file__).resolve().parents[2]/'visualize-cad-pipe-topology/scripts'
        sys.path.insert(0,str(directory))
        from current_source_review_queue import main as queue_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return queue_main()
        finally:sys.argv=previous;sys.path.pop(0)
    if len(sys.argv)>1 and sys.argv[1]in('reuse-native-artifact','reuse-bounded-attribute-artifact','reuse-riser-provider-artifact'):
        if sys.argv[1]=='reuse-riser-provider-artifact':
            from reuse_riser_provider_artifact import main as reuse_main
        elif sys.argv[1]=='reuse-bounded-attribute-artifact':
            from reuse_attribute_native_artifact import main as reuse_main
        else:
            from reuse_verified_native_artifact import main as reuse_main
        previous=sys.argv
        try:
            sys.argv=[previous[0],*previous[2:]]
            return reuse_main()
        finally:sys.argv=previous
    # Keep parser/help and non-native planning free of runtime initialization.
    if len(sys.argv)>1 and (sys.argv[1].startswith('validate')or sys.argv[1]in('reconstruct-riser-header-interval-application','reconstruct-riser-header-provider-inventory')or sys.argv[1]in('reconstruct-compound-carrier-atom-origins','reconstruct-native-balancing-valves','reconstruct-compound-riser-header-members')or sys.argv[1]in('reconstruct-inherited-terminal-geometry','reconstruct-anchored-terminal-branches','reconstruct-complementary-plan-attributes','reconstruct-complementary-anchor-chains','reconstruct-current-two-arm-routes','reconstruct-source-stable-junctions','reconstruct-ordered-sideview-owners','reconstruct-ordered-owner-crossview','reconstruct-qualified-plan-scope-extension','reconstruct-qualified-crossview-provider-inventory','reconstruct-bounded-main-complete-extents','reconstruct-alias-member-circle-interfaces','reconstruct-alias-aware-provider-inventory','reconstruct-alias-member-inline-bridges','reconstruct-bridge-aware-provider-inventory','reconstruct-axis-unbranched-vertical-DN','reconstruct-anchored-cycle-gate-batch','reconstruct-cycle-gate-plan-lengths','reconstruct-graph-first-provider-inventory','reconstruct-typed-cycle-riser-batch','reconstruct-cycle-carrier-guards','reconstruct-guarded-cycle-provider-inventory')):
        from native_projection_runtime_v1 import default_native_runtime
        with default_native_runtime(Path(__file__).resolve().parents[2]):
            return _main()
    return _main()


if __name__=='__main__':raise SystemExit(main())
