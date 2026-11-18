export function crossbarCandidateProperties(node) {
 const c=node.source_crossbar_candidate;
 if(!c || c.hydraulic_change!==false || !["source_shape_role_pending","mixed_source_shape_role_pending"].includes(c.status)) return [];
 return [["\u6e90\u6a2a\u7ebf\u5019\u9009\u7ec4",c.group_id],["\u539f\u56fe\u7ebf\u53e5\u67c4",c.source_line_handle+" / "+c.branch_line_handle],["\u540c\u7ec4\u8282\u70b9",[c.tee_id,...c.terminal_node_ids].join("\u3001")],["\u6e90\u7cfb\u7edf\u5173\u7cfb",c.mixed_source_contact?"\u4f9b\u56de\u6c34\u6e90\u5c42\u51b2\u7a81\uff0c\u5f85\u6838":"\u540c\u7cfb\u7edf\uff0c\u56fe\u5f62\u542b\u4e49\u5f85\u6838"],["\u56fe\u5f62\u542b\u4e49","\u672a\u786e\u8ba4\uff1b\u672a\u636e\u6b64\u6539\u53d8\u8fde\u63a5"]];
}
