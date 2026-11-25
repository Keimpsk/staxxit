# Overdracht Staxxit-complexiteitsonderzoek

## Status op 25 november 2026

De zeven onderzoekseries zijn volledig uitgevoerd: **490 taken, 8.320.000
partijen**. De onafhankelijke integriteitscontrole heeft alle 832 lokale
checkpointchunks opnieuw opgeteld en vergeleken met de afgeleverde resultaten.
`results/integrity.json` bevat de status en exacte bronhashes.

| Serie | Taken | Partijen | Opzet |
|---|---:|---:|---|
| baseline | 2 | 2.000.000 | Uniform willekeurig, 1 miljoen per variant |
| matrix | 288 | 2.880.000 | 12x12 geordend per variant, 10.000 per cel |
| phased | 144 | 1.440.000 | 3 fasen x12 kandidaten x2 kleuren x2 varianten |
| policies | 36 | 360.000 | Zes B-voorraadbeleidsregels, alle geordende paren |
| escape | 4 | 40.000 | B-ontsnappingsvoorkeur aan/uit, beide kleuren |
| adaptive | 8 | 800.000 | Onafhankelijke bevestiging faseschema vs vast |
| sensitivity | 8 | 800.000 | Uniform, limieten128/256/1024/2048 per variant |

Validatie-, benchmark-, kalibratie- en proefpartijen zitten niet in deze
8.320.000. Alle onderzoekstellingen zijn daadwerkelijk berekend.

## Branch en herkomst

Werk uitsluitend op `complexity-analysis-cpp`, repository
<https://github.com/Keimpsk/staxxit>. Wijzig of merge `main` niet en verander de
grafische simulator niet. De oorspronkelijke C++-bron kwam uit commit
`5027b81021f9baebc1f8bd37811604e3c5286fa1`; de Python-referenties kwamen uit
`9894202dec429fbda6e221c459c47bbad8929bb8` op `complexity-analysis`.
Hun exacte Git-blobhashes staan in `VALIDATION.md`.

De historische productierunner is bewaard in commit
`3ae6a1de7c9fa2b3cade991709381915fdeef2d5`. De enginesource is sindsdien
semantisch ongewijzigd. De daadwerkelijk geteste en gebruikte executable heeft
SHA-256 `7960cb96613703d91ca0ce7cfdc61064d6573cb191448e81d286fd8f31b5553c`.
Alle zeven productiemanifests verwijzen naar dezelfde engine/source/runner.
De latere onderhoudsrunner wordt afzonderlijk geregistreerd.

## Wat lezen

1. `REPORT.md`: Nederlandstalige resultaten en interpretatie, met overzichtsfiguur.
2. `RULES.md`: exacte regels, concrete ringindeling en voorlopige afbreekregels.
3. `STRATEGIES.md`: exacte scores en betekenis van engine-IDs0–11, policies0–5.
4. `VALIDATION.md`: drie onafhankelijke implementaties en de uitgebreide controles.
5. `COMPLEXITY.md` en `METHODOLOGY.md`: configuratietelling, cycli, censurering,
   onzekerheid en de beperkingen van boomschatters.
6. `results/experiment_selection.json`: selectie van vaste strategie en faseschema.

## Belangrijkste conclusies en hun reikwijdte

Uniforme nulmeting (limiet536): A wit36,8205%, zwart39,7791%, reguliere
remise21,8489%; B wit36,3656%, zwart38,4930%, reguliere remise23,5255%.
Herhalingen en limieten staan afzonderlijk in de resultaten en tellen niet als
remise. Exacte intervallen, duurverdelingen, actietellers, hoogtes en
voorraaduitputtingscorrelaties staan in JSON en het rapport.

Strategie8, naar de buitenring, heeft de hoogste verkennende toernooiscore in
beide varianten; strategie6, verspreiden, volgt. De fasescreening selecteert
`8,8,6`: eerste twaalf plaatsingen naar buiten, laatste zes verspreiden.
Lees de onafhankelijke `adaptive`-serie voordat je dit een verbetering noemt:
effecten verschillen tussen A en B. De hoogste gemeten score is geen bewijs
van algemene speltheoretische optimaliteit. Voor B vergelijken de aanvullende
reeksen plaatsen/slaan en ontsnappen onder het vastgelegde bewegingsbeleid.

De exacte configuratiebovengrenzen zijn circa6,3766e44 (A) en8,2344e44 (B).
Dit zijn supersets, geen aantallen bereikbare legale posities. Beide varianten
hebben bewezen bereikbare vierzetcycli: zie `cycle_witness_A/B.json`.
De onbeperkte geschiedenisboom is daarom oneindig. De Knuthschatting van de
afgeknotte boom heeft op grote diepte extreem zware staarten; ESS en
batchdiagnostiek verbieden een betrouwbare totale-ordegrootteclaim.

Onder de huidige regels zijn twee opeenvolgende passen en herplaatsen op een
leeg binnenbord na de beginzet onbereikbaar vanuit een legale beginpartij.
Hun tellers zijn nul en blijven als defensieve diagnoses bestaan. Bewijzen
staan in `METHODOLOGY.md`/`REPORT.md`.

