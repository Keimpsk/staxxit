# Wiskundige complexiteit van Staxxit

De berekeningen in dit bestand zijn daadwerkelijk uitgevoerd met `complexity.py`.
De volledige gehele getallen en controles staan in `results/complexity.json`.
Het gaat om **bovengrenzen voor posities**, niet om een telling van alle bereikbare
spelposities en evenmin om een bewijs van een optimale strategie.

## Wat is één positie?

Een positie bevat de kleur die aan zet is, de twee voorraden en op elk van de 127
onderscheiden coördinaten de geordende rij steenkleuren van onder naar boven.
Ontsnapte stapels blijven op hun afzonderlijke buitenvelden staan. Stenen van
dezelfde kleur zijn onderling ononderscheidbaar. Rotaties en spiegelingen worden
niet geïdentificeerd. Die zouden bovendien de kleur van het buitenveld en de
speler die begint moeten respecteren.

De voorraden en alle binnen- en buitenstapels samen bevatten steeds precies 18
witte en 18 zwarte stenen. Een stapel met twee witte en één zwarte steen heeft
bijvoorbeeld drie verschillende volgordes: WWZ, WZW en ZWW.

Een bordpositie hoeft niet voldoende geheugen te bevatten om de voorlopige
onderzoeksregels toe te passen: de passteller, eerdere herhalingen en het aantal
verstreken beurten horen bij de toestand van de **partijanalyse**. Zij worden
hier niet meegeteld in het aantal bordposities.

## Genererende functie

Laat `x` een witte steen en `y` een zwarte steen markeren. Een binnenveld mag leeg
zijn of een willekeurige niet-lege kleurstring bevatten. Zijn genererende functie
is daarom

```text
S(x,y) = 1 + (x+y) + (x+y)^2 + ... = 1/(1-x-y).
[x^w y^b] S^m = C(m+w+b-1,w+b) C(w+b,w).
```

De tweede factor telt de kleurvolgorde, de eerste verdeelt een kleurstring over
`m` onderscheiden stapels, met lege stapels toegestaan.

Een extra noodzakelijke beperking volgt uit de geometrie: een ontsnappende
stapel heeft hoogte **ten hoogste 11**. Het actieve bord heeft straal 5, de
buitenring straal 6. Een rechte lijn vanuit een binnenveld bereikt de buitenring
na maximaal 11 stappen. Ontsnappen moet precies op de stapelhoogte gebeuren.
Na ontsnapping kan een stapel niet meer veranderen. Deze beperking is scherper
dan alleen een beperking op de bovenste kleur.

Definieer

```text
H10 = sum((x+y)^h, h=0..10)
N11 = sum((x+y)^h, h=0..11)
W11 = 1 + x H10
B11 = 1 + y H10
F(x,y) = S^91 N11^6 W11^15 B11^15.
```

`W11` telt lege witte buitenvelden of strings met een witte bovensteen; `B11`
doet hetzelfde voor zwart. Een neutraal buitenveld mag beide topkleuren hebben.
Alle gemengde kleuren onder de bovensteen tellen mee, ook in de eindscore.

Noem `f(w,b)` de coëfficiënt van `x^w y^b` in `F`. Voor een vaste voorraad
`(r_w,r_b)` zijn er precies `f(18-r_w,18-r_b)` configuraties in deze verruimde
configuratieruimte. De voorraad is door `w,b` bepaald en levert dus geen extra
permutatiefactor op. De kleur aan zet levert voor een veilige bovengrens een
factor twee op.

## Variant A

Na de plaatsingsfase zijn beide voorraden nul. Hiervoor volgt

```text
2 f(18,18)
= 637661402840420185012089800965417367804333680
≈ 6,376614028404 × 10^44.
```

In de plaatsingsfase zijn er uitsluitend enkelvoudige stenen op binnenvelden,
geen ontsnapte stapels, en blijft de eerste witte steen op het middenveld.
Na `t=1..35` plaatsingen gelden `w=ceil(t/2)` en `b=floor(t/2)`. De speler aan
zet is door `t` bepaald. Wanneer de verplichte aaneengesloten plaatsing tijdelijk
wordt losgelaten, geeft dit per `t`

