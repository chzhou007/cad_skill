import assert from 'node:assert/strict';
import {checkedOmissionVerticalDN,omissionVerticalDNProperties,omissionVerticalDNCsvValues} from '../assets/viewer/public/omission-vertical-DN.js';
import {edgeAttributeCsvFields as completeFields} from '../assets/viewer/public/edge-attributes-omission-vertical.js';
import {edgeAttributeCsvFields as previousFields} from '../assets/viewer/public/edge-attributes-terminal-branches.js';
import {omissionVerticalDNCsvFields} from '../assets/viewer/public/omission-vertical-DN.js';
assert.deepEqual(completeFields.slice(0,-3),previousFields.filter(k=>!omissionVerticalDNCsvFields.includes(k)));
assert.deepEqual(completeFields.slice(-3),omissionVerticalDNCsvFields);
const h='a'.repeat(64),e={edge_id:'E',system:'supply',attribute_paths:[[[0,0],[0,10]],[[20,0],[20,10]]]};
const r={edge_id:'E',path_index:0,segment_index:0,scope_points:[[0,0],[0,10]],system:'supply',nominal_mm:80,axis_source_sha256:h,seed_domain:{edge_id:'E',path_index:1,segment_index:0,nominal_mm:80},seed_text_handles:['DN01'],physical_length_mm:null,whole_edge_DN_assigned:false,related_HIL_confirmation_inherited:false,human_accepted:false,omission:{source:'original_native_omission_pair_replayed',physical_T_crossed:false,inline_joint_crossed:false,physical_length_mm:null,marker_chains:[['A','B'],['A','C']]}};
const c={current_rendered_graph_sha256:h,omission_vertical_DN:{mode:'qualified_native_omission_vertical_DN_context_v1',records:[r],count:1,raw_graph_changed:false,physical_lengths_assigned:0,whole_edge_DN_assigned:0,human_accepted:false,source_bindings:{native_source:h,native_graph:h,native_proof:h,rendered_graph:h}}};
assert.equal(checkedOmissionVerticalDN(e,c).length,1);
assert.equal(omissionVerticalDNCsvValues(e,c).axis_omission_vertical_DN_segment_count,1);
assert(omissionVerticalDNProperties(e,true,c).some(p=>p[0].includes('管径')&&p[1]==='DN80'));
assert(omissionVerticalDNProperties(e,true,c).some(p=>p[1].includes('未知')));
for(const variant of ['system','scope','seed','hash','length','T','duplicate','HIL']){
 const x=structuredClone(c),a=x.omission_vertical_DN.records[0];
 if(variant==='system')a.system='return';
 if(variant==='scope')a.scope_points[1][0]=1;
 if(variant==='seed')a.seed_domain.path_index=0;
 if(variant==='hash')x.current_rendered_graph_sha256='b'.repeat(64);
 if(variant==='length')a.physical_length_mm=0;
 if(variant==='T')a.omission.physical_T_crossed=true;
 if(variant==='duplicate'){x.omission_vertical_DN.records.push(structuredClone(a));x.omission_vertical_DN.count=2;}
 if(variant==='HIL')a.related_HIL_confirmation_inherited=true;
 assert.deepEqual(checkedOmissionVerticalDN(e,x),[],variant);
 assert.deepEqual(omissionVerticalDNCsvValues(e,x),{},variant);
}
console.log('Native omission vertical DN reader positive, Chinese and eight invalidation controls passed');
