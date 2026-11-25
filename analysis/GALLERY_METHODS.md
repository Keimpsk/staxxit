# Selectie van bijzondere Staxxit-partijen

Deze uitbreiding bewaart een kleine, reproduceerbare verzameling opvallende
partijen met hun volledige legale zetverloop. De criteria hieronder zijn vóór
de nieuwe archiefruns vastgelegd. Een geselecteerde partij is een voorbeeld
uit de geregistreerde steekproef, geen bewezen wereldrecord of bewijs dat
haar speler optimaal speelde.

De officiële onderzoeksregels blijven in `RULES.md` staan. Registratie verandert
de legale zetten, keuzeverdeling, toevalsreeks of einduitslag niet. De oude
8.320.000 onderzoekspartijen en hun oorspronkelijke bestanden blijven als
afzonderlijk onderzoek herkenbaar. De galerij krijgt een eigen manifest en
daadwerkelijk uitgevoerde steekproefaantallen.

## Wat is een geregistreerde partij?

Een partij begint bij het lege binnenbord met beide voorraden op 18 en wit
aan zet. Iedere handeling, inclusief een verplichte pas, telt één beurt.
Een zetlijst gebruikt dezelfde stapelvolgorde als de engines: onder naar boven.
Toestand 0 is de beginstand; toestand `i` is de stand na handeling `i`.

Het dossier bevat de variant, volledige beleidsinstellingen en fasekeuzes,
experimentseed, partij-index, zetlimiet, eindreden, scores en alle zetten.
De geometrie en concrete kleurkaart staan in `RULES.md`; CSV en de bordfiguren
gebruiken axiale coördinaten. In JSON zijn de 127 velden geïndexeerd met eerst
`q=-6..6`, daarna `r=-6..6`, uitsluitend waar
`max(abs(q),abs(r),abs(q+r)) <= 6`. Bron-/binaryhashes en de identiteit
van de taak staan in het runmanifest. Bij naspelen worden alle tussenstanden
opnieuw berekend en op legaliteit, score en behoud van 18+18 stenen gecontroleerd.

Een seed alleen vervangt geen zetlijst: wijzigingen in zettenvolgorde of RNG
kunnen later andere trajecten opleveren. De expliciete zetten blijven daarom
de primaire replaybron; seeds maken aanvullende regeneratie mogelijk.

## Rechtstreeks gemeten recordcategorieën

| Categorie | Exact selectiecriterium | Afloop toegestaan |
|---|---|---|
| Kortste gewonnen partij | Minimaal aantal uitgevoerde handelingen tot een reguliere winst | Alleen wit- of zwartwinst |
| Langste geobserveerde partij | Maximaal aantal uitgevoerde handelingen | Alle zes onderzoeksaflopen |
| Langste regulier beëindigde partij | Maximaal aantal handelingen tot reguliere winst of remise | Alleen reguliere afloop |
| Meeste slagzetten | Maximaal aantal handelingen van type `c` | Alle zes onderzoeksaflopen |
| Hoogste stapel | Hoogste hoogte van een stapel in enige bereikte toestand | Alle zes onderzoeksaflopen |

Een slagzet telt eenmaal, ongeacht de hoogte of kleurinhoud van de aangevallen
stapel. Een buitenstapel blijft aanwezig in de toestand en telt mee in de
hoogtemeting. `repeat`, `blocked` en `limit` krijgen geen reguliere winnaar.
Bij een langste partij op de zetlimiet staat expliciet dat zij is afgekapt;
de werkelijke voortzettingsduur is onbekend. Daarom bestaat ook de afzonderlijke
categorie voor de langste reguliere partij.

De eerste vier categorieën zeggen niets over de kwaliteit van de gespeelde
zetten. Een partij met veel slagen kan bijvoorbeeld door beide spelers slecht
gespeeld zijn. Een hoge stapel is ook niet automatisch gunstig: slaan en
ontsnappen vereisen een exacte afstand, en hoogte >=12 verandert de mogelijkheden.

## Beste gewonnen voorbeeld per plaatsingsstrategie

Voor iedere vaste plaatsingsstrategie 0–11 wordt een reguliere zege gekozen,
met beide kleurrollen en alle geregistreerde tegenstrategieën in aanmerking.
De rangschikking binnen deze categorie is lexicografisch:

1. Grootste verschil in bezette buitenvelden: `E_winnaar - E_verliezer`.
2. Daarna grootste verschil in totale stenen in ontsnapte stapels:
   `S_winnaar - S_verliezer`.
3. Daarna de kortste partij.
4. Daarna de vaste taak-/partij-identiteit als reproduceerbare tie-break.

Een zege met meer buitenvelden weegt dus zwaarder dan een zege met meer
ontsnapte stenen. Bij een positieve buitenveldmarge mag de secundaire
steenmarge negatief zijn: dat verandert de officiële overwinning niet.
De kleuren van de afzonderlijke stenen binnen een ontsnapte stapel zijn voor
deze score niet relevant; de eigenaar van de stapel ontvangt de gehele score.

