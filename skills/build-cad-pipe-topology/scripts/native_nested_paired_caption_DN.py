"""Reuse native straddling caption geometry on a complete WCS pipe projection.

The original paired-caption reader expects modelspace LINEs. This adapter
exposes every original pipe primitive, retaining root/child provenance. It
does not learn a new offset, use DN to select a pipe, or change topology.
"""
import collections,copy,hashlib,itertools,math
import ezdxf
from confirm_crossview_paths import encode
from axis_unbranched_vertical_DN import native_items
from native_paired_caption_geometry import interior_pair,leader_claims,dot,vector
from native_repeated_branch_DN_layout import candidates
from axis_local_DN_segment_domains import locate
from pipe_annotation_attributes import source_texts,parse_dn_annotation
from calibrated_direct_dn_evidence import profile
from native_dn_text_position import supported
from native_line_path_evidence import LAYERS,_on

MODE='native_nested_paired_caption_geometry_reapplication_v1'


def collect(doc,graph,route,handles,source_hash,graph_hash):
    before=encode(graph),encode(route)
    if (not handles or len(handles)!=len(set(handles)) or graph['metadata']['source_sha256']!=source_hash
        or route['inputs']['source']['sha256']!=source_hash or route['inputs']['graph']['sha256']!=graph_hash):
        raise ValueError('unique current nested caption targets and source identities required')
    items=native_items(doc,graph);private=ezdxf.new('R2013');links={}
    for item in items:
        entity=private.modelspace().add_line(*item['XYZ'],dxfattribs={'layer':item['layer']})
        links[entity.dxf.handle]=copy.deepcopy(item)
    texts=[]
    for text in source_texts(doc,'axis',source_hash):
        entity=doc.entitydb[text['handle']]
        if entity.dxftype()=='TEXT' and supported(entity) and parse_dn_annotation(text['text']):
            texts.append(dict(text,profile=profile(doc,entity)))
    by={t['handle']:t for t in texts};targets=set(handles)
    if not targets<=by.keys():raise ValueError('target is not a supported native scalar TEXT')
    claims=leader_claims(doc,texts);pairs=[];held=[];cache={}
    for first,second in itertools.combinations(texts,2):
        hs=[first['handle'],second['handle']]
        if first['profile']!=second['profile'] or first['rotation']!=second['rotation']:continue
        height=first['profile']['height']
        if math.dist(first['position'],second['position'])>5*height:continue
        angle=math.radians(first['rotation']);axis=[math.cos(angle),math.sin(angle)]
        if abs(dot(vector(first['position'],second['position']),axis))>2*height:continue
        try:
            if any(h in claims for h in hs):raise ValueError('original F reader owns this caption')
            geometry=interior_pair(private,first,second);observations=[]
            for observation in geometry['observations']:
                text=observation['text'];h=text['handle'];item=links[observation['native_pipe']['source_LINE']]
                if item['root_handle'] is None:raise ValueError('pair is not two nested native source pipes')
                if h not in cache:cache[h]=candidates(doc,graph,text,items)
                hits=[x for x in cache[h] if x['root_handle']==item['root_handle'] and x['child_handle']==item['child_handle']]
                if len(hits)!=1 or not hits[0]['Z_coincident'] or len(hits[0]['current_graph_owners'])!=1:
                    raise ValueError('paired native source Z or graph owner not unique')
                binding=hits[0];value=parse_dn_annotation(text['text'])['nominal_mm']
                observations.append(dict(source_text={k:v for k,v in text.items() if k!='profile'},nominal_mm_candidate=value,
                    source_chain=[binding['root_handle'],binding['child_handle']],current_edge_id=binding['current_graph_owners'][0],native_binding=binding,
                    scope='native_nested_branch_annotation_only_not_whole_edge_DN',whole_edge_DN_assigned=False,human_accepted=False))
            if len({o['source_chain'][0] for o in observations})!=1:raise ValueError('paired captions span different source INSERTs')
            if {o['native_binding']['layer'] for o in observations}!=set(LAYERS.values()):raise ValueError('pair is not independent supply and return pipes')
            owner=dict(records=observations,source_sha256=source_hash,graph_sha256=graph_hash,graph_mutated=False,physical_values_fused=False,human_accepted=False)
            domains=locate(graph,owner,source_hash,graph_hash)
            # Replace private handles with a fully reversible native identity.
            for o in geometry['observations']:
                o['native_pipe']['source_item']=copy.deepcopy(links[o['native_pipe']['source_LINE']])
                for candidate in o['all_geometric_candidates']:
                    candidate['source_item']=copy.deepcopy(links[candidate['source_LINE']])
            pairs.append(dict(text_handles=hs,geometry=geometry,ownership=owner,domains=domains))
        except ValueError as exc:held.append(dict(text_handles=hs,reason=str(exc)))
    counts=collections.Counter(h for p in pairs for h in p['text_handles']);qualified=[]
    for p in pairs:
        if any(counts[h]!=1 for h in p['text_handles']):held.append(dict(text_handles=p['text_handles'],reason='caption participates in competing native pairs'))
        else:qualified.append(p)
    scopes={(s['edge_id'],s['path_index'],s['segment_index']):s for s in route['records']};records=[]
    for pair in qualified:
        owners={o['source_text']['handle']:o for o in pair['ownership']['records']}
        for domain in pair['domains']['records']:
            h=domain['text_handle']
            if h not in targets:continue
            key=domain['edge_id'],domain['segment']['path_index'],domain['segment']['segment_index'];scope=scopes[key];owner=owners[h]
            if (scope['native_source_status']!='single_source_line_covers' or scope['scope_points']!=domain['segment']['scope_points']
                or scope['direction_class']!='vertical' or len(scope['native_witnesses'])!=1):
                held.append(dict(text_handles=[h],reason='paired source lacks one original vertical routing witness'));continue
            witness=scope['native_witnesses'][0]
            if (witness['scope']!='decomposed_selected_insert' or witness['source_handle']!=owner['source_chain'][0]
                or witness['layer']!=owner['native_binding']['layer']
                or not all(_on(p,witness['start'],witness['end'],.05) for p in scope['scope_points'])):
                raise ValueError('pair native root/geometry differs from routing witness')
            records.append(dict(edge_id=key[0],path_index=key[1],segment_index=key[2],system=scope['system'],scope_points=copy.deepcopy(scope['scope_points']),
                floor_start=scope['floor_start'],floor_end=scope['floor_end'],nominal_mm=owner['nominal_mm_candidate'],
                observations=[dict(source_text=owner['source_text'],nominal_mm=owner['nominal_mm_candidate'],native_evidence=owner)],
                paired_caption_evidence=pair,native_witnesses=copy.deepcopy(scope['native_witnesses']),source='axis11_original_straddling_pair_geometry_on_nested_native_lines',
                whole_edge_DN_assigned=False,physical_length_mm=None,human_accepted=False))
    if len({(r['edge_id'],r['path_index'],r['segment_index']) for r in records})!=len(records):raise ValueError('multiple paired observations require a transition reader')
    if before!=(encode(graph),encode(route)):raise ValueError('source graph or route changed')
    return dict(mode=MODE,records=records,qualified_pairs=qualified,held_pairs=held,
        unmatched_target_text_handles=sorted(targets-{o['source_text']['handle'] for r in records for o in r['observations']}),
        all_native_pipe_items=len(items),private_pipe_projection_sha256=hashlib.sha256(encode(links)).hexdigest(),
        all_native_caption_count=len(texts),F_owned_text_handles=sorted(claims),
        original_geometry_reader_reused=True,DN_used_to_choose_pipe=False,layout_control_threshold_changed=False,
        graph_mutated=False,horizontal_values_assigned=0,physical_lengths_assigned=0,human_accepted=False)
