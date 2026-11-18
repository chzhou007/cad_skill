import assert from 'node:assert/strict';
import {renderTechnicalUpdates} from '../assets/viewer/public/review-technical-updates.mjs';
const text={title:'\u6280\u672f\u8fdb\u5c55',summary:'\u4e09\u901a\u5df2\u91cd\u5efa',scope:'\u5f85\u6620\u5c04',viewer_url:'http://127.0.0.1:10334/'};
const result=renderTechnicalUpdates([text,{...text,svg:{path:'assets/a.svg'},overview:{path:'assets/a.png'},pair:{path:'assets/pair.png'}}]);
assert.equal((result.match(/<summary>/g)||[]).length,2);
assert.equal((result.match(/<img /g)||[]).length,2);
assert.ok(!result.includes('undefined')&&!result.includes('src=""'));
for(const field of ['svg','overview','pair']){
 for(const value of [undefined,null,{}, {path:null},{path:''}]){
  const html=renderTechnicalUpdates([{...text,[field]:value}]);assert.ok(html.includes(text.title));assert.ok(!html.includes('<img '));
 }
}
assert.equal(renderTechnicalUpdates(null),'');assert.equal(renderTechnicalUpdates([null,undefined]),'');
const escaped=renderTechnicalUpdates([{title:'<script>',summary:'A&B',pair:{path:'assets/".png'}}]);
assert.ok(!escaped.includes('<script>'));assert.ok(escaped.includes('&lt;script&gt;'));assert.ok(escaped.includes('A&amp;B'));assert.ok(escaped.includes('&quot;'));
console.log('technical progress: text-only, partial/full media and escaped content passed');
