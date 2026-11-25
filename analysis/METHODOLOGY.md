# Methodologische afbakening en onafhankelijke audit

Dit bestand beoordeelt het onderzoeksontwerp onafhankelijk van de enginebouw.
De conclusies moeten worden gelezen naast `VALIDATION.md`, `STRATEGIES.md`,
`COMPLEXITY.md` en de daadwerkelijk voltooide JSON-resultaten. Een experimentplan
is geen meetresultaat. Alleen bestanden met een volledige taakdekking bewijzen
dat een geplande serie is voltooid.

## Diagnostische invariant voor twee passen

Onder de huidige regels kan `blocked` vóór een reguliere eindstand niet optreden.
Het verbonden binnenbord heeft 91 velden en hoogstens 36 bezette velden. Een
niet-lege bezette deelverzameling heeft dus een bezet veld met een vrij
aangrenzend binnenveld. Een speler met voorraad kan daar plaatsen. Zonder
voorraad heeft de eigenaar van die grensstapel een eenstapsbeweging; als de
slagplicht die onderdrukt, bestaat er juist een legale slag. In de gemengde
plaatsingsfase van A kan de speler met voorraad altijd plaatsen. Bij leeg
binnenbord geldt de voorlopige middenherstart, of zonder voorraad is al een
reguliere eindstand bereikt. Minstens één speler heeft dus een legale handeling.
Omdat een pas bord en voorraad niet verandert, kan geen tweede pas volgen.
De aparte teller blijft nuttig als defensieve foutdetectie. Dit bewijs is
afhankelijk van de huidige regels, inclusief de voorlopige middenherstart.

Ook een middenherstart na de beginzet is in een legale volledige partij
onbereikbaar. Alleen ontsnappen kan het laatste actieve binnenveld leegmaken;
de ontsnappende speler heeft dan geen voorraad en geen actieve stapels meer,
waardoor de partij onmiddellijk regulier eindigt. De andere handelingen laten
minstens één actieve stapel over. `center_resets` moet daarom eveneens nul
blijven. Een fallback voor synthetische toestanden verandert dit bereikbaarheidsoordeel niet.

## Eenheid van waarneming en reproduceerbaarheid

De onafhankelijke eenheid is één partij, met een eigen deterministische
pseudowillekeurige stroom afgeleid uit een vaste experimentseed en partij-index.
Dezelfde partij-index moet onafhankelijk van threadaantal, chunkgrootte en
hervattingsmoment dezelfde partij opleveren. Dit wordt praktisch gecontroleerd
door kleine runs met verschillende thread-/chunkindelingen te vergelijken.

De runner gebruikt een SHA-256-afleiding van `(basis-seed, taak-id)` voor een
taakseed. De engine leidt daaruit afzonderlijke partijstromen af. Dit is een
praktische Monte-Carlo-aanname van onafhankelijkheid; het bewijst geen
wiskundige onafhankelijkheid van pseudowillekeurige getallen. Verschillende
strategiecombinaties hebben verschillende taak-id's en dus afzonderlijke stromen.
Een omgewisselde wit/zwart-combinatie is geen gepaarde waarneming, tenzij daarvoor
expliciet dezelfde partijseed en een passende koppeling zijn geïmplementeerd.

Een checkpoint is alleen herbruikbaar bij dezelfde enginesource en executable,
spelregels, strategieën, zetlimiet, seeds en indexreeks. JSON-manifests en
code-/binaryhashes maken deze voorwaarde controleerbaar. Een diagnostische
taakfilter moet als selectie worden geregistreerd: een voltooide subset is geen
voltooide volledige matrix.

## Nulmeting

Uniform willekeurig betekent: kies iedere **legale handeling** met dezelfde
kans. Het betekent niet dat iedere handelingsoort dezelfde kans krijgt. Een
bord met 40 plaatsingen en twee slagzetten geeft een individuele slagzet dus
kans `1/42`, niet `1/4`.

