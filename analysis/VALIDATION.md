# Onafhankelijke validatie

De officiële regels uit de opdracht zijn de norm. Eerdere simulatie-uitkomsten zijn niet als bewijs hergebruikt.

## Bronnen en onafhankelijkheid

De Pythonbestanden in `reference/` zijn ongewijzigde kopieën uit branch `complexity-analysis`, commit `9894202dec429fbda6e221c459c47bbad8929bb8`. Hun Git-blobidentiteiten zijn:

| Bestand | Git blob SHA-1 |
|---|---|
| `staxxit_analysis.py` | `06213f264796b19d778f9abf1087a8812f73debb` |
| `staxxit_variants.py` | `9d524b7eb2bd2aeab3b1994ecbc20dadf94b77d6` |

`reference/oracle.py` implementeert dezelfde gebruikersregels opnieuw met coördinaten, immutable kleurreeksen en direct berekende richtingen. De oracle deelt geen C++-bordrepresentatie, raytabellen of zetgenerator. De geometrie is afzonderlijk gecontroleerd: 91 binnenvelden, 36 buitenvelden, en 15/15/6 wit/zwart/neutraal. De aangenomen kleurvolgorde is die van beide bestaande engines: zes neutrale hoekvelden, met afwisselend wit en zwart op de overige buitenvelden, beginnend wit na hoek `(6,0)` in de richting `(0,6)`. De opdracht geeft aantallen maar geen volledige kleurkaart; deze bestaande kaart blijft daarom een expliciete modelaanname.

Er is bij deze controle geen verschil tussen de legale zetten of scoreberekening van de oorspronkelijke Python-engine en de onafhankelijke oracle gevonden. De bewaarde oorspronkelijke Pythonrunner is geen onderzoeksrunner: hij heeft geen hervatbare checkpoints en zijn herhalingssleutel bevat niet de teller van opeenvolgende passen. De nieuwe onderzoeksrunner en oracle nemen die teller wel op als onderdeel van de volledige toestand. De legacy-bestanden blijven intact voor controleerbare herkomst.

## Tests

`tests/test_rules.py` bevat 26 handgemaakte tests. Zij controleren de eerste middenplaatsing, aansluiting aan aanwezige binnenstapels, uitsluitend vrije binnenvelden, de voorlopige herstart op een leeg binnenbord, zes bewegingsrichtingen en maximale afstand, exacte slagafstand, blokkering en eigen stapels, globale slagplicht, fasen en individuele voorraadrechten in variant B, ontsnappen naar eigen/neutrale vrije velden, niet meer handelen door ontsnapte stapels, splitsen vanaf hoogte 12 met beide eigen bovenstenen, slagplicht vóór splitsen, materiaalbehoud, voorraad-/fasegebonden einde, lexicografische eindscore inclusief alle kleuren in ontsnapte stapels, en de volledige herhalingssleutel. Een synthetische positie met 18+18 stenen en een omsingelde witte stapel toont een situatie waarin wit moet passen terwijl de partij geen reguliere eindstand heeft en zwart wel kan handelen.

Lokale regelvoorbeelden mogen minder dan 36 stenen bevatten om precies één regel te isoleren. Die voorbeelden worden niet als bereikbaar of representatief aangemerkt. De gerandomiseerde volledige posities en gespeelde trajecten moeten altijd exact 18 witte en 18 zwarte stenen bevatten, inclusief voorraden en ontsnapte stapels.

`tests/differential.py` controleert voor iedere bezochte toestand de volledige verzameling legale zetten en de einduitslag. Voor iedere gekozen zet vergelijkt hij ook de volledige volgende bordtoestand, voorraad, beurt en uitslag, met materiaalcontrole vóór en na de handeling. De zetkeuze komt uit één Python-RNG met expliciete seed; verschillen tussen de Python- en C++-RNG zijn daardoor geen bron van schijnbare engineverschillen. Synthetische geldige materiaalposities met variabele stapelhoogtes vullen de bereikbare trajecten aan en verhogen onder andere de splitsingsdekking. Bereikbaarheid van die synthetische posities wordt niet verondersteld.

De C++-engine wordt benaderd via een stateloos, regelgebaseerd `--protocol`. Hierdoor controleert de vergelijking de engine, zonder te vertrouwen op eerdere samengevatte simulatiecijfers. Het uitvoerbestand wordt met SHA-256 in het validatieresultaat geïdentificeerd. Een verschil schrijft een reproduceerbare toestand naar `results/validation_failure.json` en stopt met een fout.

