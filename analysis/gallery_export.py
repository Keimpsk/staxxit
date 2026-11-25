"""Readable, static exports of selected games. No game decisions are made here."""
from __future__ import annotations
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

STRATEGIES = ['Willekeurig','Naast eigen','Naast vijandelijke','Naast beide kleuren',
              'Weinig vijandelijke buren','Compact','Verspreid','Naar centrum',
              'Naar buitenring','Omsingelen','Eigen mobiliteit','Slag uitlokken']
LABELS = dict(shortest_won='Kortste gewonnen partij', longest_observed='Langste waargenomen partij',
              longest_regular='Langste regulier beëindigde partij', most_captures='Meeste slagzetten',
              tallest_stack='Hoogste stapel', tactical_offer='Offer- en terugslagmotief',
              comeback_score='Grootste comeback in ontsnappingsscore',
              comeback_material='Grootste comeback in stapelcontrole', best_strategy='Gewonnen voorbeeld per plaatsingsstrategie')
OUTCOMES = ['wit wint','zwart wint','reguliere remise','herhaling','twee passen','zetlimiet']
POSITIONS = [(q,r) for q in range(-6,7) for r in range(-6,7) if max(abs(q),abs(r),abs(q+r))<=6]

def outer_colors():
    colors = {}
    q,r,c = 6,0,0
    for dq,dr in [(-1,1),(-1,0),(0,-1),(1,-1),(1,0),(0,1)]:
        for j in range(6):
            colors[(q,r)] = 2 if j==0 else c
            if j: c=1-c
            q,r=q+dq,r+dr
    return colors

OUTER = outer_colors()

def text_atomic(path, value):
    from run_gallery import atomic_bytes
    atomic_bytes(path, value.encode('utf-8'))

def csv_text(rows):
    out = io.StringIO(newline='')
    if rows:
        w = csv.DictWriter(out, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    return out.getvalue()

def board_svg(snapshot, title):
    size, cx, cy = 25, 350, 300
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="700" height="625" viewBox="0 0 700 625">',
             '<rect width="700" height="625" fill="white"/>',
             f'<text x="350" y="24" text-anchor="middle" font-family="sans-serif" font-size="17">{escape(title)}</text>']
    for i,(q,r) in enumerate(POSITIONS):
        x,y=cx+size*math.sqrt(3)*(q+r/2),cy+size*1.5*r
        polygon=' '.join(f'{x+size*math.cos(math.radians(30+60*k)):.2f},{y+size*math.sin(math.radians(30+60*k)):.2f}' for k in range(6))
        color=OUTER.get((q,r),-1)
        fill={-1:'#f4f6f8',0:'#fff5da',1:'#536477',2:'#c8cdd3'}[color]
        parts.append(f'<polygon points="{polygon}" fill="{fill}" stroke="#83909b" stroke-width=".7"/>')
        stack=snapshot['stacks'][i]
        if stack!='-':
            top=stack[-1]
            parts.append(f'<circle cx="{x:.2f}" cy="{y-2:.2f}" r="15.5" fill="{"#fff" if top=="0" else "#20272e"}" stroke="#111" stroke-width="1.2"/>')
            parts.append(f'<text x="{x:.2f}" y="{y+2:.2f}" text-anchor="middle" font-family="sans-serif" font-size="12" fill="{"#111" if top=="0" else "#fff"}">{len(stack)}</text>')
        parts.append(f'<text x="{x:.2f}" y="{y+19:.2f}" text-anchor="middle" font-family="sans-serif" font-size="7" fill="{"#fff" if color==1 else "#4b5661"}">{q},{r}</text>')
    score=snapshot['scores']
    parts.append(f'<text x="350" y="575" text-anchor="middle" font-family="sans-serif" font-size="13">Wit: {score[0][0]} buitenvelden / {score[0][1]} stenen; zwart: {score[1][0]} / {score[1][1]}</text>')
    parts.append('<text x="350" y="598" text-anchor="middle" font-family="sans-serif" font-size="11">Cirkelkleur = bovensteen; getal = hoogte. Volledige stapelvolgorde staat in JSON.</text>')
    parts.append('</svg>')
    return '\n'.join(parts)+'\n'

def move_label(move):
    kind=move['t']
    if kind=='pass': return 'passen'
    if kind not in ('p','m','c','s','e'): return 'passen'
    q,r=POSITIONS[move['q']]
    target=f'({q},{r})'
    if kind=='p': return f'plaatsen op {target}'
    p=POSITIONS[move['p']]
    label={'m':'bewegen','c':'slaan','s':'splitsen','e':'ontsnappen'}[kind]
    extra=f"; onderstuk {move['k']} blijft" if kind=='s' else ''
    return f'{label} {p} → {target}{extra}'