Onder variant A zijn de eerste 36 beurten de gezamenlijke plaatsingsfase.
Onder B is de fase spelergebonden: `reserve` als de actieve speler nog voorraad
heeft, anders `full`, ook als de tegenstander nog stenen kan plaatsen. Een
gemiddeld legaal-zettenaantal moet als `totale keuzes / totale fasebeurten`
worden geaggregeerd; ongewogen gemiddelden van per-partijgemiddelden beantwoorden
een andere vraag.

De relatie tussen als eerste de voorraad uitputten en winnen is observationeel.
Kleur, eerdere slagen, materiaalverdeling en de gekozen speelstijl beïnvloeden
beide. Rapporteer de kruistabel naar kleur, winnaar en onderzoeksafloop. De
uitputtingsvolgorde manipuleren in een apart beleidsvergelijkingsexperiment
benadert een interventie op dat beleid, maar bewijst nog geen op zichzelf staand
causaal voordeel van precies de voorraadvolgorde.

## Zes afzonderlijke eindcategorieën

Iedere partij valt in precies één categorie:

1. Reguliere winst van wit.
2. Reguliere winst van zwart.
3. Reguliere remise op de officiële twee scorecriteria.
4. Afgebroken wegens herhaling.
5. Vastgelopen na twee opeenvolgende passen.
6. Afgebroken op de configureerbare zetlimiet.

De laatste drie categorieën leveren geen vastgestelde reguliere winnaar of
remise op. Zij blijven afzonderlijk zichtbaar in tabellen, CSV en JSON.
De primaire winstpercentages gebruiken **alle gestarte partijen** als noemer.
Een aanvullend percentage onder uitsluitend reguliere uitslagen moet het label
`conditioneel op reguliere afloop` krijgen. Die subset kan door strategie en
variant selectief verschillen.

Een rangschikking kan een onzekerheidsinterval voor de onbekende uiteindelijke
spelerscore laten zien. Met `W` reguliere zeges, `D` reguliere remises,
`U` afgebroken/vastgelopen partijen en `n` totaal ligt de nog niet vastgestelde
gemiddelde score binnen

```text
[(W + 0,5 D)/n, (W + 0,5 D + U)/n].
```

Dit is een **identificatie-interval** voor de onbekende uitkomsten, geen
95%-betrouwbaarheidsinterval. Het kan aanvullend met steekproefonzekerheid worden
gerapporteerd. Afgebroken partijen standaard als halve punten tellen is een
extra onderzoeksscore en mag niet zonder toelichting een officiële remise heten.

## Betrouwbaarheidsintervallen

Voor elke losse uitkomstcategorie is de indicator per partij Bernoulli. Een
tweezijdig 95%-Wilsoninterval gebruikt `z=1,959963984540054`, `p=k/n` en

```text
centrum = (p + z²/(2n)) / (1 + z²/n)
halflengte = z sqrt(p(1-p)/n + z²/(4n²)) / (1 + z²/n).
```

