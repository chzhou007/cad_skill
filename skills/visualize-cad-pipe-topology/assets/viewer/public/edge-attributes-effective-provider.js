import * as prior from './edge-attributes-uniform-subroute.js';
import {checkedRiserHeaderMember}from'./riser-header-member-attributes.js';
export * from './edge-attributes-uniform-subroute.js';
export function crossViewAttributeCsvValues(edge,context=null){
 const old=prior.crossViewAttributeCsvValues(edge,context),member=checkedRiserHeaderMember(edge,context);
 if(!member||member.member_kind!=='approach'||!(member.nominal_mm>0)||!(member.complete_horizontal_centerline_mm>0))return old;
 if(typeof old.diameter_nominal_mm==='number'&&old.diameter_nominal_mm>0)return old;
 return {...old,diameter_nominal_mm:member.nominal_mm,diameter_text:`DN${member.nominal_mm}`,diameter_status:'native_complete_horizontal_member_approach_DN'};
}
