# Onderzoeksregels en aannames

Bron: de gebruikersopdracht van 25 november 2026. Deze regels hebben voorrang op
de bestaande simulator. De HTML/JavaScript-simulator is geen onderdeel van deze wijziging.

Het bord heeft 91 binnenvelden (axiale afstand tot midden <=5) en 36 buitenvelden
(afstand 6). Beide kleuren hebben 18 stenen, inclusief voorraad, actieve en
ontsnapte stenen. Een stapel bewaart de kleuren van onder naar boven; de bovenste
steen bepaalt de eigenaar. Wit begint en plaatst in het midden. Elke handeling
en elke pas wisselt de beurt.

Plaatsen kan alleen vanuit de eigen voorraad op een vrij binnenveld dat aan
een aanwezige actieve steen of stapel grenst. Bij een leeg binnenbord wordt
voorlopig opnieuw in het midden geplaatst. Bewegen gaat recht in een van zes
richtingen, maximaal de eigen stapelhoogte, zonder andere stapels te passeren.
Een vijandelijke stapel slaan of naar buiten ontsnappen kan alleen op exact de
eigen stapelhoogte. Bij slaan komt de volledige aanvaller boven op het doel.
Een eigen stapel slaan is verboden. Ontsnappen kan naar een vrij eigenkleurig
of neutraal buitenveld; ontsnapte stapels blijven daar en bewegen niet meer.

Een stapel met hoogte >=12 kan in één beurt gesplitst worden. Een niet-lege
bovenste deelstapel gaat naar een vrij aangrenzend binnenveld. Beide resterende
topstenen moeten van de actieve speler zijn. Splitsen houdt de volgorde intact.

Variant A: eerst alle 36 stenen plaatsen, dan bewegen. Een beschikbare slag
heeft in de bewegingsfase voorrang op elke beweging, splitsing of ontsnapping.
Variant B: bij eigen voorraad >0 zijn alleen plaatsen en facultatief slaan
beschikbaar. Zodra de eigen voorraad nul is, zijn alle normale handelingen
beschikbaar en geldt de normale globale slagplicht, onafhankelijk van de
tegenstandervoorraad.

De partij eindigt direct na een handeling als een speler geen eigen actieve
stapel en geen voorraad meer heeft; bij A alleen na de plaatsingsfase. De
lexicografische score is (aantal bezette buitenvelden, totaal aantal stenen
in die ontsnapte stapels). Alle kleuren in een ontsnapte stapel tellen mee
voor de eigenaar. Gelijke scores geven een reguliere remise.

## Voorlopige afbreekregels

Geen legale handeling geeft een pas; twee opeenvolgende passen geven `blocked`.
De derde herhaling geeft `repeat`. De sleutel bevat aanzetkleur, beide voorraden,
alle geordende binnen-/buitenstapels en de pasteller. De variant ligt per partij
vast. De geschiedenis voor het tellen van eerdere toestanden wordt afzonderlijk
bewaard en maakt het onderzoeksproces eindig. De beginstand telt mee.

De standaardzetlimiet is 536 beurten, inclusief passen, instelbaar via `--limit`.
Als geen eerdere beëindiging optreedt, volgt `limit`. `repeat`, `blocked` en
`limit` worden afzonderlijk geteld en krijgen geen reguliere winnaar/remise.
Herplaatsingen op leeg binnenbord, passen en vroege ontsnappingen worden
afzonderlijk geteld. Gemeten partijduur is de duur onder deze afbreekregels.

## Buitenring

De opdracht specificeert aantallen, maar geen coördinaten voor de kleuren.
We behouden de indeling van beide aangeleverde engines: start bij (6,0), loop
de zes zijden in richtingen (-1,1), (-1,0), (0,-1), (1,-1), (1,0), (0,1).
Iedere hoek is neutraal; de vijf tussenvelden per zijde zijn doorlopend
afwisselend wit en zwart, beginnend met wit. Dit levert 15+15+6 velden.
Conclusies gelden voor deze concrete ringindeling; een andere indeling is
een ander experiment.
