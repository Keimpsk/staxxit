# Bijzondere partijen: automatisch bewaard en nagespeeld

De engine bewaart nu automatisch opvallende partijen. De registratie is getest
en daadwerkelijk gebruikt voor een nieuwe reeks van **4.880.000 partijen**:
1.000.000 willekeurige partijen per variant en 10.000 partijen voor ieder
geordend paar van twaalf plaatsingsstrategieën per variant. Daaruit zijn
40 records/partijdossiers geselecteerd. De 24 voorbeelden voor de twaalf
plaatsingsstrategieën komen uitsluitend uit de gebalanceerde strategiematrix.

Open de [hoofdgalerij](results/gallery/README.md). Ieder dossier bevat de
volledige zetten, een borddiagram op relevante momenten, alle tussenstanden,
de uitslag, instellingen en seeds. Er zijn bestanden in Markdown, JSON,
CSV en SVG. Het [machineleesbare register](results/gallery/catalog.json)
legt de categorieën en bestandscontrolesommen vast.

## Gevonden voorbeelden

Alle waarden hieronder zijn records binnen de geregistreerde steekproef,
geen bewezen theoretische extremen. Een beurt is één handeling van één speler.

| Categorie | Variant A | Variant B |
|---|---:|---:|
| Kortste gewonnen partij | [64 beurten](results/gallery/games/A-matrix_A_w09_b06-g000004907.md) | [63 beurten](results/gallery/games/B-matrix_B_w08_b05-g000002508.md) |
| Meeste slagzetten | [56, afgebroken bij de zetlimiet](results/gallery/games/A-baseline_A-g000397409.md) | [55, regulier gewonnen](results/gallery/games/B-matrix_B_w11_b07-g000006782.md) |
| Hoogste stapel | [35 stenen](results/gallery/games/A-matrix_A_w10_b05-g000002222.md) | [35 stenen](results/gallery/games/B-baseline_B-g000802613.md) |
| Scorecomeback | [0–6 buitenvelden achter, uiteindelijk 6–6 en winst op stenen: 20–6](results/gallery/games/A-matrix_A_w01_b08-g000006701.md) | [0–5 buitenvelden achter, uiteindelijk 6–5 gewonnen](results/gallery/games/B-matrix_B_w05_b08-g000001749.md) |
| Offer- en terugslagmotief | [Een stapel van 12 laten slaan door een stapel van 10 en onmiddellijk terugslaan](results/gallery/games/A-baseline_A-g000750520.md) | [Een stapel van 14 laten slaan door een stapel van 10 en onmiddellijk terugslaan](results/gallery/games/B-matrix_B_w00_b11-g000005673.md) |

Beide offerpartijen zijn uiteindelijk door de speler van het motief gewonnen.
Het motief bewijst geen bewuste intentie of optimale tactiek. De categorie
materiaalcomeback bewaart daarnaast partijen waarin de latere winnaar bij
gelijke ontsnappingsscore veel minder stenen in zijn actieve stapels
controleerde. Dat is uitdrukkelijk geen bewezen verloren stelling.

## Lange partijen afzonderlijk onderzocht

De hoofdreeks had de onderzoeksgrens van 536 beurten. Daarom zijn de eerste
100.000 willekeurige partijen per variant met dezelfde taak-seeds en indices
nogmaals berekend, met een ruimere grens van 10.000 beurten. Dit zijn
**200.000 aanvullende simulaties van dezelfde starttrajecten**, geen
200.000 onafhankelijke nieuwe partijstromen. De afzonderlijke
[galerij voor lange partijen](results/gallery_long/README.md) bevat
16 recordverwijzingen naar 15 dossiers.

| Record bij limiet 10.000 | Variant A | Variant B |
|---|---:|---:|
| Langste waargenomen partij | [2.846 beurten, beëindigd wegens herhaling](results/gallery_long/games/A-baseline_A-g000013752.md) | [2.751 beurten, reguliere zwartwinst](results/gallery_long/games/B-baseline_B-g000022974.md) |
| Langste reguliere partij | [2.246 beurten, zwart wint](results/gallery_long/games/A-baseline_A-g000053221.md) | [2.751 beurten, zwart wint](results/gallery_long/games/B-baseline_B-g000022974.md) |

De twee galerijen hebben ieder hun eigen limiet, selectiepopulatie en manifest.
Hun records worden niet ongemerkt samengevoegd. Afbrekingen wegens herhaling
of zetlimiet krijgen geen reguliere winnaar.

## Controle en herkomst

De onafhankelijke Pythonoracle heeft alle 40 hoofd- en 15 lange dossiers,
samen 20.532 handelingen, volledig nagespeeld. Iedere zet, tussenstand,
stapelvolgorde, score, eindreden en het behoud van 18+18 stenen is gecontroleerd.
Alle 508 gecomprimeerde checkpointchunks zijn onafhankelijk samengevoegd;
hun totaaltellers en recordselecties komen overeen met de oplevering. Zie
de [hoofdaudit](results/gallery/validation.json),
[lange-partij-audit](results/gallery_long/validation.json) en
[validatiedocumentatie](GALLERY_VALIDATION.md).

De registrerende steekproef gebruikte engine/sourceversie `72dbf10` met de
volledige bronhashes in de manifests en executable-SHA256
`d5cbb847399ccd5ecbd4a83996c36cde6e83f1301eb8c50c3db40f52b1f5225c`.
De later geïntegreerde uitbreiding voor uitsluitend vroeg ontsnappen heeft
eigen beleidsvlaggen. Bij deze galerij waren die niet actief; de ongewijzigde
standaardpartijstromen zijn afzonderlijk getest.

De [exacte selectiecriteria](GALLERY_METHODS.md) zijn vóór de reeks vastgelegd.
De oude onderzoeksresultaten blijven afzonderlijk beschikbaar. Registratie
verbruikt geen extra toevalsgetallen en verandert de gekozen zetten niet.

## Uitvoeren en hervatten

```powershell
.\analysis\build.ps1 -OutputName staxxit_gallery.exe
$env:STAXXIT_GALLERY_CPP = (Resolve-Path analysis/build/staxxit_gallery.exe).Path
& $Python -m unittest discover -s analysis/tests -p test_records.py
& $Python analysis/run_gallery.py --results-dir analysis/results/gallery_new
& $Python analysis/validate_gallery.py analysis/results/gallery_new/catalog.json
```

Een afwijkende seed, limiet of steekproef krijgt een aparte `--results-dir`.
Het herhalen van hetzelfde commando hervat de complete gzipcheckpoints in
`analysis/checkpoints/gallery/<run_id>/`. Die tijdelijke kandidatenarchieven
worden niet gecommit. De compacte einddossiers wel. De oorspronkelijke reeks
kan met de bronversie in het manifest en dezelfde compiler worden gereproduceerd.

Zonder lokale checkpoints kan iedere ontvanger de bewaarde dossiers controleren:

```powershell
& $Python analysis/validate_gallery.py analysis/results/gallery/catalog.json --artifacts-only
```

Eén partij opnieuw genereren gaat via `staxxit_gallery.exe --replay ID`, met
de seed, variant, strategieën, beleidsvlaggen en limiet uit het dossier. De
expliciete zetten en snapshots blijven ook bij latere enginewijzigingen leesbaar.
