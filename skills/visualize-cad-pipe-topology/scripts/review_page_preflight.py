"""Check review-page data and derive progress from authoritative coverage rows."""
import argparse,hashlib,json,re
from pathlib import Path,PurePosixPath

def text(value,label,required=False):
    if not isinstance(value,str) or required and not value.strip():raise ValueError(label+' must be readable text')
    if '\ufffd' in value or any(0xd800<=ord(c)<=0xdfff for c in value):raise ValueError(label+' contains unreadable Unicode')
    return value

def media(reference,root,label,require_hash=False):
    if not isinstance(reference,dict):raise ValueError(label+' must be a media object')
    name=text(reference.get('path'),label+'.path',True);relative=PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:raise ValueError(label+' path must stay inside page root')
    path=(Path(root)/name).resolve()
    if not path.is_relative_to(Path(root).resolve()) or not path.is_file():raise ValueError(label+' media file missing or outside page root')
    expected=reference.get('sha256')
    if require_hash or expected is not None:
        if not isinstance(expected,str) or not re.fullmatch('[0-9a-f]{64}',expected) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError(label+' media SHA256 differs')

def validate_dataset(data,root):
    """Fail before publishing malformed media; do not alter any questions/answers."""
    if not isinstance(data,dict):raise ValueError('review data must be an object')
    seen=set();contexts=0;missing_optional_vectors=0
    for field in ('sections','followup_sections'):
        sections=data.get(field,[])
        if not isinstance(sections,list):raise ValueError(field+' must be an array')
        for index,s in enumerate(sections):
            label=f'{field}[{index}]'
            if not isinstance(s,dict):raise ValueError(label+' must be an object')
            text(s.get('title'),label+'.title',True)
            for key in ('description','note'):
                if key in s:text(s[key],label+'.'+key)
            questions=s.get('questions')
            if not isinstance(questions,list):raise ValueError(label+'.questions must be an array')
            if questions:media(s.get('image'),root,label+'.image',True)
            values=s.get('contexts',[])
            if not isinstance(values,list):raise ValueError(label+'.contexts must be an array')
            for ci,c in enumerate(values):
                name=f'{label}.contexts[{ci}]'
                if not isinstance(c,dict):raise ValueError(name+' must be an object')
                text(c.get('title'),name+'.title',True);media(c,root,name)
                locators=c.get('locators')
                if not isinstance(locators,list):raise ValueError(name+'.locators must be an array before renderSection')
                for li,locator in enumerate(locators):
                    if not isinstance(locator,dict):raise ValueError(name+'.locators entries must be objects')
                    text(locator.get('label'),name+f'.locators[{li}].label',True)
                    if 'description' in locator:text(locator['description'],name+f'.locators[{li}].description')
                if c.get('svg_path') is not None:media(dict(path=c['svg_path']),root,name+'.vector')
                else:missing_optional_vectors+=1
                contexts+=1
            for qi,q in enumerate(questions):
                name=f'{label}.questions[{qi}]'
                if not isinstance(q,dict):raise ValueError(name+' must be an object')
                identity=text(q.get('id'),name+'.id',True)
                if identity in seen:raise ValueError('Duplicate review question ID '+identity)
                seen.add(identity);text(q.get('text'),name+'.text',True);options=q.get('options')
                if not isinstance(options,list) or len(options)<2:raise ValueError(name+'.options needs at least two choices')
                for option in options:text(option,name+'.options choice',True)
                if len(set(options))!=len(options):raise ValueError(name+'.options contains duplicates')
                evidence=q.get('source_evidence',{})
                if not isinstance(evidence,dict):raise ValueError(name+'.source_evidence must be an object')
                if 'pair_sha256' in evidence and evidence['pair_sha256']!=s['image']['sha256']:raise ValueError(name+' Pair identity differs from displayed review image')
    return dict(status='review_page_schema_and_media_passed_not_human_acceptance',question_count=len(seen),context_count=contexts,optional_vector_absent=missing_optional_vectors,questions_or_answers_mutated=False,human_accepted=False)

def coverage_summary(coverage,rows):
    """Count mapping, native candidates and published values separately."""
    if not isinstance(coverage,dict) or not isinstance(rows,list):raise ValueError('Coverage object and row array required')
    keys=('total_plan_edges','mapped_plan_edges','published_attribute_covered_plan_edges')
    for key in keys:
        if isinstance(coverage.get(key),bool) or not isinstance(coverage.get(key),int) or coverage[key]<0:raise ValueError('Invalid coverage count '+key)
    total,mapped,published=(coverage[k] for k in keys);candidate=coverage.get('native_candidate_attribute_covered_plan_edges')
    if any(not isinstance(r,dict) for r in rows):raise ValueError('Coverage rows must be objects')
    if len(rows)!=total or len({r.get('edge_id') for r in rows})!=total or any(not isinstance(r.get('edge_id'),str) or not r['edge_id'] for r in rows):raise ValueError('Coverage edge inventory differs')
    for row in rows:
        if not isinstance(row.get('mapping_covered'),bool) or not isinstance(row.get('published_attribute_covered'),bool) or row['published_attribute_covered'] and not row['mapping_covered']:raise ValueError('Coverage row has invalid mapping/publication state')
    if sum(r['mapping_covered'] for r in rows)!=mapped or sum(r['published_attribute_covered'] for r in rows)!=published or not 0<=published<=mapped<=total:raise ValueError('Coverage counts disagree with actual rows')
    if candidate is not None:
        if isinstance(candidate,bool) or not isinstance(candidate,int) or not published<=candidate<=mapped:raise ValueError('Invalid native candidate coverage')
        if any(not isinstance(r.get('native_candidate_attribute_covered'),bool) or r['native_candidate_attribute_covered'] and not r['mapping_covered'] for r in rows) or sum(r['native_candidate_attribute_covered'] for r in rows)!=candidate:raise ValueError('Native candidate count disagrees with actual rows')
    native=f'原生候选属性{candidate}/{total}条' if candidate is not None else '原生候选属性覆盖尚未记录'
    floor=coverage.get('floor');floor_label=('一层' if floor==1 else f'{floor}层') if isinstance(floor,int) and not isinstance(floor,bool) else '当前楼层'
    native_stats=f'原生候选属性覆盖{candidate}／{total}条' if candidate is not None else '原生候选属性覆盖尚未记录'
    return dict(total=total,mapped=mapped,native_candidate=candidate,published=published,unmapped=total-mapped,
        stats=f'{floor_label}映射{mapped}／{total}条 · {native_stats} · 在线平面属性覆盖{published}／{total}条',
        text=f'{floor_label}技术映射{mapped}/{total}条平面边，{native}，在线属性{published}/{total}条；未映射{total-mapped}条。技术范围、在线发布与人工验收分别记录。',human_accepted=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--page-root',type=Path,required=True);p.add_argument('--coverage',type=Path);p.add_argument('--rows',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if bool(a.coverage)!=bool(a.rows):p.error('--coverage and --rows are required together')
    if a.output.exists():raise FileExistsError(a.output)
    data=a.dataset.read_text('utf-8-sig').strip()
    if data.startswith('window.REVIEW_CASES = '):data=data.removeprefix('window.REVIEW_CASES = ').removesuffix(';')
    result=validate_dataset(json.loads(data),a.page_root)
    if a.coverage:result['coverage']=coverage_summary(json.loads(a.coverage.read_text('utf-8-sig')),json.loads(a.rows.read_text('utf-8-sig')))
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(result['status'])

if __name__=='__main__':main()