Deze categorie heet een **beste gewonnen voorbeeld**, niet de beste bewezen
partij. De rangschikking gebruikt de eindscore; zij berekent geen zetkwaliteit,
minimaxwaarde, foutloosheid of schoonheid. Een grote uitslag tegen een zwakke
tegenstander bewijst geen sterke strategie. De gewone winstmatrices blijven
de geschikte bron voor het vergelijken van beleidsregels.

Het runmanifest vermeldt de selectiepopulatie. Voor de uiteindelijke
voorbeelden per strategie wordt uitsluitend de gebalanceerde
12x12-matrix gebruikt. Zo krijgt strategie 0 niet extra veel kansen op een
extreme zege via de grotere uniforme nulmeting. Wanneer een speler een
wisselend faseschema gebruikt, wordt dat volledige schema vermeld en mag het
voorbeeld niet als een zuivere uitvoering van één vast strategie-ID gelden.

## Waarneembare kandidaat voor een tactisch offer

De detector zoekt een concrete reeks van drie opeenvolgende handelingen:

1. Speler `c` plaatst (`p`) of beweegt (`m`) een stapel naar binnenveld `t`.
2. De tegenstander slaat die stapel onmiddellijk op `t`.
3. Speler `c` slaat de ontstane vijandelijke stapel onmiddellijk terug op `t`.

De partij moet vervolgens regulier door speler `c` worden gewonnen. Het
dossier markeert de drie betreffende beurten en vermeldt de aangeboden
stapelhoogte en de hoogte van de vijandelijke aanvaller. De opmerkelijkheid
wordt gerangschikt op de hoogte van de gevangen vijandelijke aanvaller,
vervolgens de aangeboden hoogte, met een vaste identiteits-tie-break.

Dit is een zichtbaar offer-/terugslagmotief. Het bewijst niet dat de eerste
handeling bewust als offer werd gekozen, dat de tegenstander moest aannemen,
dat de terugslag beslissend was of dat geen betere zet bestond. De eerste
handeling is geen slagzet; zo wordt een gewone keten van verplichte slagen
niet automatisch als een vrijwillig offer beschreven. Ook een plaatsing in
variant B kan onderdeel van het motief zijn.

Registratie kan terecht geen kandidaat vinden. De galerij meldt dan dat deze
categorie in de uitgevoerde steekproef leeg bleef; er worden geen voorbeelden
geconstrueerd of achteraf als gespeeld gepresenteerd.

## Comebacks: score en materiaal afzonderlijk

Een ogenschijnlijk verloren positie vereist een evaluatiemodel. Dat model is
nog niet opgelost voor Staxxit. Daarom gebruikt de galerij twee expliciete
waarnemingscriteria, met een reguliere uiteindelijke winnaar en een gemarkeerde
eerdere tussenstand. Beide voorraden moeten op dat eerdere moment leeg zijn,
zodat openingsverschillen door het om-en-om plaatsen geen comeback opleveren.

**Achterstand in de lopende officiële score.** De latere winnaar stond eerder
achter in de lexicografische score `(bezette buitenvelden, ontsnapte stenen)`.
De detector bewaart de eerdere score en het tijdstip. De grootste achterstand
in buitenvelden gaat voor; daarna volgt de steenachterstand en daarna het
vroegste tijdstip van deze achterstand. Een positieve buitenveldachterstand
mag samengaan met een negatieve steenachterstand: de speler staat volgens de
officiële lexicografische score dan nog steeds achter. Een steenachterstand
bij gelijke buitenvelden kan zelfstandig kwalificeren. Dit is een echte
achterstand in de getelde score, maar nog geen
bewijs dat de stelling speltheoretisch verloren was.

**Achterstand in gecontroleerd actief materiaal.** Bij een gelijke lopende
scoretuple beschikte de latere winnaar over minstens zes actieve gecontroleerde
stenen minder dan de tegenstander. Het gecontroleerde materiaal is
`M_c = som(stapelhoogte)` over binnenstapels waarvan de bovensteen kleur `c`
heeft. Een gemengde stapel telt geheel voor zijn huidige eigenaar. Dit is iets
anders dan het aantal fysiek witte of zwarte stenen: die blijven inclusief
voorraad en buitenstapels steeds 18 per kleur. De detector rangschikt op de
grootste waarde `M_tegenstander - M_winnaar`, daarna het vroegste tijdstip.

De drempel zes is een vooraf gekozen selectiedrempel voor opvallende voorbeelden,
geen empirisch bewezen grens voor een slechte positie. Een materiaalachterstand
is in Staxxit geen zekere nadeelmaat: de overwinning hangt van ontsnapping af.
De beschrijving noemt deze partij daarom een **materiaalkomback volgens de
heuristiek**, niet een bewezen ontsnapping uit een verloren stelling.