## Werkelijk uitgevoerde Pythoncontrole

`results/validation_python.json` legt een geslaagde run vast met seed `20261125`, 1.000 partijen per variant, zetlimiet 536 en 10.000 aanvullende synthetische posities. Daarbij zijn 373.682 toestanden en 351.711 overgangen vergeleken. Alle vijf actietypen zijn uitgevoerd, inclusief 3.105 splitsingen en 3.281 ontsnappingen. Er waren geen verschillen of materiaalverliezen. Deze kleine validatieset is geen nulmeting en wordt niet als onderzoeksbewijs voor winstpercentages gebruikt.

De actuele C++-validatie staat in `results/validation.json`, nadat de hieronder beschreven vergelijking met het gebouwde uitvoerbestand is uitgevoerd. Het bestand zelf is leidend voor het aantal vergelijkingen, de seed, looptijd en executablehash.

`tests/runner_audit.py` controleert daarnaast de volledige onderzoeksrunner onafhankelijk. De Python-oracle gebruikt daarvoor dezelfde expliciet geïmplementeerde SplitMix64-generator en zetvolgorde, zodat iedere individuele willekeurige partij exact dezelfde keuzes krijgt. Voor 1.000 partijen per variant worden 21 integerstatistieken exact vergeleken: uitslagen, zetten-/pas-/actieaantallen, fasen en legale keuzes, duurverdeling, bron- en maximale stapelhoogtes, acties en vroege acties per speler, eerste lege voorraad, materiaalcontroles en bezochte dieptes. Dezelfde resultaten moeten met één en vier threads ontstaan en moeten optellen uit twee hervatbare `--start`-batches van 500 partijen. Een aanvullende zetlimiet van één beurt moet alle tien testpartijen als zetlimiet beëindigen. `results/validation_runner.json` bevat het resultaat. Deze controle dekt ook de aflooplogica en telling, naast de vergelijking van losse zetten.

## Bereikbare herhalingscycli

`tests/cycle_witness.py` heeft voor beide varianten vanaf de echte beginpositie een legale prefix en een vierzetten-cyclus gevonden. `results/cycle_witness_A.json` bevat een prefix van 56 zetten; variant B heeft een prefix van 64 zetten. In beide gevallen leidt de cyclus exact terug naar dezelfde volledige toestand, inclusief stapelvolgorde, voorraad, buitenvelden, beurt en pasteller. De cyclus bevat geen passen en geen reguliere eindstand. De opgeslagen zetten zijn opnieuw vanaf de beginpositie afgespeeld met legale-zetten- en materiaalcontrole. Met `--cpp` wordt diezelfde replay tevens door C++ gecontroleerd.

Deze concrete witnesses bewijzen dat beide spelvarianten zonder herhalingsregel of zetlimiet een oneindig legaal spelverloop toelaten. De voorlopige derde-herhalingsregel beëindigt zulke trajecten apart als herhaling. Dit bewijst geen frequentie onder willekeurig of optimaal spel.

## Reproduceren

Voer vanuit de repositoryroot uit met Python 3.10 of nieuwer:

```powershell
python -m unittest discover -s analysis/tests -p test_rules.py -v
python analysis/tests/differential.py --games 1000 --synthetic 10000 --output analysis/results/validation_python.json
$env:STAXXIT_CPP = (Resolve-Path analysis/build/staxxit.exe).Path
python -m unittest discover -s analysis/tests -p test_rules.py -v
python analysis/tests/differential.py --cpp analysis/build/staxxit.exe --games 1000 --synthetic 10000
python analysis/tests/runner_audit.py --cpp analysis/build/staxxit.exe --games 1000
python analysis/tests/cycle_witness.py --cpp analysis/build/staxxit.exe
```

Gebruik het werkelijke pad naar het gebouwde C++-uitvoerbestand als dit anders is. Handgemaakte grensgevallen plus grote differentiële steekproeven geven aanzienlijk meer zekerheid dan overeenkomende winstpercentages, maar vormen geen uitputtend correctheidsbewijs voor alle bereikbare toestanden. De tegenvoorbeelden met cycli zijn wel exacte, eindige witnesses en geen statistische schatting.