Dit is de score-inversie beschreven in het
[NIST/SEMATECH-handboek, paragraaf 7.2.4.1](https://itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

Deze marginale intervallen hebben niet gezamenlijk 95% dekking voor alle zes
categorieën, 144 matrixcellen of alle strategieverschillen. De nulmeting en
vooraf gekozen contrasten zijn eenvoudiger te interpreteren dan de meest extreme
gevonden cel. Voor confirmatieve claims over vele vergelijkingen zijn aparte
holdoutpartijen en een correctie, bijvoorbeeld Holm voor een vooraf gedefinieerde
familie toetsen, nodig. Een Wilsoninterval om één geselecteerd hoog percentage
verhelpt selectiebias niet.

Voor de gemiddelde geobserveerde duur kan uit de exacte duurhistogram de
steekproefvariantie en `SE=s/sqrt(n)` worden berekend. Een interval
`mean ± 1,96 SE` is bij grote onafhankelijke steekproeven een normale
benadering. Het betreft de **onderzoeksduur met de opgegeven afbreekregels**.
Het is geen schatting van de gemiddelde onbeperkte duur: een limietpartij op
536 beurten kan zonder limiet aanzienlijk langer duren of oneindig doorgaan.
Herhaling en vastlopen zijn eveneens eigen eindprocedures. Zonder aannames over
de voortzetting kan men voor zulke gevallen geen reguliere partijduur imputeren.

De mediaan en andere kwantielen worden uit de histogram aantallen bepaald.
Een exacte mediaan uit een histogram bevat nog steeds steekproefonzekerheid.
Als geen kwantielinterval is berekend, wordt er geen interval gesuggereerd.
De volledige histogram maakt latere intervalberekening en vergelijking van de
staarten mogelijk.

Een conditionele score telt onder de `R=W+L+D` reguliere uitslagen de waarden
1 voor winst, 0,5 voor remise en 0 voor verlies. De schatting is
`m=(W+0,5D)/R`; een normale benadering gebruikt
`SE=sqrt(((W+0,25D)/R-m²)/(R-1))` en `m ± 1,96 SE`.
Dit is een interval voor de conditionele score, geen Wilsoninterval voor een
binomiale winstkans en geen oplossing voor selectieve onderzoeksafbreking.
Intervallen voor geselecteerde fasewinnaars blijven exploratief; de afzonderlijk
gespeelde schema-holdout geeft een nieuwe schatting tegen de vaste referentie.

## Plaatsingsmatrix en selectie van een kampioen

Het ontwerp omvat per variant 12 × 12 geordende combinaties, dus 144 cellen,
inclusief de diagonaal. Met 10.000 partijen per cel zijn dat 1.440.000 partijen
per variant. De rij is wit, de kolom zwart. Wit/zwart omkeren is een ander
experiment: Staxxit heeft een vaste eerste zet en de bordkleuren kunnen een
kleureffect geven.

De bewegingskeuze blijft aanvankelijk voor beide spelers dezelfde. Daardoor
beschrijft de matrix de gevolgen van een plaatsingsheuristiek **onder die
bewegingskeuze**. In variant B beïnvloeden vroege slagkeuzes ook de latere
plaatsingskansen; het gebruikte beleid om plaatsen en slaan te mengen hoort
daarom bij de definitie van iedere matrixcel.

Een kampioen die op basis van deze matrix wordt geselecteerd is een
**verkennende winnaar van deze geteste heuristieken en tegenstanders**. De
grootste gemeten waarde is gemiddeld te gunstig door selectie, vooral bij kleine
onderlinge verschillen. Herhaal kansrijke vergelijkingen met nieuwe seeds voor
een bevestigende schatting. Een ronde-robin-gemiddelde hangt ook af van de
verdeling van tegenstanders; het is geen minimaxwaarde of universeel optimale
strategie.

## Gefaseerde plaatsing

De eerste, middelste en laatste zes plaatsingen worden per speler geteld aan
de hand van het aantal werkelijk geplaatste stenen: 1..6, 7..12 en 13..18.
Slagbeurten in variant B verbruiken geen plaatsingsnummer.

Een studie waarin per fase één van 12 heuristieken varieert en de overige fases
op een geselecteerde vaste kampioen blijven, onderzoekt **lokale vervanging**.
Met beide kleuren en 10.000 partijen per conditie vergelijkt zij nuttige
verbeteringen rond dat referentiebeleid. Zij onderzoekt niet alle `12³=1.728`
eigen faseschema's en ook niet hun volledige interactie met alle schema's van
de tegenstander. Twee afzonderlijk gunstige vervangingen kunnen gecombineerd
ongunstig zijn. Een aanbevolen gemengd schema moet daarom nog als compleet
beleid met nieuwe partijen worden vergeleken.

Selectie van de referentiekampioen uit eerdere data is toegestaan voor
verkennend vervolgonderzoek. Rapporteer de selectieprocedure en gebruik nieuwe
seeds in de faseproeven. De conclusie luidt dan dat een vervanging beter was
tegen de gekozen referentie in deze steekproef, niet dat de optimale strategie
in die fase is bewezen.

## Variant B: vroeg slaan en vroeg ontsnappen

Het geordende beleidsonderzoek vergelijkt de vastgelegde keuzeheuristieken
binnen dezelfde plaatsings- en bewegingsinstellingen. Registreer naast resultaten
ook daadwerkelijk gedrag: hoeveel vroege slagen, hoeveel beurten voorraad
behouden blijft, wanneer de voorraad leegraakt en hoe vaak ontsnappingen vóór
uitputting van de tegenstander optreden. Een beleidsnaam alleen bewijst niet
dat het bedoelde contrast in de gespeelde partijen vaak voorkwam.

Vroeg ontsnappen is pas legaal wanneer de eigen voorraad leeg is. Een proef van
twee ontsnappingsprioriteiten tegen elkaar is dus een beleidsexperiment ná
uitputting van de eigen voorraad, eventueel vóór die van de ander.
Een 2 × 2 vergelijking kan praktische voordelen en tegenvoorbeelden tonen.
Zij kan **geen dominante strategie bewijzen**: dominantie vereist een garantie
tegen alle toegestane tegenstrategieën, niet alleen de bemonsterde opponent.
Een definitieve optimale verhouding plaatsen/slaan is evenmin aangetoond door
een klein eindig aantal handgemaakte mengheuristieken.

## Cycli en boomcomplexiteit

Een werkelijk legale cyclus vereist een vanaf de beginpositie bereikte prefix,
een reeks legale handelingen zonder tussentijdse officiële eindstand, en exact
dezelfde bordpositie, voorraden en speler aan zet aan begin en eind.
Voor de pasregel moet ook de relevante pasgeschiedenis compatibel zijn.
Een opgeslagen en door beide engines nagespeelde getuige kan bewijzen dat die
cyclus zonder voorlopige herhalings-/zetlimietregels eindeloos herhaalbaar is.
Een willekeurige algebraïsch toegestane positie zonder bewezen prefix bewijst
dat niet. Een waargenomen herhalingspercentage is evenmin een exact percentage
van alle mogelijke oneindige spelverlopen.

De Knuthschatter en numerieke beperkingen staan afgeleid in `COMPLEXITY.md`.
Alleen de uniforme nulmeting kan de gewone producten van **alle** legale
vertakkingsaantallen gebruiken om de volledige afgeknotte geschiedenisboom te
schatten. Bij strategisch beperkte selectie blijft een ongewogen product een
beschrijvende padmaat; het is geen geldige schatter voor die volledige boom.
Rapporteer voor boomschattingen altijd de afknotting, rekenkundig gemiddelde via
log-sum-exp, batchvariatie en ESS. Zware staarten kunnen een ogenschijnlijk
stabiel gemiddelde misleidend maken; een uniforme foutgarantie is niet verkregen.

## Vooraf vastgelegde rapportagegrenzen

- Noem een volledige serie alleen voltooid bij alle gevraagde aantallen per cel.
- Scheid officiële uitslagen van onderzoeksafbrekingen in iedere hoofdvergelijking.
- Label ranglijsten en fasekeuzes als verkennend.
- Beperk causale en optimale claims tot wat het experiment werkelijk manipuleert.
- Behandel configuratiebovengrenzen, geschatte boomgrootte en speelsterkte als
  drie verschillende grootheden.
- Houd voorafgaande metingen met gewijzigde regels of foutieve engines buiten de
  definitieve resultaten; bewaar hun diagnose met een herkenbaar label.

Primaire methodologische bron voor de boomschatting:
[Belov e.a., IJCAI 2017, paragraaf 2](https://ijcai.org/proceedings/2017/67), die
de Knuthschatter met selectiekansen en de variantieproblematiek uitwerkt.
