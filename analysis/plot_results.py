"""Plot the completed baseline and 12x12 strategy matrix; no simulations run.

Optional dependency installation:
  python -m pip install --target analysis/build/plot_packages matplotlib==3.11.2
Reproduce:
  python analysis/plot_results.py --svg analysis/results/overview.svg
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OUTCOMES = ('Wit wint', 'Zwart wint', 'Reguliere\nremise', 'Herhaling', 'Vastgelopen', 'Zetlimiet')
COLORS = {'A': '#2563a6', 'B': '#d87916'}


def read_complete(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if not data.get('complete'):
        raise ValueError(f'Incomplete results cannot be plotted: {path}')
    for item in data['results']:
        r = item['result']
        if r['games'] <= 0 or len(r['outcomes']) != 6 or sum(r['outcomes']) != r['games']:
            raise ValueError(f'Invalid outcome counts: {path}, {item["task"]["id"]}')
        if sum(r['duration']) != r['games']:
            raise ValueError(f'Invalid duration histogram: {path}, {item["task"]["id"]}')
    return data


def comma(value, decimals=1):
    return f'{value:.{decimals}f}'.replace('.', ',')


def count_label(value):
    return f'{value:,}'.replace(',', '.')


def median(hist):
    target = (sum(hist) + 1) // 2
    total = 0
    for turn, count in enumerate(hist):
        total += count
        if total >= target:
            return turn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir', type=Path, default=HERE / 'results')
    parser.add_argument('--output', type=Path, default=HERE / 'results' / 'overview.png')
    parser.add_argument('--svg', type=Path, help='Optional vector copy of the same figure')
    parser.add_argument('--dpi', type=int, default=200)
    parser.add_argument('--package-dir', type=Path, default=HERE / 'build' / 'plot_packages')
    args = parser.parse_args()
    if args.dpi < 72:
        parser.error('--dpi must be at least 72')
    if args.package_dir.exists():
        sys.path.insert(0, str(args.package_dir.resolve()))
    os.environ.setdefault('MPLCONFIGDIR', str(HERE / 'build' / 'mplconfig'))
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as exc:
        parser.error(f'{exc}. Install optional matplotlib as documented in this script.')

    baseline_path = args.results_dir / 'baseline.json'
    matrix_path = args.results_dir / 'matrix.json'
    baseline = read_complete(baseline_path)
    matrix = read_complete(matrix_path)
    if baseline['manifest']['limit'] != matrix['manifest']['limit']:
        raise ValueError('Baseline and matrix have different turn limits')
    limit = baseline['manifest']['limit']
    base = {item['task']['variant']: item['result'] for item in baseline['results']}
    if set(base) != {'A', 'B'} or len(baseline['results']) != 2:
        raise ValueError('Expected one complete baseline task per variant')
    if len(matrix['results']) != 288:
        raise ValueError('Expected the full 12x12 matrix for both variants')
    matrices = {}
    matrix_n = {}
    for variant in 'AB':
        values = np.full((12, 12), np.nan)
        counts = set()
        for item in matrix['results']:
            task, result = item['task'], item['result']
            if task['variant'] != variant:
                continue
            w, b = task['white'], task['black']
            if not (0 <= w < 12 and 0 <= b < 12) or not np.isnan(values[w, b]):
                raise ValueError('Invalid or duplicate strategy-matrix cell')
            values[w, b] = 100 * result['outcomes'][0] / result['games']
            counts.add(result['games'])
        if np.isnan(values).any() or len(counts) != 1:
            raise ValueError('Matrix must have complete coverage and equal games per cell')
        matrices[variant] = values
        matrix_n[variant] = counts.pop()

    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 11,
        'axes.titlesize': 13, 'axes.titleweight': 'bold',
        'axes.labelsize': 11, 'axes.spines.top': False,
        'axes.spines.right': False, 'svg.fonttype': 'none',
        'figure.facecolor': 'white', 'savefig.facecolor': 'white',
    })
    fig = plt.figure(figsize=(16, 12), layout='constrained')
    grid = fig.add_gridspec(3, 2, height_ratios=[1, 1.22, .14])
    outcomes_ax = fig.add_subplot(grid[0, 0])
    duration_ax = fig.add_subplot(grid[0, 1])
    heat_axes = [fig.add_subplot(grid[1, 0]), fig.add_subplot(grid[1, 1])]
    footer = fig.add_subplot(grid[2, :])
    footer.axis('off')
    fig.suptitle('Staxxit — gemeten spelverloop en plaatsingsstrategieën', fontsize=19, weight='bold')

    positions = np.arange(6)
    for i, variant in enumerate('AB'):
        r = base[variant]
        rates = 100 * np.asarray(r['outcomes']) / r['games']
        bars = outcomes_ax.bar(positions + (i - .5) * .36, rates, width=.34,
                               color=COLORS[variant], label=f'Variant {variant}', zorder=3)
        for bar, value in zip(bars, rates):
            text = comma(value, 3 if value < .1 else 2 if value < 2 else 1)
            outcomes_ax.annotate(text, (bar.get_x() + bar.get_width() / 2, value),
                                  xytext=(0, 4), textcoords='offset points', ha='center',
                                  va='bottom', fontsize=8, color='#333333')
    outcomes_ax.set_title('Nulmeting: zes afzonderlijke uitkomsten\n' +
                          ' · '.join(f'{v}: n={count_label(base[v]["games"])}' for v in 'AB'))
    outcomes_ax.set_xticks(positions, OUTCOMES, fontsize=9)
    outcomes_ax.set_ylabel('Aandeel van alle partijen (%)')
    outcomes_ax.set_ylim(0, 47)
    outcomes_ax.set_axisbelow(True)
    outcomes_ax.grid(axis='y', color='#e5e7eb')
    outcomes_ax.legend(frameon=False, loc='upper right', ncols=2)

    for variant in 'AB':
        r = base[variant]
        hist = np.asarray(r['duration'])
        if len(hist) != limit + 1:
            raise ValueError('Duration histogram length does not match the configured limit')
        duration_ax.step(np.arange(len(hist)), 100 * np.cumsum(hist) / r['games'],
                         where='post', color=COLORS[variant], linewidth=2,
                         label=f'{variant}: mediaan {median(hist)} beurten')
    duration_ax.axvline(limit, color='#6b7280', linewidth=1, linestyle=':')
    duration_ax.set_title(f'Nulmeting: cumulatieve geobserveerde duur\nZetlimiet: {limit} beurten')
    duration_ax.set_xlabel('Beurten, inclusief passen')
    duration_ax.set_ylabel('Partijen geëindigd of afgebroken (%)')
    duration_ax.set_xlim(0, limit + 5)
    duration_ax.set_ylim(0, 102)
    duration_ax.set_axisbelow(True)
    duration_ax.grid(color='#e5e7eb')
    duration_ax.legend(frameon=False, loc='lower right')

    for variant, ax in zip('AB', heat_axes):
        values = matrices[variant]
        image = ax.imshow(values, cmap='viridis', vmin=0, vmax=100, aspect='equal')
        ax.set_title(f'Variant {variant}: witwinst per strategiecombinatie\n'
                     f'n={count_label(matrix_n[variant])} per cel · zetlimiet {limit}')
        ax.set_xlabel('Plaatsingsstrategie zwart (engine-ID)')
        ax.set_ylabel('Plaatsingsstrategie wit (engine-ID)')
        ax.set_xticks(range(12))
        ax.set_yticks(range(12))
        ax.set_xticks(np.arange(-.5, 12, 1), minor=True)
        ax.set_yticks(np.arange(-.5, 12, 1), minor=True)
        ax.grid(which='minor', color='white', linewidth=.45, alpha=.6)
        ax.tick_params(which='minor', bottom=False, left=False)
        for row in range(12):
            for column in range(12):
                value = values[row, column]
                ax.text(column, row, comma(value), ha='center', va='center', fontsize=7.5,
                        color='white' if value < 57 else '#171717')
    colorbar = fig.colorbar(image, ax=heat_axes, location='right', shrink=.9, pad=.02, fraction=.025)
    colorbar.set_label('Reguliere witwinst / alle partijen (%)')
    footer.text(.5, .7,
                'Matrix: rij = wit, kolom = zwart; IDs 0–11 volgens STRATEGIES.md. '
                'Uniforme bewegingskeuze voor beide spelers.',
                ha='center', va='center', fontsize=10, color='#333333')
    footer.text(.5, .25,
                'Herhaling, vastlopen en zetlimiet zijn afzonderlijke onderzoeksaflopen. '
                'Duur betreft de afgeknotte onderzoeksprocedure; er zijn geen betrouwbaarheidsintervallen afgebeeld.',
                ha='center', va='center', fontsize=9, color='#555555')

    outputs = [args.output] + ([args.svg] if args.svg else [])
    for output in outputs:
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=args.dpi, metadata={'Creator': 'Staxxit analysis/plot_results.py'})
    plt.close(fig)
    provenance = {
        'baseline_sha256': hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
        'matrix_sha256': hashlib.sha256(matrix_path.read_bytes()).hexdigest(),
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'matplotlib_version': matplotlib.__version__, 'numpy_version': np.__version__,
        'dpi': args.dpi, 'limit': limit,
        'baseline_games': {v: base[v]['games'] for v in 'AB'},
        'matrix_games_per_cell': matrix_n,
        'outputs': [output.name for output in outputs],
        'note': 'Observed complete datasets only. No confidence intervals or inferred outcomes plotted.',
    }
    args.output.with_suffix('.provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(provenance, indent=2))


if __name__ == '__main__':
    main()
