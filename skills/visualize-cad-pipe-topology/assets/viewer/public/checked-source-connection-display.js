import {checkedInheritedEntryDN} from './inherited-branch-entries-DN.js';
import {checkedPlanBranchDN} from './plan-seeded-branch-DN.js';
export function checkedLocalConnectionEvidence(edge,context,old){
 const r=checkedInheritedEntryDN(edge,context,old);
 if(r?.kind==='branch'&&r.whole_physical_DN_complete)return r;
 const inherited=checkedPlanBranchDN(edge,context,old);
 return inherited?.whole_physical_DN_complete?inherited:null;
}
export function localConnectionDescription(edge,context,old,zh,fallback){
 if(!checkedLocalConnectionEvidence(edge,context,old))return fallback;
 return zh?'\u4e3b\u7ba1\u4e09\u901a\u53ca\u672c\u652f\u8def\u5df2\u63d0\u4f9b\u6e90\u56fe\u56de\u8bc1\uff1b\u672b\u7aef\u8bbe\u5907\u4e2a\u4f53\u5bf9\u5e94\u548c\u4eba\u5de5\u9a8c\u6536\u5206\u522b\u8bb0\u5f55':'Native evidence covers the main T and this branch; terminal identity and human acceptance have separate status';
}
export function localConnectionProperties(edge,context,old,zh,rows){
 const r=checkedLocalConnectionEvidence(edge,context,old);if(!r)return rows;
 return rows.map(([k,v])=>k==='\u5c40\u90e8\u8bc1\u636e\u72b6\u6001'||k==='Local evidence status'?
  [zh?'\u539f\u59cbLINE\u8986\u76d6\u72b6\u6001':'Raw LINE coverage status',zh?'\u4fdd\u7559\u539f\u59cb\u6e90\u7ebf\u672a\u5b8c\u6574\u8986\u76d6\u7684\u8bb0\u5f55\uff1b\u8fde\u63a5\u53e6\u7531\u539f\u5f52\u4e00\u5316\u4e0e\u4e09\u901a\u89c4\u5219\u56de\u8bc1\uff0c\u7269\u7406\u957f\u5ea6\u4ecd\u672a\u77e5':'Original incomplete LINE coverage retained; connectivity has separate normalization/T evidence and physical length remains unknown']:[k,v]);
}