```text
C(90,w-1) C(91-w,b).
```

Inclusief de unieke lege beginpositie is de som voor `t=0..35`

```text
23416540714091893007807969656069358
≈ 2,341654071409 × 10^34.
```

De toestand na plaatsing 36 behoort tot de bewegingsfase en wordt niet nogmaals
geteld. Samen is de configuratiebovengrens voor variant A dus

```text
637661402863836725726181693973225337460403038
≈ 6,376614028638 × 10^44; log10 = 44,804590130284176.
```

Omdat maximaal 36 stenen op 91 binnenvelden staan, kan de plaatsingsfase van A
niet door een vol bord vastlopen. De actieve velden vormen een verbonden
zeshoekig bord: een niet-lege echte deelverzameling heeft een vrij aangrenzend
veld. Beide spelers kunnen daardoor al hun stenen plaatsen.

## Variant B

Alle voorraden `0..18` worden toegelaten, ook combinaties die beurtvolgorde of
verplichte beëindiging in een echte partij zouden uitsluiten. De bovengrens is

```text
2 sum(f(w,b), w=0..18, b=0..18)
= 823444427278144967900654111032274842667357228
≈ 8,234444272781 × 10^44; log10 = 44,91563429477373.
```

Equivalent is dit `2 [x^18 y^18] F/((1-x)(1-y))`. Iedere geometrische configuratie
legt precies één bijbehorende reservecombinatie vast.

## Controle en bereikbaarheid

`complexity.py` vermenigvuldigt de celpolynomen met gehele getallen en kapt alleen
coëfficiënten boven 18 per kleur af. Zulke termen kunnen bij vermenigvuldiging met
polynomen met niet-negatieve exponenten nooit terugkeren naar het geldige bereik.
De afkapping verliest daarom geen geldige coëfficiënten.

Als onafhankelijke controle wordt de beperking op ontsnapte hoogtes losgelaten.
Dan geldt `F_relaxed = S^97 (1+xS)^15 (1+yS)^15`. Expansie naar de aantallen
bezette witte en zwarte buitenvelden geeft de gesloten formule

```text
f_relaxed(w,b) = sum over i=0..min(15,w), j=0..min(15,b):
 C(15,i) C(15,j) C(96+w+b,w+b-i-j) C(w+b-i-j,w-i).
```

Alle **361** coëfficiënten van deze onafhankelijke formule zijn gelijk aan de
rechtstreekse cel-DP. Verder zijn alle coëfficiënten symmetrisch onder verwisseling
van wit en zwart en wordt de bovengrens nergens groter door de hoogtebeperking.
Eén losse witte steen heeft 112 mogelijke velden: 91 binnen, 15 wit buiten en
6 neutraal buiten. Ook die controle slaagt.

Bereikbare posities vormen een deelverzameling van deze configuraties. Nog niet
volledig afgedwongen zijn onder andere de plaatsingsadjacentie, centrumstart,
stapelvorming uitsluitend via vijandelijke overnames, toegestane splitsneden,
slagplicht, beurtvolgorde en het onmiddellijk stoppen van een partij. Ook kan
de beschikbare ruimte tijdens eerdere zetten een configuratie onbereikbaar
maken. De exacte omvang van beide bereikbare verzamelingen is hier niet bepaald.
Een willekeurige simulatiebezoekentelling kan die exacte omvang evenmin bewijzen.

Dit onderzoek van één vast bord bewijst geen asymptotische classificatie zoals
PSPACE-hardheid. Daarvoor moet eerst een familie van bordgroottes en algemene
beslissingsproblemen worden gedefinieerd.

## Spelboomschatting

De boom van zetgeschiedenissen verschilt van de graaf van bordposities: meerdere
geschiedenissen kunnen hetzelfde bord bereiken. Een eindige positievoorraad
bewijst daarom geen eindige, onbeperkte spelboom. Zonder definitieve
herhalingsregel is niet aangetoond dat alle mogelijke spelverlopen eindigen.
Het feit dat materiaal behouden blijft is geen strikt dalende grootheid:
gewone bewegingen zijn omkeerbaar wanneer geen slagplicht in de weg staat.

