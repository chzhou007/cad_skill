"""Measure actual before/after interface payloads, never infer model billing.

An operator supplies comparable payload files and separate correctness evidence.
Text tokens use an explicitly named optional tokenizer; byte metrics always work.
"""
import argparse
import hashlib
import json
from pathlib import Path


def read_pin(row,base):
    path=Path(row['path'])
    if not path.is_absolute():path=base/path
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if row.get('sha256')!=digest:raise ValueError('measurement input hash changed: '+str(path))
    return path,raw,digest


def measure(manifest_path,output,encoding=None):
    manifest_path=Path(manifest_path).resolve();data=json.loads(manifest_path.read_text('utf-8-sig'))
    if data.get('schema_version')!=1 or not data.get('comparisons'):raise ValueError('nonempty comparison manifest required')
    encode=None
    if encoding:
        import tiktoken
        encode=tiktoken.get_encoding(encoding).encode
    seen=set();rows=[]
    for row in data['comparisons']:
        ident=row.get('id')
        if not ident or ident in seen:raise ValueError('unique comparison IDs required')
        seen.add(ident);result={'id':ident,'meaning':row.get('meaning'),'correctness_evidence':[]}
        for side in ('before','after'):
            paths=row.get(side)
            if not isinstance(paths,list)or not paths:raise ValueError('explicit payload files required')
            payloads=[];pins=[]
            for pin in paths:
                path,raw,digest=read_pin(pin,manifest_path.parent)
                payloads.append(raw.decode('utf-8-sig',errors='strict'))
                pins.append({'path':str(path),'sha256':digest,'bytes':len(raw)})
            # Record per-message tokens; no invented system prompt or model context.
            result[side]={'files':pins,'messages':len(paths),'utf8_bytes':sum(x['bytes']for x in pins),
                          'characters':sum(len(x)for x in payloads),
                          'text_tokens':sum(len(encode(x,disallowed_special=()))for x in payloads)if encode else None}
        for pin in row.get('correctness_evidence',[]):
            path,_,digest=read_pin(pin,manifest_path.parent)
            result['correctness_evidence'].append({'path':str(path),'sha256':digest})
        for metric in ('utf8_bytes','characters','text_tokens'):
            before=result['before'][metric];after=result['after'][metric]
            result[metric+'_reduction_fraction']=(1-after/before)if before else None
        rows.append(result)
    report={'schema_version':1,'manifest':{'path':str(manifest_path),'sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest()},
            'tokenizer':encoding,'text_token_scope':'explicit interface payloads only',
            'actual_model_usage_measured':False,'billing_savings_measured':False,
            'correctness_not_inferred_from_smaller_payload':True,'comparisons':rows}
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--tokenizer')
    args=p.parse_args(argv)
    try:
        result=measure(args.manifest,args.output,args.tokenizer)
        print(json.dumps({'status':'measured','report':str(args.output),'comparisons':len(result['comparisons']),
                          'tokenizer':args.tokenizer,'actual_model_usage_measured':False},ensure_ascii=False));return 0
    except (OSError,ValueError,KeyError,ImportError)as e:
        print(json.dumps({'status':'failed','error':str(e)},ensure_ascii=False));return 1

if __name__=='__main__':raise SystemExit(main())