Reguliere eindstanden tellen bij beide comebackmetingen niet als eerdere
achterstand. Daardoor wordt het verwijderen van de laatste eigen actieve
stapel niet achteraf als een materiaalcomeback gemarkeerd wanneer de partij
door die handeling al afgelopen is.

## Vastgelegd steekproefprotocol en bestandsformaat

De standaardopzet van `run_gallery.py` plant twee afzonderlijke families:

- Een uniforme reeks van 1.000.000 partijen per variant, met beide
  plaatsingsstrategieën op 0.
- De volledige 12x12-matrix van vaste plaatsingsstrategieën, 10.000 partijen
  per geordende combinatie en per variant.

Dat plan omvat 290 taken en 4.880.000 partijen. Met chunks van 10.000 zijn
er 488 checkpoints. Dit zijn de configuratiedefaults, **geen zelfstandige
bewering dat een run is voltooid**. Het catalogusmanifest bevat de werkelijk
voltooide omvang. Een aparte pilot met 100.000 uniforme partijen per variant
en 1.000 per matrixcel omvat 488.000 partijen; zijn resultaten horen in een
afzonderlijke bestemming.

De plaatsingskeuze en de beweging zijn in deze standaardreeks gelijk aan het
eerder vastgelegde uniforme beleid: policy 0, geen ontsnappingsvoorkeur en
geen wisselend faseschema. Alleen de vaste plaatsingsheuristiek varieert in
de matrix. De basis-seed is standaard 2026112501 en de zetlimiet 536.
Globale extrema en motieven worden uit beide families geselecteerd; de
voorbeelden per vaste plaatsingsstrategie uitsluitend uit de matrix.

De taakseed is de eerste acht bytes, little-endian geïnterpreteerd, van
SHA-256 over `staxxit.gallery.v1:<basis-seed>:<taak-id>`. De engine leidt de
partijstream af uit deze seed en de partij-index, zoals in `STRATEGIES.md`.
De 64-bits seeds staan als decimale strings in JSON zodat JavaScriptclients
ze niet onbedoeld afronden.

De verzameling heeft de volgende machineleesbare lagen:

- `staxxit.records.v1`: door de engine gekozen kandidaten binnen één chunk.
- `staxxit.trace.v1`: een zelfstandige partijtrace met configuratie, zetten,
  snapshots, eindreden en controleerbare selectiemetrieken.
- `staxxit.gallery.v1`: de samengevoegde catalogus, met verwijzingen naar
  unieke partijbestanden, selectiecriteria en een studie-manifest.

De machinecategorieën zijn `shortest_won`, `longest_observed`,
`longest_regular`, `most_captures`, `tallest_stack`, `best_strategy`,
`tactical_offer`, `comeback_score` en `comeback_material`. Een partij kan
meerdere categorieën vertegenwoordigen en wordt dan eenmaal als unieke
trace opgeslagen. Iedere categorie wordt per variant geselecteerd;
`best_strategy` bovendien apart per strategie-ID.

De laatste stand na een reguliere eindhandeling wisselt in de trace de
aanzetkleur, conform de vaste snapshotconventie. Dat betekent niet dat er
nog een handeling wordt gespeeld. De eindreden en de replaycontrole bepalen
het einde, niet de aanzetkleur in de laatste snapshot.

## Determinisme, checkpoints en samenvoegen

Iedere taak gebruikt een vaste seed en expliciete partij-indexreeks.
Registratie verbruikt geen extra toevalsgetallen uit de partijstroom. Bij
gelijke primaire records beslist een vaste volgorde van taakidentiteit en
partij-index, niet de volgorde waarin threads klaar zijn. De winnaar tussen
chunks moet daardoor gelijk zijn aan de winnaar van dezelfde volledige reeks
in één keer. Meerdere categorieën mogen naar dezelfde bewaarde partij verwijzen.

Checkpoint- en galerijmanifests bewaren de broninstellingen, het aantal werkelijk
onderzochte partijen en de indexreeksen. Een onderbroken chunk wordt opnieuw
berekend; alleen volledige, geldige chunks tellen mee. De eindgalerij krijgt
een afzonderlijke onafhankelijke replaycontrole. Ook het ontbreken van een
kwalificerende partij is een geldige, expliciete uitkomst.

## Wat deze galerij niet aantoont

De voorbeelden zijn bewust extreem geselecteerd en niet representatief voor
de gemiddelde partij. Zij mogen niet worden gebruikt als ongecorrigeerde
schattingen voor offerfrequentie, comebackkans, strategiewinstpercentage of
de kans op een bepaalde stapelhoogte. Frequenties vereisen tellers over alle
onderzochte partijen en een afzonderlijke steekproefanalyse.

Alle recordtitels betekenen daarom steeds: **beste gevonden voorbeeld binnen
de opgegeven variant, regels, beleidsmix, seeds, steekproef en zetlimiet**.