## Reproduceren en hervatten

Zie `README.md` en `run_all.ps1`. De hoofdengine is standaard C++17; de
onderzoeks- en verificatiescripts gebruiken alleen de Pythonstandaardbibliotheek.
De optionele figuur gebruikt Matplotlib; de gebruikte pakketten staan lokaal
in de genegeerde map `build/plot_packages`.

Op deze machine is Python3.12.14 meegeleverd met de Codex-runtime. Het gebruikte
pad was:

```text
C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1123-915-0_26.1123.915.0_x64__3k8sg7r9htsxt\dependencies\python\python.exe
```

De portable GCC16.2.0 staat lokaal in `../../.tools/w64devkit/bin/g++.exe`
ten opzichte van `analysis`; deze compiler en de binaries zijn niet gecommit.
De relatieve compilerfallback in `build.ps1` zoekt dit pad. De gebruikte CPU
heeft 16 kernen/32 threads; alle productietaken gebruikten32 threads en
steenbehoudcontrole na iedere handeling.

Checkpoints staan lokaal onder `analysis/checkpoints/<run_id>/` en worden niet
gepushd. De volledige geaggregeerde resultaten, histogrammen en manifests wel.
Hervatten vereist dezelfde enginebinary/-source en spelinstellingen. Iedere
partij heeft een eigen deterministische seed uit taakseed en partij-index;
threads hebben geen invloed op de partij. Na alleen runneronderhoud kan de
identiteit van een bestaande run expliciet worden behouden:

```powershell
& $Python analysis/run_study.py --suite baseline --threads 8 --resume-run 84994028b49c2366
```

Dit controleert alle spelinstellingen en beide enginehashes tegen het bestaande
manifest en valideert ook hergebruikte tellers. Deze exacte hervatting is
uitgevoerd: alle2 miljoen baselinepartijen kwamen uit bestaande checkpoints
en de JSON-resultaatbytes bleven identiek. Zie
`results/validation_checkpoint_resume.json`. Voor andere series: neem de
run-id uit hun JSON en geef dezelfde kampioen-/schema-/games-/chunkparameters.

Na gewijzigde spelregels, strategieën of binary: gebruik een nieuwe run. Meng
geen chunks met andere instellingen. Na het wijzigen van selectiebronnen:
`select_experiments.py --matrix-only`, voer `phased` opnieuw uit, en selecteer
daarna pas nieuwe schema's. De selectie controleert bronvolledigheid en
kampioenconsistentie; onafhankelijke integriteit controleert de taakroosters.

## Technische afwijkingen en opgeloste problemen

- De desktopwerkmap was aanvankelijk een lege Git-repository. Het project is
  daarom in de submap `staxxit` gekloond, direct op de gevraagde branch.
- GitHubnetwerk en hardware-CIM vereisten uitvoering buiten de sandbox;
  alle wijzigingen/downloads bleven beperkt tot de onderzoekswerkmap.
- Er was geen bruikbare C++-compiler. De officiële portable compiler is lokaal
  gedownload en de SHA-256 is gecontroleerd; geen systeeminstallatie nodig.
- Beide oorspronkelijke herhalingssleutels misten de pasteller. De onafhankelijke
  onderzoeksafhandeling neemt deze op; de historische Pythonkopieën blijven
  herkenbaar en hun gedrag wordt tegen de oracle gecontroleerd.
- Windows gaf tijdens de matrix na850.000 partijen één tijdelijke fout bij
  atomair vervangen van het resultaatbestand. Dezelfde run is hervat en reeds
  voltooide chunks zijn overgeslagen. Geen partij of uitkomst ging verloren.
  De onderhoudsrunner probeert tijdelijke Windowsbestandslocks nu kort opnieuw.
  Tests controleren dat de oude doelversie intact blijft tot vervangen lukt.
- De CSV-export gebruikt expliciete `white_strategy`, `black_strategy` en
  `*_count`-kolommen om strategienummers en uitkomsttellingen te onderscheiden.

## Logische vervolgstappen

Dit zijn nieuwe onderzoeksvragen, geen ontbrekende verplichte runs:

- Test plaatsingskeuzes tegen sterkere, gedeelde bewegingsstrategieën en
  gebruik onafhankelijke bevestiging voor nieuwe kandidaten.
- Isoleer uitsluitend vroege ontsnappingsvoorkeur; de huidige ontsnappingsproef
  geeft prioriteit aan alle legale ontsnappingen en registreert vroege apart.
- Varieer B-voorraaddrempels en conditionele slagkansen; de huidige optimale
  verhouding geldt alleen binnen de zes geteste heuristieken.
- Gebruik gestratificeerde/importance sampling of lokale exacte tellingen
  voor stabielere boomschattingen; presenteer geen ondiepe kalibratie als
  bewijs voor betrouwbaarheid op diepte536.
- Zoek bereikbaarheidseisen die de theoretische configuratiebovengrens verder
  aanscherpen. Een echte minimaxoplossing is niet door deze Monte-Carloruns bewezen.

Verander de voorlopige spelregels pas na een expliciete beslissing van de
gebruiker; behandel gewijzigde regels als afzonderlijke experimenten.
