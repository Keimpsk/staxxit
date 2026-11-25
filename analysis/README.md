# Staxxit onderzoeksengine

Alles gebeurt op `complexity-analysis-cpp`; merge niets naar `main`.
De bestaande HTML/JavaScript-simulator wordt niet gebruikt of aangepast.

## Benodigd

- C++17-compiler met standaardbibliotheek en threads: getest met GCC 16.2.0.
- Python >=3.10, alleen standaardbibliotheek.
- PowerShell voor de gemaksscripts op Windows.

Op de onderzochte ASUS ROG Flow Z13: 16 fysieke kernen /32 logische processoren,
circa 27,65 GiB fysiek RAM. Details staan in `results/hardware.json`.
De portable compiler kwam van de officiële
[w64devkit-release](https://github.com/skeeto/w64devkit/releases/tag/v2.11.0);
het archief is met de gepubliceerde SHA-256 geverifieerd. Compiler/binaries
horen niet in Git. Geef een compilerpad via `-Compiler` of `STAXXIT_CXX`.

## Bouwen en controleren

Voer vanuit de repositoryroot uit. Stel `$Python` in op een werkende Python.

```powershell
$Python = 'python'
.\analysis\build.ps1 -Compiler 'C:\pad\naar\g++.exe'
$env:STAXXIT_CPP = (Resolve-Path .\analysis\build\staxxit.exe).Path
& $Python -m unittest discover -s analysis/tests -p 'test_*.py'
& $Python analysis/tests/differential.py --cpp $env:STAXXIT_CPP
& $Python analysis/tests/runner_audit.py --cpp $env:STAXXIT_CPP
& $Python analysis/complexity.py
& $Python analysis/tree_summary.py --self-test
& $Python analysis/benchmark.py --games 30000
```

Linux/macOS equivalent voor de build:

```bash
mkdir -p analysis/build
g++ -O3 -march=native -std=c++17 -pthread -Wall -Wextra analysis/staxxit.cpp -o analysis/build/staxxit
python3 analysis/tests/differential.py --cpp analysis/build/staxxit
python3 analysis/run_study.py --engine analysis/build/staxxit --suite baseline --threads 16
```

`-march=native` stemt de binary af op de bouwmachine. Laat dit weg voor een
binary die op andere CPU's moet werken. Steenbehoud gebruikt runtimefouten,
geen wegcompileerbare `assert`. De onderzoeksscripts zetten
`--verify-every-step` aan en controleren 18 witte+18 zwarte stenen, inclusief
voorraden, na iedere handeling en aan het einde van iedere partij.

## Reproduceren en hervatten

De volledige reeks, inclusief tests, benchmarks, selectie en onafhankelijke
vervolgexperimenten:

```powershell
.\analysis\run_all.ps1 -Python $Python -Compiler 'C:\pad\naar\g++.exe' -Threads 32
```

Een losse reeks:

```powershell
& $Python analysis/run_study.py --suite baseline --threads 32
& $Python analysis/run_study.py --suite matrix --threads 32
& $Python analysis/summarize.py
& $Python analysis/select_experiments.py
```

Standaard: 1.000.000 partijen per variant voor `baseline`, 10.000 per
geordende combinatie voor `matrix` (12x12x2=2.880.000 partijen).
De standaardseed is 20261125, zetlimiet536, chunk10.000. Zie `--help`.
`--start` in de C++-CLI kiest de eerste partij-index; threads en chunkindeling
veranderen de individuele partij niet. Willekeurigheid is uniform over
afzonderlijke legale handelingen; splitsingen op verschillende hoogtes zijn
verschillende handelingen.

Checkpoints staan atomair in `analysis/checkpoints/<run_id>/...` en worden
niet gecommit. Onderbreek met Ctrl+C en herhaal hetzelfde commando. Voltooide
chunks worden gecontroleerd en overgeslagen. Een onderbroken chunk wordt
opnieuw berekend. Manifests bevatten executable-/source-/runnerhashes,
spelinstellingen en seeds. Gewijzigde binaries/configuraties geven een eigen
run-id. De JSON-voortgang toont aantal, snelheid en geschatte resterende tijd.
Een nieuw gebouwde binary kan door buildmetadata een andere hash krijgen;
bewaar de bestaande binary als hervatten essentieel is. Compacte geaggregeerde
resultaten blijven in Git beschikbaar zonder de checkpoints.

`complete:true` en het verwachte aantal taken zijn vereist voor definitieve
rapportage. `--only` schrijft een afzonderlijk diagnostisch resultaat.
Een proefrun hoort in een eigen `--results-dir` om definitieve resultaten
niet te overschrijven.

## Bestanden en interpretatie

- `RULES.md`: exacte regels, buitenringaanname en voorlopige afbreekregels.
- `VALIDATION.md`: onafhankelijke oracle, fixtures, trajecten en herkomsthashes.
- `STRATEGIES.md`: alle scores, fasekeuzes en B-beleid.
- `METHODOLOGY.md`: steekproeven, selectie, censurering en betrouwbaarheidsintervallen.
- `COMPLEXITY.md`: exacte combinatorische bovengrenzen en bereikbaarheid.
- `REPORT.md`: resultaten en beperkingen in het Nederlands.
- `Handover.md`: voortzetten en resultaten interpreteren.
- `results/*.json`, `*.csv`: ruwe geaggregeerde tellingen, histogrammen en afleidingen.
- `results/win_matrix_A.csv`, `win_matrix_B.csv`: witwinst per geordende strategiecombinatie.

De zes uitkomstcategorieën staan steeds in volgorde witwinst, zwartwinst,
reguliere remise, herhaling, vastgelopen, zetlimiet. Die laatste drie worden
apart gehouden. Partijduur is de geobserveerde onderzoeksduur; een zetlimiet
is geen bewijs van remise. Intervallen voor uitkomstpercentages zijn
afzonderlijke Wilson95%-intervallen, zonder simultane multiple-comparisonclaim.

Strategierangschikkingen zijn verkennend en conditioneel op reguliere
beëindiging. Er staan ook scoregrenzen voor onbesliste uitkomsten bij.
De vervolgruns gebruiken onafhankelijke taak-seeds. Een winnaar tegen deze
tegenstanders is geen bewijs van een wiskundig optimale of dominante strategie.
Bereikbare cycli bewijzen dat de onbeperkte geschiedenisboom oneindig is;
de statistische schatting geldt alleen voor de afgeknotte onderzoeksboom.
