# Exacte definities van de onderzochte heuristieken

Dit zijn reproduceerbare, begrensde strategieën voor empirische vergelijking.
Een beste score in deze experimenten bewijst geen speltheoretisch optimale
strategie. De engine gebruikt nulgebaseerde nummers 0–11; de opdracht nummerde
dezelfde twaalf strategieën 1–12.

## Plaatsing

Voor iedere legale plaatsing op `t` worden de volgende grootheden bepaald:

- `O(t)` en `E(t)`: aantallen aangrenzende **actieve stapels** met respectievelijk
  de eigen en de vijandelijke bovenkleur. Eén aangrenzende stapel telt één keer,
  ongeacht de hoogte of de kleuren van onderliggende stenen.
- `d(t,p) = max(|q_t-q_p|, |r_t-r_p|, |q_t+r_t-q_p-r_p|)`:
  afstand op het zeshoekige rooster.
- `r(t) = d(t,midden)`.
- `V(p,t)`: aantal lege aangrenzende binnenvelden van vijandelijke stapel `p`
  **na** het hypothetisch plaatsen op `t`. Buitenvelden tellen niet als vrije
  plaatsings- of binnenbewegingsruimte.

De maximale score wordt gekozen; bij gelijke scores kiest de engine uniform.
Iedere score wordt opnieuw uit de actuele toestand berekend.

| Engine-ID | Strategie | Te maximaliseren score |
|---:|---|---|
| 0 | Willekeurig | Uniform over alle legale plaatsingen |
| 1 | Naast zoveel mogelijk eigen stenen | `O(t)` |
| 2 | Naast zoveel mogelijk vijandelijke stenen | `E(t)` |
| 3 | Naast eigen én vijandelijke stenen | `7 min(O(t),E(t)) + O(t) + E(t)` |
| 4 | Zo min mogelijk vijandelijke buren | `-E(t)` |
| 5 | Compact plaatsen | `-Σ d(t,p)` over alle eigen actieve stapels `p` |
| 6 | Verspreid plaatsen | `Σ d(t,p)` over alle eigen actieve stapels `p` |
| 7 | Richting centrum | `-r(t)` |
| 8 | Richting buitenring | `r(t)` |
| 9 | Tegenstanders omsingelen | `Σ [6 - V(p,t)]` over vijandelijke buren `p` van `t` |
| 10 | Eigen mobiliteit maximaliseren | Aantal legale acties in de hieronder gedefinieerde hypothetische eigen bewegingsfase |
| 11 | Tot ongunstig slaan verleiden | `7 B(t) + O(t) - E(t)`, met `B(t)` hieronder |

Bij strategie 3 maakt factor 7 het minimum van de twee buurtypen belangrijker
dan de totale bezetting: het totaal bedraagt hoogstens 6. Bij strategieën 5 en
6 tellen alle eigen actieve stapels mee, zonder gewichten naar hoogte. Zonder
eigen actieve stapel is de afstandssom nul.

**Mobiliteit, strategie 10.** Plaats eerst hypothetisch de eigen steen op `t`,
zet daarna uitsluitend voor de scoreberekening de eigen voorraad op nul en
roep de normale generator voor variant B aan voor dezelfde speler. De score
is de grootte van die legale-actieset, inclusief de normale slagplicht,
splitsingen en ontsnappingen. De tegenstandersvoorraad blijft staan. Dit is een
exact berekende, expliciet contrafeitelijke mobiliteitsmaat; ze voorspelt geen
volledige toekomstige bewegingsfase. De echte speltoestand verandert niet.

**Lokzetten, strategie 11.** Voor iedere vijandelijke stapel van hoogte 1 naast
`t` wordt diens mogelijke toekomstige slagzet naar de nieuw geplaatste steen
bekeken. Het vertrekveld wordt dan leeg en de vijandelijke stapel op `t` heeft
hoogte 2. Vanuit `t` wordt op iedere rechte straal de eerste overblijvende
actieve stapel gezocht. Is die eigen en is zijn hoogte precies gelijk aan zijn
afstand tot `t`, dan kan hij onmiddellijk terugslaan. `B(t)` is de som van
zulke terugslagmogelijkheden over alle naburige vijandelijke aanvallers.