Voor de simulaties is de onderzochte boom expliciet begrensd door de gekozen
zetlimiet en de voorlopige pas- en herhalingsregels. Een pas is één verplichte
opvolger. Een reguliere einduitslag, tweede opeenvolgende pas, derde herhaling
of zetlimiet is een blad. Verschillende herhalingsgeschiedenissen blijven
verschillende boomknopen, ook als zij hetzelfde huidige bord tonen.

De gebruikte methode bouwt voort op willekeurige padschatting van
[Knuth (1975)](https://www-cs-faculty.stanford.edu/~knuth/persi75-talk.pdf).
Een moderne primaire uiteenzetting met expliciete selectiekansen staat bij
[Belov e.a. (IJCAI 2017), paragraaf 2](https://ijcai.org/proceedings/2017/67).
Bij uniforme keuze uit alle legale opvolgers, met vertakkingsaantallen
`b_0,...,b_(D-1)`, is een padschatting voor het totale aantal boomknopen

```text
Z = 1 + b_0 + b_0 b_1 + ... + product(b_i, i=0..D-1).
```

De verwachting van `Z` is de grootte van die **afgeknotte** boom: een knoop op
diepte `d` wordt bezocht met kans `1/product(b_i,i<d)` en draagt bij bezoek juist
de inverse kans bij. Voor het aantal knopen op een vaste diepte gebruikt men
alleen de betreffende productterm en telt men nul als het pad eerder eindigt.

De engine slaat de logaritmen van de schattingen op. Het rekenkundige gemiddelde
moet als `logsumexp(log Z_1,...,log Z_n)-log(n)` worden berekend; het gemiddelde
van `log Z` is de log van een geometrisch gemiddelde en is **geen** onvertekende
boomgrootteschatter. Ook `gemiddelde vertakking ^ gemiddelde duur` heeft hier
geen geldige afleiding.

Voor andere gedragsstrategieën zijn uniforme vertakkingsproducten niet geldig
voor de volledige spelboom. Bij bekende positieve selectiekansen kunnen inverse
padkansen worden gebruikt; een deterministische strategie die sommige legale
zetten kans nul geeft, kan de volledige boom niet op deze manier schatten.
De nulmeting met uniforme zetten is daarom de geschikte bron.

### Onzekerheid en interpretatie

Rapporteer naast de schatting het aantal onafhankelijke partijen, de limiet,
de herhalings-/pasafspraak en de variatie tussen onafhankelijke batches.
Bij loggewichten `z_i=log Z_i` kan uit `S1=sum(exp(z_i))` en
`S2=sum(exp(2 z_i))` de diagnostische effectieve steekproefgrootte
`ESS=S1^2/S2` worden berekend. Een laag ESS betekent dat weinig paden de
schatting dragen. `ESS` is geen bewijs van nauwkeurigheid.

Voor empirische standaardfouten en eventueel batch-bootstrap moeten de gewichten
eerst numeriek stabiel worden herschaald. Een smal interval op logwaarden meet
alleen de spreiding van logwaarden; het is geen interval voor het rekenkundige
boomgemiddelde. Zelfs zeer grote aantallen partijen kunnen zeldzame zware
staarten missen. Daarom zijn de uitkomsten een verkennende orde-inschatting
voor de geregistreerde afknotting, geen gegarandeerd betrouwbaar totaal voor
de onbeperkte spelboom en geen bewijs van minimaxcomplexiteit.

Voor een exact Markov-model van de onderzoeksregels zou men ook de passteller,
de resterende zetlimiet en de herhalingsadministratie opnemen. Als `N` een
bovengrens voor bordposities met speler aan zet is, geeft bijvoorbeeld
`2 (L+1) N 3^N` een zeer grove bovengrens voor zulke geaugmenteerde toestanden
vóór de derde herhaling. Dat getal wordt niet als spelcomplexiteitsresultaat
gepresenteerd: vrijwel alle combinaties van geschiedenis en bord zijn onmogelijk.

## Reproduceren

```powershell
python analysis/complexity.py --output analysis/results/complexity.json
```

Er zijn geen externe Python-pakketten nodig. Het script schrijft alle grote
getallen als decimale strings naar JSON om afronding in JSON-clients te voorkomen.
