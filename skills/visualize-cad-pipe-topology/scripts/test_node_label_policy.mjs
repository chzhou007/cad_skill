import assert from 'node:assert/strict';
import {shouldShowNodeLabel} from '../assets/viewer/public/core.js';
for (const [labels, focused, active, count] of [[true,false,false,0],[false,true,false,0],[false,false,true,1]]) {
  assert.equal(shouldShowNodeLabel({node_label_visible:false},labels,focused,active,count),false);
  assert.equal(shouldShowNodeLabel({},labels,focused,active,count),true);
}
assert.equal(shouldShowNodeLabel({},false,false,false,0),false);
assert.equal(shouldShowNodeLabel({},false,false,true,5),false);
