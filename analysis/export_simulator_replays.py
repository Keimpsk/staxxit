"""Export saved research trajectories to simulator .staxxit v1; no simulations."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import re
from pathlib import Path
import zipfile

from gallery_export import LABELS, STRATEGIES
from run_gallery import atomic_bytes
from validate_gallery import validate_trace

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
POSITIONS = tuple((q,r) for q in range(-6,7) for r in range(-6,7)
                  if max(abs(q),abs(r),abs(q+r))<=6)
SIMULATOR_COMMIT = '6feac4bc4db75df842064e4496132a928a8706cb'
RULES = dict(allowPass=True, endOnTwoPasses=True, threefold=True, restartAtCenter=True)
SLUGS = dict(shortest_won='kortste-winst',longest_observed='langste-waargenomen',
             longest_regular='langste-reguliere',most_captures='meeste-slagzetten',
             tallest_stack='hoogste-stapel',tactical_offer='offer-terugslag',
             comeback_score='comeback-score',comeback_material='comeback-stapelcontrole')
PRIORITY = ('shortest_won','comeback_score','tallest_stack','most_captures',
            'tactical_offer','longest_regular','longest_observed','comeback_material','best_strategy')
MAX_BYTES, MAX_MOVES = 5_000_000, 20_000

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def json_bytes(value):
    return (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')

def coordinate(index):
    if type(index) is not int or not 0<=index<len(POSITIONS):
        raise ValueError(f'Invalid research board index: {index}')
    q,r=POSITIONS[index]
    return f'{q},{r}'

def convert_move(move):
    if type(move['side']) is not int or move['side'] not in (0,1):
        raise ValueError('Invalid player')
    kinds=dict(p='place',m='move',c='capture',s='split',e='exit',x='pass')
    if move['t'] not in kinds: raise ValueError('Unknown research action')
    result=dict(player='W' if move['side']==0 else 'B',kind=kinds[move['t']])
    if result['kind']!='pass': result['to']=coordinate(move['q'])
    if result['kind'] not in ('pass','place'): result['from']=coordinate(move['p'])
    if result['kind']=='split':
        if type(move['k']) is not int or not 1<=move['k']<=35:
            raise ValueError('Invalid retained lower-stack height')
        result['h1']=move['k']
    return result

def exported_result(outcome):
    if type(outcome) is not int or outcome not in range(6): raise ValueError('Invalid research outcome')
    return [dict(winner='W',ending='regular'),dict(winner='B',ending='regular'),
            dict(winner='draw',ending='regular'),dict(winner='draw',ending='repetition'),
            dict(winner=None,ending='blocked'),None][outcome]

def validate_date(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})',value):
        raise ValueError('Export date must use the simulator ISO 8601 timestamp format')
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None: raise ValueError('Export date must include a timezone')
    return value

def convert_trace(trace, source_metadata=None, date=None):
    validate_trace(trace)
    if date is None: date=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
    validate_date(date)
    cfg=trace['config']; initial=trace['snapshots'][0]
    board={coordinate(i):['W' if x=='0' else 'B' for x in stack]
           for i,stack in enumerate(initial['stacks']) if stack!='-'}
    moves=[convert_move(m) for m in trace['moves']]
    if len(moves)>MAX_MOVES: raise ValueError('Simulator move limit exceeded')
    record=dict(version=1,variant=cfg['variant'],rules=RULES.copy(),date=date,
                players=dict(W=f"Onderzoek: {STRATEGIES[cfg['white']]}",
                             B=f"Onderzoek: {STRATEGIES[cfg['black']]}"),
                initial=dict(board=board,current='W' if initial['side']==0 else 'B',
                             piecesLeft=dict(W=initial['reserve'][0],B=initial['reserve'][1])),moves=moves)
    result=exported_result(trace['outcome'])
    if result is not None: record['result']=result

    def annotate(ply, message):
        if not 1<=ply<=len(moves): raise ValueError('Comment witness is outside recorded trajectory')
        old=moves[ply-1].get('comment')
        comment=(old+' ' if old else '')+message
        if len(comment)>2000: raise ValueError('Simulator move-comment limit exceeded')
        moves[ply-1]['comment']=comment

    source_metadata=source_metadata or {}
    if moves:
        source=source_metadata.get('file_id','opgeslagen onderzoekspartij')
        annotate(1,f"Bron: {source}; seed {cfg['seed']}; partij-index {trace['game_id']}. De datum is de exportdatum; de oorspronkelijke partijtijd is niet vastgelegd.")
    for selected in source_metadata.get('selections',[]):
        category=selected['category']; player=selected.get('player',-1)
        metric={'tactical_offer':'offers','comeback_score':'comeback_score',
                'comeback_material':'comeback_material'}.get(category)
        if metric and player in (0,1):
            witness=trace['metrics'][metric][player]
            if witness is not None:
                if category=='tactical_offer':
                    message=f"Offer/terugslagmotief: stapel {witness['offered_height']} wordt geslagen door stapel {witness['attacker_height']}; twee beurten later volgt de terugslag. Dit bewijst geen bewuste opzet."
                elif category=='comeback_score':
                    message=f"Scorecomeback van de latere winnaar: achterstand {witness['field_deficit']} buitenvelden en {witness['stone_deficit']} ontsnapte stenen."
                else:
                    message=f"Materiaalcomeback: {witness['deficit']} minder gecontroleerde actieve stenen bij gelijke ontsnappingsscore. Geen bewezen verloren stelling."
                annotate(witness['ply'],message)
        if category=='tallest_stack':
            height=trace['metrics']['max_height']
            ply=next(s['ply'] for s in trace['snapshots'] if max((len(x) if x!='-' else 0 for x in s['stacks']),default=0)==height)
            if ply: annotate(ply,f'Hoogste stapel in deze partij: {height} stenen.')
    if moves and trace['outcome']==5:
        annotate(len(moves),f"Onderzoeksafbreking bij zetlimiet {cfg['limit']}; geen reguliere uitslag. De simulator toont dit als een nog lopende partij.")
    if moves and trace['outcome']==3:
        annotate(len(moves),'Onderzoeksafloop: derde herhaling. Het onderzoeksarchief registreert dit afzonderlijk; de simulator presenteert dit als remise wegens herhaling.')
    if len(json_bytes(record))>MAX_BYTES: raise ValueError('Simulator file-size limit exceeded')
    return record

def filename_for(trace, selections):
    best=min(selections,key=lambda s:PRIORITY.index(s['category']))
    slug=(f"strategie-{best['strategy']:02d}" if best['category']=='best_strategy' else SLUGS[best['category']])
    return f"{trace['config']['variant']}-{slug}.staxxit"

def make_zip(path, output, entries, date):
    timestamp=datetime.fromisoformat(date.replace('Z','+00:00')).astimezone(timezone.utc)
    stamp=(timestamp.year,timestamp.month,timestamp.day,timestamp.hour,timestamp.minute,timestamp.second)
    blob=io.BytesIO()
    with zipfile.ZipFile(blob,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for relative in sorted(entries):
            info=zipfile.ZipInfo(relative,date_time=stamp)
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            archive.writestr(info,(output/relative).read_bytes())
    atomic_bytes(path,blob.getvalue())

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog',type=Path,action='append',help='Defaults to both published galleries')
    p.add_argument('--output-dir',type=Path,default=HERE/'results'/'simulator_replays')
    p.add_argument('--date',help='ISO 8601 export timestamp; defaults to actual export time')
    a=p.parse_args()
    catalogs=a.catalog or [HERE/'results'/'gallery'/'catalog.json',HERE/'results'/'gallery_long'/'catalog.json']
    sources={path.resolve().relative_to(REPO).as_posix():digest(path) for path in catalogs}
    existing=a.output_dir/'manifest.json'
    old=json.loads(existing.read_text(encoding='utf-8')) if existing.exists() else None
    if old and old['source_catalogs']!=sources:
        raise ValueError('Different source galleries already exported here; choose another --output-dir')
    date=a.date or (old['exported_at'] if old else datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'))
    validate_date(date)
    files=[]; used=set()
    for number,path in enumerate(catalogs):
        catalog=json.loads(path.read_text(encoding='utf-8'))
        if catalog.get('schema')!='staxxit.gallery.v1' or not catalog.get('complete'):
            raise ValueError(f'Incomplete or unknown gallery: {path}')
        family='hoofd' if number==0 else ('lang' if number==1 else f'galerij-{number+1}')
        selected_by_id={}
        for selected in catalog['selections']:
            selected_by_id.setdefault(selected['file_id'],[]).append(selected)
        for entry in catalog['games']:
            source=path.parent/entry['trace_file']
            if digest(source)!=entry['sha256']: raise ValueError(f'Corrupt trace: {source}')
            trace=json.loads(source.read_text(encoding='utf-8'))
            selections=selected_by_id[entry['file_id']]
            file=f'{family}/{filename_for(trace,selections)}'
            if file in used: raise ValueError(f'Output filename collision: {file}')
            used.add(file)
            converted=convert_trace(trace,dict(file_id=entry['file_id'],selections=selections),date)
            atomic_bytes(a.output_dir/file,json_bytes(converted))
            files.append(dict(file=file,trace_file=source.resolve().relative_to(REPO).as_posix(),
                              source_sha256=entry['sha256'],sha256=digest(a.output_dir/file),
                              source_outcome=trace['outcome'],source_termination=trace['termination'],
                              source_file_id=entry['file_id'],source_catalog=path.resolve().relative_to(REPO).as_posix(),
                              moves=len(converted['moves']),variant=converted['variant'],
                              bytes=(a.output_dir/file).stat().st_size,
                              categories=[s['category'] for s in selections]))
    files.sort(key=lambda x:x['file'])
    manifest=dict(schema='staxxit.simulator_exports.v1',complete=True,exported_at=date,
                  date_semantics='Actual export timestamp; original simulation wall-clock times were not recorded.',
                  target_simulator=dict(repository='Keimpsk/staxxit-simulator',ref='feature/game-rules-and-replay',
                                        commit=SIMULATOR_COMMIT,format_version=1),
                  converter_sha256=digest(__file__),source_catalogs=sources,files=files,
                  total_files=len(files),total_moves=sum(x['moves'] for x in files))
    atomic_bytes(existing,json_bytes(manifest))
    rows=[dict(file=x['file'],variant=x['variant'],moves=x['moves'],research_ending=x['source_termination'],
               categories='; '.join(LABELS[k] for k in x['categories']),source_trace=x['trace_file']) for x in files]
    buf=io.StringIO(newline=''); writer=csv.DictWriter(buf,fieldnames=list(rows[0]),lineterminator='\n')
    writer.writeheader(); writer.writerows(rows)
    atomic_bytes(a.output_dir/'index.csv',buf.getvalue().encode('utf-8'))
    lines=['# Partijen laden in de Staxxit-simulator','',
           f'Er zijn **{len(files)} importbestanden** gemaakt uit de bewaarde partijen. Hiervoor zijn geen simulaties opnieuw uitgevoerd.','',
           '1. Open de simulatorversie van branch `feature/game-rules-and-replay`.',
           '2. Klik op het startscherm op **Load .staxxit replay**.',
           '3. Kies één `.staxxit`-bestand uit `hoofd` of `lang`.',
           '4. Gebruik **Play**, **Pause**, **Speed**, de stapknoppen of de zetlijst.', '',
           'Het ZIP-bestand bevat dezelfde importbestanden en deze index. Pak het eerst uit; laad daarna één `.staxxit`-bestand.','',
           'Het formaat is UTF-8 JSON, versie1. Een onderzoeksafbreking bij de zetlimiet blijft in de simulator een lopende partij. Een herhaling wordt als remise wegens herhaling weergegeven; de bronclassificatie blijft apart in dit manifest bewaard. De datum in het importbestand is de exportdatum.','',
           '| Bestand | Variant | Beurten | Onderzoeksafloop | Categorieën |','|---|---|---:|---|---|']
    for row in rows:
        lines.append(f"| [{row['file']}]({row['file']}) | {row['variant']} | {row['moves']} | {row['research_ending']} | {row['categories']} |")
    lines+=['','Bronformaat: [STAXXIT-FORMAT.md](https://github.com/Keimpsk/staxxit-simulator/blob/feature/game-rules-and-replay/docs/STAXXIT-FORMAT.md).',
            f"De exports zijn gericht op simulatorcommit `{SIMULATOR_COMMIT}`. De aparte `validation.json` legt de daadwerkelijk uitgevoerde simulatorcontrole vast.",'']
    atomic_bytes(a.output_dir/'README.md','\n'.join(lines).encode('utf-8'))
    make_zip(a.output_dir/'staxxit-partijen.zip',a.output_dir,[x['file'] for x in files]+['README.md','manifest.json','index.csv'],date)
    print(json.dumps(dict(files=len(files),moves=manifest['total_moves'],max_file_bytes=max(x['bytes'] for x in files),
                          output_dir=str(a.output_dir),simulations_run=0)))

if __name__=='__main__': main()
