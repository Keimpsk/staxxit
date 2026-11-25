# De onderzoekspartijen laden in je simulator

De 55 opgeslagen galerijdossiers zijn omgezet naar het `.staxxit`-formaat van
`Keimpsk/staxxit-simulator`, branch `feature/game-rules-and-replay`. Er zijn
**geen partijen opnieuw gesimuleerd**. Beginstand, alle handelingen en alle
stapelvolgordes waren al bewaard.

## Laden

1. Open de simulatorversie van `feature/game-rules-and-replay`, of de preview
   van die branch. Een oudere versie zonder replayfunctie heeft deze knop niet.
2. Pak [staxxit-partijen.zip](results/simulator_replays/staxxit-partijen.zip) uit.
3. Klik op het startscherm op **Load .staxxit replay** en kies één bestand.
4. Gebruik **Play**, **Pause**, **Speed**, de stapknoppen en de zetlijst.
   **Jump to move** gaat rechtstreeks naar een zetnummer.

Begin bijvoorbeeld met:

- [B-kortste-winst.staxxit](results/simulator_replays/hoofd/B-kortste-winst.staxxit): 63 beurten.
- [B-comeback-score.staxxit](results/simulator_replays/hoofd/B-comeback-score.staxxit): van 0–5 achter naar 6–5 buitenvelden gewonnen.
- [A-offer-terugslag.staxxit](results/simulator_replays/hoofd/A-offer-terugslag.staxxit): het geregistreerde offer-/terugslagmotief bij beurt95.
- [B-langste-reguliere.staxxit](results/simulator_replays/lang/B-langste-reguliere.staxxit): 2.751 beurten.

De [volledige index](results/simulator_replays/README.md) bevat alle 55 bestanden
met categorie, variant en partijduur. `hoofd` bevat de 40 hoofddossiers;
`lang` bevat de 15 dossiers uit de aanvullende lange reeks. Commentaren
markeren relevante offers, comebacks, stapelhoogtes en onderzoeksafbrekingen.

## Omzetting en eindredenen

Het officiële [formaat](https://github.com/Keimpsk/staxxit-simulator/blob/feature/game-rules-and-replay/docs/STAXXIT-FORMAT.md)
en de implementatie in `lib/staxxit/record.ts` zijn gelezen en gebruikt.
Een `.staxxit`-bestand is UTF-8 JSON, versie1, met variant, vier expliciete
regelinstellingen, exportdatum, beginstand en chronologische handelingen.

Numerieke onderzoeksvelden worden omgezet naar axiale tekstcoördinaten `q,r`;
steenkleuren 0/1 worden W/B. Acties `p/m/c/s/e/x` worden
`place/move/capture/split/exit/pass`. Bij splitsen is `h1` de hoogte van het
onderste deel dat achterblijft. Alle vier de experimentele regelinstellingen
staan aan, overeenkomstig de onderzoekspartijen.

Reguliere winnaars en remises blijven behouden. De drie op een zetlimiet
afgebroken dossiers krijgen geen `result`: de simulator toont ze als lopende
partijen. Het commentaar bewaart de echte onderzoeksafbreking. De herhalingspartij
wordt in de simulator een remise met `ending: repetition`; de bronclassificatie
`repeat` blijft afzonderlijk in het exportmanifest staan. Er wordt geen opgave
verzonnen. De verplichte datum is het daadwerkelijke exportmoment; de
oorspronkelijke wall-clock-partijtijd is niet geregistreerd.

## Controle met de daadwerkelijke simulatorcode

Alle 55 bestanden zijn geladen door de ongewijzigde TypeScriptfunctie
`parseReplay` en de centrale engine uit simulatorcommit
`6feac4bc4db75df842064e4496132a928a8706cb`. De controle vergeleek **20.532 zetten
en 20.587 frames**, inclusief alle geordende stapels, beide voorraden,
aanzetkleur, fase, pasteller, scores, materiaalbehoud en eindreden.
Alle vergelijkingen slaagden. Ook alle 188 splitsingen en 269 ontsnappingen
in deze dossiers zijn meegenomen.

De grootste export is 275.440 bytes en de langste heeft 2.846 zetten,
ruim binnen de simulatorgrenzen van 5.000.000 bytes en 20.000 zetten.
De zes Pythonconvertertests slagen eveneens. Het resultaat en de exacte
simulatorbronhashes staan in
[validation.json](results/simulator_replays/validation.json). De simulatorrepo
is uitsluitend gelezen; er was geen codewijziging nodig.

## Later opnieuw exporteren

Vanuit de onderzoeksrepositoryroot, met een werkende Python3:

```powershell
python analysis/export_simulator_replays.py
```

De converter leest alleen bestaande trajecten. Hij voert geen C++-engine of
nieuwe simulatie uit. Het manifest bewaart de herkomst, oorspronkelijke
onderzoekseindreden, bestandschecksums en het exportmoment. Bij herhaalde
export met dezelfde bronnen blijft de datum gelijk; met `--date` kun je
expliciet een ander ISO8601-exportmoment opgeven. Afwijkende galerijen horen
in een eigen `--output-dir`.

De directe simulatorcontrole is reproduceerbaar met Node24 en een lokale
checkout van de simulatorbranch; de kleine loader lost alleen relatieve
TypeScriptimports op. Er zijn hiervoor geen npm-pakketten nodig:

```powershell
node --experimental-loader ./analysis/tests/simulator_ts_loader.mjs analysis/tests/validate_simulator_replays.mjs --simulator-root analysis/build/simulator-reference --manifest analysis/results/simulator_replays/manifest.json --output analysis/results/simulator_replays/validation.json
python -m unittest discover -s analysis/tests -p test_simulator_export.py
```

De simulatorcheckout staat lokaal onder de genegeerde `analysis/build`-map.
Importbestanden, ZIP, converter en controlescripts worden wel meegeleverd op
de onderzoeksbranch. De grafische simulator en `main` blijven ongewijzigd.
