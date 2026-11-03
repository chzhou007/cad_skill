const zhLabel={diameter:'\u7ba1\u5f84',floor:'\u697c\u5c42\u4f4d\u7f6e',source:'\u539f\u56fe\u6807\u6ce8',unknown:'\u672a\u6807\u6ce8 / \u5f85\u6838\u5b9e'};
export function edgeAttributeProperties(edge,data){
 if(!edge.pipe_diameter&&!edge.pipe_floor_location)return [];
 const zh=data.display?.edge_attribute_language==='zh-CN',label=zh?zhLabel:{diameter:'Pipe diameter',floor:'Floor location',source:'Source annotation',unknown:'Not annotated / unverified'};
 const dn=edge.pipe_diameter?.display||label.unknown,floor=edge.pipe_floor_location?.display_zh||label.unknown;
 return [[label.diameter,dn],[label.floor,floor],[label.source,(edge.pipe_diameter?.observations||[]).map(o=>o.text.text+' ['+o.text.source_id+':'+o.text.handle+']').join('; ')||label.unknown]];
}
export const edgeAttributeCsvFields=['diameter_nominal_mm','diameter_text','diameter_status','floor_location_text_zh','floor_location_status'];
