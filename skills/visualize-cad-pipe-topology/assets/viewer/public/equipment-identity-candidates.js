// Equipment identity evidence remains separate from physical-port confirmation.
export function equipmentIdentityCandidateProperties(node){
 const labels=node?.source_label_candidates, evidence=node?.source_label_pair_evidence;
 if(node?.node_type!=='equipment'||node.identity_status!=='unresolved'||evidence?.identity_confirmed!==false||!Array.isArray(labels)||labels.length<2||labels.some(x=>typeof x!=='string'||!x.trim()))return [];
 return [['\u5019\u9009\u8bbe\u5907\u7f16\u53f7',labels.join(' / ')],['\u7f16\u53f7\u53ca\u7aef\u53e3\u72b6\u6001','\u7f16\u53f7\u5f85\u539f\u56fe\u5bf9\u7167\uff1b\u8bbe\u5907\u7aef\u53e3\u548c\u8de8\u56fe\u8fde\u63a5\u672a\u786e\u8ba4']];
}

export function equipmentIdentityResolutionProperties(node){
 const proof=node?.source_identity_evidence,record=proof?.record;
 if(node?.node_type!=='equipment'||node.identity_status!=='source_layout_identity_resolved_human_unreviewed'||proof?.rule!=='robust_rotated_caption_footprint'||proof.ports_inferred!==false||proof.human_accepted!==false||record?.new_node_id!==node.node_id||record?.source_handle!==node.source_handle||!Number.isFinite(record?.source_text_rotation))return [];
 return [['\u8bbe\u5907\u8eab\u4efd\u6765\u6e90','\u539f\u56fe\u65cb\u8f6c\u6807\u6ce8\u8303\u56f4\u5df2\u56de\u8bc1\uff08\u542b\u5b57\u5bbd\u8bef\u5dee\u68c0\u67e5\uff09'],['\u539f\u6807\u6ce8',`${record.label} [${record.source_text_handle}] / ${record.source_text_rotation}\u00b0`],['\u5386\u53f2\u8282\u70b9 ID',record.old_node_id],['\u7aef\u53e3\u4e0e\u9a8c\u6536','\u8bbe\u5907\u7aef\u53e3\u548c\u8de8\u56fe\u8fde\u63a5\u672a\u786e\u8ba4\uff1b\u4eba\u5de5\u9a8c\u6536\u5f85\u5b8c\u6210']];
}