Deze lokzetheuristiek waardeert een mogelijke terugslag; hij bewijst niet dat
de tegenstander die specifieke slagzet zal kiezen. Andere verplichte slagzetten
elders kunnen ook beschikbaar zijn. In variant A wordt de toekomstige slagzet
uitsluitend voor de score berekend; tijdens de echte plaatsingsfase wordt niet
geslagen. De factoren en gewichten zijn vooraf gekozen en niet op de
gerapporteerde winstpercentages afgestemd.

## Gemeenschappelijke bewegingsstrategie en actietypekeuze

Zonder aanvullende policy worden alle legale acties uniform bemonsterd. Als de
getrokken actie een plaatsing is en de plaatsingsstrategie niet 0 is, wordt de
plaatsingsbestemming vervangen door een maximale-scoreplaatsing. Daardoor
blijft bij variant B de kans op het **actietype** plaatsen of slaan voor alle
twaalf plaatsingsstrategieën gelijk aan hun aandeel in de legale-actieset.
Na het uitputten van de eigen voorraad blijven beweging, slagzet, splitsing en
ontsnapping uniform over de legale acties. De slagplicht staat altijd boven de
strategie.

## Variant B: voorraad- en slagbeleid

De CLI accepteert `--white-policy` en `--black-policy` onafhankelijk, of
`--policy` voor beide spelers. De onderstaande policies gelden zolang er
voorraad is. Bij een lege voorraad kiest de speler uniform uit de normale
legale-actieset. Binnen gekozen plaatsingen geldt de ingestelde
plaatsingsstrategie.

| Policy-ID | Naam | Exacte keuze |
|---:|---|---|
| 0 | Uniform | Uniform actietype-/actiegedrag zoals hierboven |
| 1 | Zo snel mogelijk plaatsen | Kies een plaatsing zolang er een beschikbaar is |
| 2 | Slaan zodra mogelijk | Kies uniform een slagzet als er één is; anders plaatsen |
| 3 | Laatste drie in voorraad houden | Bij meer dan 3 voorraad: plaatsen. Bij hoogstens 3: slaan indien mogelijk, anders plaatsen |
| 4 | Alleen tactisch gunstig slaan | Kies een maximale-score-slagzet als de beste tactische score minstens 1 is; anders plaatsen |
| 5 | Dynamisch beleid | Beste tactische slagzet bij score minstens 0 met meer dan 6 voorraad, en minstens 2 met hoogstens 6 voorraad; anders plaatsen |

Voor slagzet `a` is de tactische score `h_doel - kwetsbaar × h_resultaat`.
`kwetsbaar` is 1 wanneer de tegenstander in de toestand na `a` een legale slagzet
heeft naar precies de nieuwe eigen stapel, anders 0. `h_resultaat` telt beide
samengevoegde stapels. Hiervoor wordt de volledige legale generator voor de
tegenstander aangeroepen met diens werkelijke voorraad. Bij meerdere beste
slagzetten is de keuze uniform. Bij afwezigheid van slagzetten kiest het beleid
een plaatsing. Vrijwillig passen is niet toegestaan. Policy 3 garandeert dus
geen blijvende voorraad: wanneer slaan onmogelijk is, wordt doorgeplaatst.

Dit beleid vergelijkt concrete heuristieken, geen exacte minimaxwaarde.
De ratio vroegtijdig slaan/plaatsen wordt **gemeten** uit
`early_capture_by_player` en `actions_by_player[speler][0]`; het is geen vooraf
opgelegde constante verhouding.

## Vroegtijdig ontsnappen

Met `--white-escape-first` of `--black-escape-first` kiest die speler uniform
een ontsnapping zodra een ontsnapping in zijn legale-actieset staat. Dit
respecteert de slagplicht. `early_escape` betekent dat de eigen voorraad leeg
is en de tegenstander nog voorraad heeft. De vlag blijft ook na de
plaatsingsfase actief; een winstverschil is daarom het totale effect van deze
voorkeur, niet uitsluitend een causaal effect van de vroege ontsnappingen.
Empirisch succes tegen de geteste policies bewijst geen dominante strategie.