def export_game(root, trace, selected, file_id):
    from run_gallery import write_json
    json_path=root/'games'/f'{file_id}.json'
    write_json(json_path, trace)
    c,m=trace['config'],trace['metrics']
    rows=[]
    for move, after in zip(trace['moves'],trace['snapshots'][1:]):
        p=POSITIONS[move['p']] if move['p']>=0 else ('','')
        q=POSITIONS[move['q']] if move['q']>=0 else ('','')
        rows.append(dict(ply=move['ply'], player='wit' if move['side']==0 else 'zwart',
                         action=move['t'], from_q=p[0],from_r=p[1],to_q=q[0],to_r=q[1],
                         retained_bottom=move['k'], source_height=move['source_height'],target_height=move['target_height'],
                         legal_count=move['legal_count'],white_reserve=after['reserve'][0],black_reserve=after['reserve'][1],
                         white_fields=after['scores'][0][0],black_fields=after['scores'][1][0],
                         white_escaped_stones=after['scores'][0][1],black_escaped_stones=after['scores'][1][1]))
    text_atomic(root/'games'/f'{file_id}.csv', csv_text(rows))
    lines=[f'# Partij {file_id}', '',
           f"Variant **{c['variant']}**, afloop **{OUTCOMES[trace['outcome']]}**, {m['turns']} beurten.", '',
           f"Seed `{c['seed']}`, partij-index `{trace['game_id']}`. Wit: {STRATEGIES[c['white']]}; zwart: {STRATEGIES[c['black']] }.", '',
           f"Voorraadbeleid wit/zwart: `{c['white_policy']}/{c['black_policy']}`. Ontsnappingsvoorkeur: `{c['white_escape_first']}/{c['black_escape_first']}`. Faseschema's: `{c['white_schedule']}` / `{c['black_schedule']}`.", '',
           f"Slagzetten: **{m['captures']}**. Grootste stapel: **{m['max_height']}**. Zetlimiet: {c['limit']}.", '',
           'Geselecteerd voor: '+', '.join(LABELS[s['category']] for s in selected)+'.', '',
           f'[Volledig reproduceerbaar JSON-bestand]({file_id}.json) · [Zetten als CSV]({file_id}.csv) · [Bordcoördinaten en buitenkleuren](../board.json)', '']
    if trace['outcome']>=3:
        lines += ['**Onderzoeksafbreking:** deze partij heeft geen reguliere winnaar of remise. De duur is de geobserveerde duur onder de opgegeven stopregels.', '']
    witness_plies=set()
    for s in selected:
        player=s.get('player',-1)
        metric_key={'tactical_offer':'offers','comeback_score':'comeback_score','comeback_material':'comeback_material'}.get(s['category'])
        if metric_key and player in (0,1):
            witness=m[metric_key][player]
            if witness:
                witness_plies.add(witness['ply'])
                if s['category']=='tactical_offer':
                    witness_plies.update(range(max(0,witness['ply']-1), min(m['turns'],witness['ply']+2)+1))
                lines += [f"Selectie **{LABELS[s['category']]}**, speler {'wit' if player==0 else 'zwart'}: `{json.dumps(witness, ensure_ascii=False)}`.", '']
    if any(s['category']=='tallest_stack' for s in selected):
        peak=next(s['ply'] for s in trace['snapshots'] if max((len(x) if x!='-' else 0 for x in s['stacks']),default=0)==m['max_height'])
        witness_plies.add(peak)
    witness_plies.add(m['turns'])
    for ply in sorted(witness_plies):
        snapshot=trace['snapshots'][ply]
        name=f'{file_id}-ply{ply:04d}.svg'
        text_atomic(root/'games'/name, board_svg(snapshot, f"Variant {c['variant']} — na beurt {ply}"))
        lines += [f'![Bord na beurt {ply}]({name})','']
    lines += ['## Volledig zetverloop', '', 'Coördinaten zijn axiaal: het midden is (0,0). Stapels worden in JSON van onder naar boven weergegeven; 0 is wit, 1 is zwart.', '',
              '| Beurt | Speler | Handeling | Voorraad W/Z | Buitenvelden W/Z | Ontsnapte stenen W/Z |',
              '|---:|---|---|---|---|---|']
    for move,after in zip(trace['moves'],trace['snapshots'][1:]):
        score=after['scores']
        lines.append(f"| {move['ply']} | {'wit' if move['side']==0 else 'zwart'} | {move_label(move)} | {after['reserve'][0]}/{after['reserve'][1]} | {score[0][0]}/{score[1][0]} | {score[0][1]}/{score[1][1]} |")
    text_atomic(root/'games'/f'{file_id}.md', '\n'.join(lines)+'\n')
    return dict(file_id=file_id, game_id=trace['game_id'],task_id=selected[0]['task_id'],
                trace_file=f'games/{file_id}.json',markdown_file=f'games/{file_id}.md',
                sha256=hashlib.sha256(json_path.read_bytes()).hexdigest())

