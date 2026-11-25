# Onafhankelijke validatie van de partijgalerij

De nieuwe registratie is gecontroleerd met `validate_gallery.py` en
`tests/test_records.py`. Deze scripts gebruiken de onafhankelijke,
coördinatengebaseerde Pythonoracle. Zij importeren geen C++-zetgenerator,
registratiecode, onderzoekscollector of selectiemerger.

## Uitgevoerde controles

De tien regressietests zijn daadwerkelijk geslaagd op de uiteindelijke
gecombineerde engine. Het machineleesbare resultaat staat in
`results/validation_game_records_engine.json`.

- Voor 1.000 partijen per variant zijn alle 21 oorspronkelijke
  integertellers/histogrammen gelijk met registratie aan en uit, en gelijk aan
  de oorspronkelijke gevalideerde engine. Er veranderen geen gespeelde
  partijen door het bewaren van records.
- De geselecteerde catalogus is volledig gelijk bij 1 en 4 threads.
- Twee blokken van 500 partijen selecteren na samenvoegen dezelfde records
  als één blok van 1.000, inclusief de kleinste partij-index bij gelijke rang.
- Alle 48 partijen per variant van een kleine volledige steekproef zijn
  afzonderlijk gegenereerd en onafhankelijk nagespeeld. De batchrecords komen
  exact overeen met de opnieuw berekende extrema over deze 96 trajecten.
- Iedere geselecteerde partij uit de regressiebatches is met `--replay` uit
  zijn seed en partij-index opnieuw gegenereerd. De volledige trajecten en
  tussenstanden komen exact overeen.
- De latere optie voor uitsluitend vroeg ontsnappen wordt expliciet in de
  configuratie bewaard. Registratie en replay geven ook met deze optie aan
  exact dezelfde partij terug. Oude dossiers zonder deze optionele vlaggen
  blijven geldig.
- Gerichte wijzigingen in een steen, score, zet, einduitslag, slagzetsteller
  en RNG-identiteit worden afgewezen. Afwijkende voorraad-, fase- en
  ontsnappingsbeleidsinstellingen worden voor de vaste galerijpopulatie
  eveneens afgewezen.

Lokale handfixtures controleren daarnaast de exacte materiaalgrens,
scoregelijkheid inclusief de tweede tiebreak, uitsluiting van terminale
toestanden, vroegste getuigen bij gelijke achterstand en het onmiddellijke
plaats/beweeg–slag–terugslagmotief. Zulke kleine lokale fixtures zijn bedoeld
om één criterium te isoleren; volledige trajecten controleren steeds alle
36 stenen.

## Volledige galerijen

| Reeks | Gespeelde partijen | Taken | Checkpoints | Dossiers | Selecties | Onafhankelijk nagespeelde zetten |
|---|---:|---:|---:|---:|---:|---:|
| Hoofdgalerij, limiet536 | 4.880.000 | 290 | 488 | 40 | 40 | 10.246 |
| Aanvullende lange reeks, limiet10.000 | 200.000 | 2 | 20 | 15 | 16 | 10.286 |

Beide controles zijn geslaagd. De aanvullende lange reeks herberekent voor
dezelfde twee taakseeds en partij-indices 0–99.999 de baseline met een ruimere
limiet. Dit zijn geen 200.000 onafhankelijke nieuwe partij-identiteiten.

Voor ieder definitief dossier controleert de validator:

1. De lege beginstand, wit aan zet en 18 stenen per voorraad.
2. Iedere afzonderlijke legale handeling en het volledige aantal beschikbare
   legale handelingen; een pas mag alleen bij afwezigheid van legale acties.
3. Alle 127 geordende stapels, voorraden, aanzetkleur, pasteller, scores,
   actieve stapelaantallen en gecontroleerde actieve stapelhoogtes.
4. Behoud van precies 18 witte en 18 zwarte stenen, inclusief ontsnapte
   stapels en voorraad; buitenkleurbeperkingen blijven geldig.
5. De juiste prioriteit van reguliere beëindiging, twee passen, derde
   herhaling en zetlimiet. De dossiers normaliseren na iedere handeling de
   aanzetkleur naar de volgende speler, ook na de laatste handeling.
6. De aanvankelijke SplitMix64-toestand, exacte seed/partij-identiteit,
   plaatsingsstrategielabels en stapelhoogtes vóór de handelingen.
7. Alle selectiematen en getuigen voor offers, scoreachterstanden en
   materiaalachterstanden, opnieuw berekend uit de trajecten.
8. De bordindexen, axiale coördinaten en buitenkleuren in `board.json`,
   vergeleken met de afzonderlijk geïmplementeerde geometrie van de oracle.

Verder zijn alle 508 lokale checkpointbestanden gecontroleerd. Hun
integertellers zijn onafhankelijk opnieuw opgeteld naar de taakstatistieken.
De 4.811 opgeslagen chunkkandidaten zijn op consistente rang-/categorieclaims
gecontroleerd en onafhankelijk samengevoegd tot de globale selectie, met de
vastgelegde taak-/partij-tiebreaks. De regel dat beste strategievoorbeelden
uitsluitend uit de evenwichtige strategiematrix komen is afzonderlijk getoetst.

De volledige oracle-replay betreft alle definitieve dossiers. De validator
claimt geen volledige replay van iedere tussenkandidaat of van alle miljoenen
niet-bewaarde partijen. De complete kleine steekproef dient als onafhankelijke
kalibratie van het selectiealgoritme. Een record geldt binnen de opgegeven
steekproef; het is geen bewezen kortst mogelijke partij of optimaal spel.

## Reproduceercommando's

Vanuit de repositoryroot, met een werkende Python3:

```powershell
$env:STAXXIT_GALLERY_CPP = (Resolve-Path analysis/build/staxxit_gallery.exe).Path
python -m unittest discover -s analysis/tests -p test_records.py
python analysis/validate_gallery.py analysis/results/gallery/catalog.json --source-commit 72dbf10 --engine analysis/build/staxxit_gallery_sample_v1.exe --output analysis/results/gallery/validation.json
python analysis/validate_gallery.py analysis/results/gallery_long/catalog.json --source-commit 72dbf10 --engine analysis/build/staxxit_gallery_sample_v1.exe --output analysis/results/gallery_long/validation.json
```

De onderzoeksreeksen gebruiken de onveranderlijke engine-/headerbron uit
commit `72dbf10594331917eab78219953e93bba3e28da6` en de bewaarde binary met
SHA-256 `d5cbb847399ccd5ecbd4a83996c36cde6e83f1301eb8c50c3db40f52b1f5225c`.
De latere integratie van een andere onderzoeksuitbreiding verandert deze
historische herkomst niet. Met `--source-commit` worden de exacte bronbytes
uit Git gelezen; `--engine` verifieert de oorspronkelijke executable.

Voor een gedownloade checkout zonder de genegeerde lokale checkpoints of
oorspronkelijke binary kan iedere opgeslagen partij nog worden gecontroleerd:

```powershell
python analysis/validate_gallery.py analysis/results/gallery/catalog.json --artifacts-only
```

De uitkomsten staan apart in `results/gallery/validation.json` en
`results/gallery_long/validation.json`. Offers en comebacks blijven
beschrijvende patronen: de controle bewijst geen intentie, tactische
optimaliteit of een speltheoretisch verloren uitgangspositie.