De suite `early_escape` gebruikt afzonderlijke opties
`--white-early-escape-first` en `--black-early-escape-first`. De prioriteit
geldt uitsluitend zolang de tegenstander voorraad heeft. Zodra die voorraad
leeg is, keert de speler terug naar uniforme keuze uit de legale acties.
Slagplicht bepaalt eerst de legale set. De prioriteit verandert alleen de
keuze wanneer die set minstens één ontsnapping bevat.

Beide spelers plaatsen volgens ID 8. Bij twee uniforme voorraadbeleidsregels
worden de vier combinaties van vroege prioriteit onderzocht. Twee extra
paren vergelijken de schakelaar voor de snel plaatsende speler (policy 1)
tegen een tegenstander die zo vaak mogelijk vroeg slaat (policy 2).
Beide kleurtoewijzingen worden getest. Elke conditie heeft 100.000 partijen
met eigen taak-seed. Prestaties worden over alle partijen in de conditie
gemeten, inclusief afbrekingen als afzonderlijke uitkomsten. Zo wordt
selectie op het daadwerkelijk voorkomen van vroege ontsnapping vermeden.

## Eerste, middelste en laatste zes plaatsingen

`--white-schedule a,b,c` en `--black-schedule a,b,c` kiezen het strategie-ID
op basis van het aantal **eigen daadwerkelijk geplaatste stenen**: 0–5, 6–11,
12–17. Vroegtijdige slagzetten verhogen dat aantal niet. Een schedule-ID `-1`
gebruikt de gewone `--white` of `--black` strategie. De scorefuncties veranderen
verder niet. Gefaseerde experimenten tegen een vaste referentie onderzoeken
lokale vervanging per fase; ze doorzoeken niet alle `12³` schedules of alle
tegenstanders.

## Reproduceerbaarheid en metingen

De generator is expliciet SplitMix64 met rejection sampling voor uniforme
gehele getallen. Een partij heeft seed `mix(seed XOR mix(game_id))`; `game_id`
is `start + lokaal_partijnummer`. Er wordt geen thread-ID in verwerkt.
Integer-tellingen zijn daardoor gelijk bij een ander aantal threads of andere
checkpointindeling voor hetzelfde ID-bereik. De gesommeerde logschatters kunnen
door floating-pointoptelling in een andere volgorde op de laatste decimalen
verschillen. Dezelfde seeds tussen strategieën geven reproduceerbare
experimenten; na afwijkende acties lopen de trajecten vanzelf uiteen.

`source_heights[h]` telt de hoogte van de vertrekkende stapel bij iedere
niet-plaatsingsactie, **vóór** die actie. `max_heights[h]` telt partijen waarvan
de grootste ooit waargenomen stapelhoogte `h` was. Dit zijn gebeurtenis- en
partijhistogrammen, geen uniforme steekproef van alle stapels in alle posities.

`phase_turns` en `phase_choices` gebruiken de eigen voorraad vóór de beurt:
index 0 betekent voorraad aanwezig, index 1 eigen voorraad leeg. De drie
`placement_phase_*` buckets gebruiken dezelfde drie groepen van zes eigen
plaatsingen; in variant B tellen daar ook beurten met een vroege slagzet mee.

De enginesleutel voor herhaling bevat speler aan zet, beide voorraden,
opeenvolgende passen en alle bezette velden met de complete steenreeks van
onder naar boven. De herhalingsteller zelf is de geschiedenis van deze sleutel;
deze onderzoekscutoff verandert de onderliggende zetten niet. Buitenstapels
blijven voor steenbehoud en score in de toestand staan en genereren geen acties.

Elke partij eindigt met een actieve runtimecontrole van exact 18 stenen per
kleur, inclusief voorraad en ontsnapte stenen. Met `--verify-every-step`, dat
de onderzoeksscripts gebruiken, wordt bovendien na iedere handeling
gecontroleerd. Deze controle blijft werken bij releasecompilatie met `NDEBUG`.