def export_gallery(root, best, manifest, summaries):
    from run_gallery import write_json
    root=Path(root)
    board=dict(schema='staxxit.board.v1',coordinates='axial',stack_order='bottom-to-top',
               stone_colors={'0':'white','1':'black'},outer_colors={'-1':'inner','0':'white','1':'black','2':'neutral'},
               cells=[dict(index=i,q=q,r=r,outer=OUTER.get((q,r),-1)) for i,(q,r) in enumerate(POSITIONS)],
               directions=[[1,0],[1,-1],[0,-1],[-1,0],[-1,1],[0,1]])
    write_json(root/'board.json',board)
    grouped={}
    selections=[]
    for key,value in sorted(best.items()):
        s=value['selection']
        file_id=f"{s['variant']}-{s['task_id']}-g{s['game_id']:09d}"
        s=dict(s, file_id=file_id,trace_file=f'games/{file_id}.json',markdown_file=f'games/{file_id}.md')
        selections.append(s)
        if file_id not in grouped: grouped[file_id]=dict(trace=value['trace'],selections=[])
        grouped[file_id]['selections'].append(s)
    games=[export_game(root,v['trace'],v['selections'],file_id) for file_id,v in sorted(grouped.items())]
    catalog=dict(schema='staxxit.gallery.v1',complete=True,manifest=manifest,selections=selections,games=games,
                 board_file='board.json',board_sha256=hashlib.sha256((root/'board.json').read_bytes()).hexdigest(),
                 exporter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    write_json(root/'catalog.json',catalog)
    write_json(root/'statistics.json',dict(complete=True,manifest=manifest,results=summaries))
    rows=[]
    lines=['# Bijzondere Staxxit-partijen','',
           f"Deze galerij selecteert **{len(selections)} records uit {manifest['games']:,} daadwerkelijk gespeelde partijen** ({len(games)} verschillende partijen).",'',
           'Records gelden uitsluitend binnen deze steekproef. De volledige criteria staan in [GALLERY_METHODS.md](../../GALLERY_METHODS.md). Een offer is een waargenomen terugslagmotief; een materiaalachterstand is geen bewezen verloren positie.','']
    for variant in 'AB':
        lines += [f'## Variant {variant}', '', '| Categorie | Partij | Afloop | Beurten | Slagen | Grootste stapel |', '|---|---|---|---:|---:|---:|']
        for s in selections:
            if s['variant']!=variant: continue
            trace=grouped[s['file_id']]['trace']; m=trace['metrics']
            label=LABELS[s['category']]
            if s['category']=='best_strategy': label=f"Voorbeeld {s['strategy']}: {STRATEGIES[s['strategy']]}"
            lines.append(f"| {label} | [partij {s['game_id']}]({s['markdown_file']}) | {OUTCOMES[trace['outcome']]} | {m['turns']} | {m['captures']} | {m['max_height']} |")
            rows.append(dict(variant=variant,category=s['category'],strategy=s['strategy'],player=s['player'],
                             task_id=s['task_id'],seed=trace['config']['seed'],game_id=s['game_id'],
                             outcome=OUTCOMES[trace['outcome']],turns=m['turns'],captures=m['captures'],
                             max_height=m['max_height'],rank=json.dumps(s['rank']),trace_file=s['trace_file'],markdown_file=s['markdown_file']))
        present={s['category'] for s in selections if s['variant']==variant}
        for category in LABELS:
            if category not in present:
                lines += ['',f'Geen kwalificerende partij gevonden voor **{LABELS[category]}**.']
    lines += ['',f"Seedbasis: `{manifest['seed']}`. Zetlimiet: **{manifest['limit']}**. Configuraties: **{manifest['completed_tasks']}**. Checkpointchunks: **{manifest['chunks']}**.", '',
              '[Machineleesbare catalogus](catalog.json) · [CSV-index](index.csv) · [Geaggregeerde tellingen](statistics.json)', '']
    text_atomic(root/'README.md','\n'.join(lines))
    text_atomic(root/'index.csv',csv_text(rows))
    write_json(root/'progress.json',dict(complete=True,run_id=manifest['run_id'],completed=manifest['games'],total=manifest['games']))
    return catalog
