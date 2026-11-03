const zhLabel={diameter:'\u7ba1\u5f84',floor:'\u697c\u5c42\u4f4d\u7f6e',source:'\u539f\u56fe\u6807\u6ce8',unknown:'\u672a\u6807\u6ce8 / \u5f85\u6838\u5b9e',length:'\u7269\u7406\u957f\u5ea6',equipment:'\u5e73\u9762\u8bbe\u5907'};
const enLabel={diameter:'Pipe diameter',floor:'Floor location',source:'Source annotation',unknown:'Not annotated / unverified',length:'Physical length',equipment:'Plan equipment'};
export function edgeAttributeProperties(edge,data){
 const zh=data.display?.edge_attribute_language==='zh-CN',label=zh?zhLabel:enLabel;
 const rows=[];
 if(edge.pipe_diameter||edge.pipe_floor_location){
  const dn=edge.pipe_diameter?.display||label.unknown,floor=edge.pipe_floor_location?.display_zh||label.unknown;
  rows.push([label.diameter,dn],[label.floor,floor],[label.source,(edge.pipe_diameter?.observations||[]).map(o=>o.text.text+' ['+o.text.source_id+':'+o.text.handle+']').join('; ')||label.unknown]);
 }
 if(edge.presentation){
  const unknown=zh?'\u672a\u77e5':'Unknown';
  if(!rows.length)rows.push([label.diameter,edge.pipe_diameter?.display||unknown]);
  rows.push([label.length,edge.presentation.physical_length_display||unknown],[label.equipment,edge.presentation.plan_equipment_display||unknown]);
 }
 return rows;
}
export const edgeAttributeCsvFields=['diameter_nominal_mm','diameter_text','diameter_status','floor_location_text_zh','floor_location_status','physical_length_value','plan_equipment_id'];
