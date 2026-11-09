# FreeCAD–Z1: Fra modell til ferdig del

**Produktvisjon og fremtidig UX-design · versjon 0.1 · 7. november 2026**

Status: beslutningsgrunnlag og foreslått design. Dokumentet beskriver en fremtidig løsning, ikke funksjonalitet som allerede er implementert. Primærbruker er en teknisk interessert hjemmebruker med FreeCAD CAM, Makera Z1 og Windows. Første mål er pålitelig tre-akset fresing. OpenSpindle er foreslått mottaker; endelig valg av kjørebackend krever fysisk validering.

## 1. Visjonen

**Jeg skal kunne ferdigstille en CAM-jobb i FreeCAD, trykke «Klargjør på Z1», forstå nøyaktig hva maskinen skal gjøre, kontrollere det fysiske oppsettet og starte med trygghet om at riktig versjon blir kjørt.**

Brukeren skal arbeide med delen og oppsettet. Filnavn, eksportmapper, postprosessorinstallasjon, nettverksadresser og køfiler skal normalt håndteres av løsningen. Eksportert G-kode skal fortsatt være tilgjengelig for inspeksjon og vanlig manuell overføring.

Produktet bør oppleves som én arbeidsflyt fordelt over to arbeidsflater: FreeCAD for konstruksjon og CAM, OpenSpindle for maskinoppsett og kjøring. Samme jobbnavn, revisjon, operasjoner og verktøy følger med hele veien. En tydelig overgang er bedre enn å bygge enda en full CAM- eller kontrollerapplikasjon.

En moderne flyt betyr færre gjentatte beslutninger, synlig tilstand og lett feilretting. Den betyr ikke at fresestart automatisk følger etter filoverføring.

## 2. Undersøkelsesgrunnlag og sikkerhet i konklusjonene

Grunnlaget er gjennomgang av prosjektkode, offisiell dokumentasjon og tidligere kodegjennomgang i denne samtalen. Ingen av de eksterne produktene er brukertestet i denne undersøkelsen, og ingen fysisk Z1 er brukt. Sammenligningen identifiserer dokumenterte designmønstre; den er ikke en rangering av faktisk brukervennlighet eller driftssikkerhet.

Vår bro ble undersøkt på commit `7a4b69a5151c2b18b530698657d1a5d0ce53312e`; Controller-mottakeren på `185ba615ae408c84986e83e16d0eb529ab79b978`. Ti eksisterende offline-tester passerte. Ekstra simuleringer viste at en sen callback kan fullføre feil forespørsel, og at valgt fil kan byttes etter overgang til Run. Dette er konkrete utbedringer før videre automatisering. [1–2]

OpenSpindle ble undersøkt på main `c2e055b389cca7fd85ac6948b0affd297f07bce3`. Dokumentasjonen beskriver mer enn siste publiserte pakke: v0.3.0 har bare macOS-artefakter, mens main inneholder Windows-støtte. README oppgir fortsatt kjørestart, pause/resume og verktøybytter som ikke fysisk verifisert på Z1. En lovende arkitektur er derfor ikke tilstrekkelig grunn til å erstatte en fungerende kontroller umiddelbart. [3–6]

## 3. Hva vi lærer av andre verktøy

| Produkt / kilde | Dokumentert mønster | Overføring til FreeCAD–Z1 |
|---|---|---|
| Bambu Studio | Prosjektbasert arbeid, flere plater, G-kodevisning, fjernstyring og overvåkning | Bruk ett vedvarende jobbkort med miniatyr og oppsett; behold sammenhengen mellom forberedelse og maskin. [7] |
| PrusaSlicer / Prusa Connect | Integrert Connect-fane, direkte sending, kø og ulike valg for lagring og start | Integrer tilkobling og status i arbeidsflyten. Skill profil fra fysisk maskin, og opplasting fra kjøring. [8–9] |
| OctoPrint | Filopplasting, valg av fil og jobbkommandoer har separate API-operasjoner | Modellér import, maskinoverføring og start som forskjellige handlinger med egne bekreftelser. [10] |
| Autodesk Fusion Manufacture | Simulering kombinerer visning og verifikasjon; problemer kan finnes i en liste og på tidslinjen | La brukeren klikke et problem og se aktuell operasjon, bevegelse og geometri. Vis hva som faktisk er kontrollert. [11–12] |
| Makera Studio | Samlet CAM/kontroller, veiviser og Z1-oppsett med blant annet Anchor 1 og Scan Margin | Gjør maskinens konkrete oppsett forståelig visuelt. Gjenbruk Z1-begreper fremfor generiske CNC-dialoger. [13–14] |
| OpenSpindle | Z1-bord, emne, oppspenning, import, verktøymatching, kontrollregler og kjørevisning | Bruk som kandidat for mottaker og operatørflate. Utvid kildekoblingen til FreeCAD. [3–6] |
| Community Fusion Plugin | Gruppering per operasjon, oppsett og verktøy, med vurdering av koordinatsystemer | Tilby eksplisitte oppsett og stabil operasjonsidentitet, særlig når en del skal snus. [15] |
| CNC-Proxy | Varig kø, synlig synkroniseringsstatus, API og WebDAV | Lær av diagnostikken og gjenopprettingen. Z1-kompatibilitet må undersøkes før eventuell bruk som transport. [16] |

Den beste syntesen er **prosjektorienteringen fra slicerne, statusflyten fra Prusa Connect, kontrollforklaringen fra Fusion og den fysiske Z1-konteksten fra OpenSpindle**. Dette er en designanbefaling, ikke en påstand om at ett produkt allerede løser hele behovet.

Det vi ikke bør overføre direkte fra 3D-printing, er antakelsen om en automatisk ny jobb på en klar byggeplate. CNC krever at fysisk emne, oppspenning, verktøy og nullpunkt stemmer med akkurat dette oppsettet. En ferdig køjobb gjør ikke neste emne klart.

## 4. Brukssituasjoner som skal styre designet

**Første del:** Brukeren kjenner FreeCAD, men er usikker på sammenhengen mellom CAM-nullpunkt og Anchor 1. Oppgaven er å gjøre overgangen forståelig uten å kreve at brukeren lærer en ekstra intern datamodell.

**Daglig iterasjon:** En lomme blir 2 mm dypere. Brukeren vil oppdatere jobben og se hva som endret seg, uten å velge samme verktøy og oppspenning på nytt.

**Ny del i kjent oppspenning:** Samme brakett eller jigg brukes igjen. Programvareoppsettet kan gjenbrukes, mens den faktiske plasseringen og relevante målinger må bekreftes på nytt.

**Avbrudd:** Nettverk eller app forsvinner mens maskinen kjører. Brukeren trenger en korrekt forklaring på hva som er kjent, ikke en grønn «ferdig»-melding eller et nytt startforsøk.

**To oppsett:** Delen snus for baksidebearbeiding. Systemet skal vise ny orientering, nytt oppsett og målebehov som en tydelig fysisk overgang.

## 5. Den ønskede brukerreisen

### Første oppsett: én gang per installasjon

En installert FreeCAD-utvidelse legger til kommandoen «Klargjør på Z1» og et lite maskinpanel. Veiviseren finner lokal OpenSpindle, viser hvilken versjon som er tilgjengelig, og lar brukeren velge en fysisk maskin. Tilkobling kan testes uten bevegelse. Maskinprofil, postprosessorversjon og kommunikasjonsstøtte kontrolleres og vises samlet.

Maskinen får et menneskelig navn, eksempelvis «Z1 – verksted». Identiteten bindes til stabil maskin-ID der protokollen gir det; ellers brukes en uttrykkelig bekreftet tilkoblingsprofil. IP-adressen alene er ikke tilstrekkelig identitet. Flytting til en annen maskin krever et synlig valg.

Ingen miljøvariabler eller manuell JSON-redigering i normal oppstart. Diagnostikk skal kunne eksporteres ved problemer, med nettverksdetaljer og filstier skjult eller redigert før deling.

### A. Klargjør i FreeCAD

Panelet viser valgt CAM-jobb, målmaskin, materiale, emnestørrelse, operasjoner og verktøy. Brukeren velger et helt oppsett. Delvis eksport er et avansert valg som viser avhengigheter og hvilke operasjoner som utelates.

Kommandoen kontrollerer at verktøybaner er oppdaterte og at jobben ikke har feil. Hvis brukeren har endret modellen, er hovedhandlingen «Beregn og klargjør». Ulagret dokument tillates som eksplisitt øyeblikksbilde, merket «ulagret kilde»; det skal ikke tilskrives en lagret revisjon som ikke finnes.

Eksporten produserer en uforanderlig revisjon. Under behandling vises faktisk trinn: «Beregner», «Eksporterer» og «Åpner i OpenSpindle». Avbryt avbryter bare det aktuelle trinnet; teksten forklarer dersom eksporten allerede er ferdig.

### B. Åpne i OpenSpindle med konteksten intakt

OpenSpindle åpnes på riktig jobbkort. Navn og revisjon er de samme som i FreeCAD. Kortet viser en miniatyr av delen, antall operasjoner og verktøy, materialet og forventet varighet. Tidsestimat merkes med usikkerhet og utelatte manuelle verktøybytter.

Ved første import opprettes et oppsett. Senere overføringer foreslår «Oppdater denne jobben» og viser en endringsoversikt. De lager ikke automatisk enda en anonym kopi. En pågående kjøring beholder sitt opprinnelige øyeblikksbilde.

### C. Se og forstå det fysiske oppsettet

Midten av skjermen viser Z1-bordet med emne, del, verktøybaner, jigg og klemmer. Jobbens nullpunkt og maskinens målte nullpunkt har forskjellige symboler og en forklaring i klartekst. Ved avvik vises både verdier og en synlig forskyvning i 3D.

Brukeren kan velge «Vis oppspenning», «Vis neste verktøybytte» og «Vis første inngrep». Manglende holder- eller klemmegeometri vises som ukjent dekning, ikke som et problemfritt oppsett.

### D. Kontroller og start

Automatiske kontroller utføres i bakgrunnen. Operatøren får bare spørsmål om det systemet ikke kan observere: om riktig emne er montert, klemmer sitter som vist og det fysiske verktøyet stemmer. Bekreftelser knyttes til oppsettets revisjon.

En kompakt startflate oppsummerer maskin, revisjon, første verktøy, nullpunkt og gjenstående avvik. «Start fresing» er et eksplisitt valg. Overføring til maskinen og eventuell tilbakeavlesing skjer med synlige trinn. Dersom forholdene endrer seg før start, stoppes startforløpet og årsaken forklares.

### E. Følg arbeidet

Kjøreskjermen viser aktiv operasjon, neste operasjon, neste verktøybytte, estimert tid og kamera. Pause og stopp er faste, tydelig adskilte handlinger. Programvarens stoppstatus beskriver hva som faktisk ble bekreftet; den fysiske nødstoppfunksjonen erstattes ikke av skjermen.

Ved verktøybytte vises nummer, navn, diameter, type og eventuelt bilde. «Installer 3 mm endefres» er mer nyttig enn «T3». Et verktøynummer alene er ingen verifikasjon av verktøyets identitet.

### F. Ferdig og læring

Jobben er først ferdig når maskinens rapportering gir tilstrekkelig grunnlag. Resultatet får tidspunkt, faktisk varighet, brukt revisjon og eventuelle avbrudd. Brukeren kan registrere «godkjent», «må justeres» eller «forkastet» med et bilde eller en kort merknad.

«Lag en til» gjenbruker program og oppsett, men oppretter en ny kjøring og ber om nødvendig fysisk klargjøring. Erfaringer knyttes til material-, verktøy- og oppsettversjon; de endrer aldri feeds og speeds automatisk.

## 6. Skjermstruktur og visuell utforming

| Flate | Primærinnhold | Hovedhandling |
|---|---|---|
| FreeCAD: maskinpanel | Jobb, målmaskin, revisjon, eksportstatus | Klargjør på Z1 / Oppdater i OpenSpindle |
| OpenSpindle: Forbered | Operasjoner til venstre, 3D-oppsett i midten, relevante egenskaper til høyre | Kontroller oppsett |
| OpenSpindle: Kontroll | Problemer gruppert etter konsekvens, valgt problem i 3D og på tidslinjen | Rett valgt problem / Gå til start |
| OpenSpindle: Kjør | Aktiv operasjon, tidslinje, kamera og maskinstatus | Start, Pause, Fortsett eller Stopp etter tilstand |
| Historikk | Jobbkort med revisjon, resultat og erfaringer | Åpne oppsett / Lag en til |

Én tydelig hovedhandling per tilstand. Unngå parallelle knapper som «Send», «Upload», «Select» og «Run» uten forklaring. Detaljer som hash, G-kodelinjer og protokollspor ligger bak «Detaljer», men er tilgjengelige uten å forlate jobben.

Designet skal bruke rolige flater, god kontrast og tekst sammen med ikoner. Rødt reserveres for stopp og blokkerende problemer; grønt må angi en konkret bekreftet status. Tastaturnavigasjon, skalerbar tekst og 100–200 % skjermskalering inngår i normal kvalitetssikring. På berøringsskjerm skal vesentlige kontroller ha minst omtrent 44 × 44 logiske piksler. Farge alene skal aldri bære betydningen.

Eksempel på jobbkort: **Motorfeste · revisjon 7**. Undertekst: «Aluminium · 3 operasjoner · 2 verktøy · ca. 24 min + verktøybytte». Status: «Importert. Nullpunkt må kontrolleres». Hovedhandling: «Kontroller oppsett».

Eksempel på problem: **«Verktøyholder kan treffe klemme 2»**. Forklaring: «Under Profil, ved 04:12, er beregnet klaring −1,2 mm». Handlinger: «Vis bevegelsen», «Åpne operasjon i FreeCAD» og «Oppdater oppspenning». Dette forutsetter en implementert kollisjonskontroll; inntil da skal grensesnittet vise at denne kontrollen ikke er tilgjengelig.

## 7. Tilstander og feil skal være del av produktet

Import til OpenSpindle, opplasting til Z1, valg av fil og maskinkjøring er forskjellige tilstander. «Sendt» skal ikke brukes som samlebetegnelse.

| Tilstand | Betydning for brukeren | Tillatt neste handling |
|---|---|---|
| Klar lokalt | Eksportert revisjon finnes | Åpne eller overfør |
| Importert | OpenSpindle har akseptert jobben | Kontroller oppsett |
| Venter | Målmaskin er utilgjengelig eller opptatt | Avbryt venting eller fortsett å forberede |
| Overfører | Maskintransport er aktiv | Avbryt overføring dersom støttet |
| Verifisert overført | Avtalt kontroll av maskinfilen er fullført | Fullfør startkontroll |
| Start forespurt | Start er sendt, men kjøring ikke bekreftet | Avvent og undersøk; ikke gjenta automatisk |
| Kjører / verktøybytte / pauset | Rapportert maskintilstand | Bare handlinger tillatt i denne tilstanden |
| Ukjent utfall | Kontakten eller bekreftelsen mangler | Gjenopprett oversikt og avklar maskinstatus |
| Fullført / avbrutt / feilet | Kjøringen har et dokumentert utfall | Registrer resultat eller opprett ny kjøring |

Ved timeout etter opplasting: «Overføringen kunne ikke bekreftes. Filen kan finnes på maskinen». Ved frakobling under fresing: «Forbindelsen er brutt. Maskinen kan fortsatt kjøre». Ved endret kilde: «FreeCAD har nyere endringer enn revisjonen som er klar til kjøring».

Køen er først inn, først ut innen eksplisitt prioritet. Brukeren kan omprioritere ventende jobber. En ny revisjon kan erstatte en ventende revisjon etter et synlig valg, men aldri en pågående kjøring. Foreldreløse forespørsler etter krasj får «må avklares», ikke automatisk ny start eller skjult sletting.

## 8. Revisjoner og hva som gjør tidligere kontroll ugyldig

| Endring | Hva må gjentas |
|---|---|
| Modell, bane eller operasjonsrekkefølge | Eksport og relevant bane-/kollisjonskontroll |
| Verktøygeometri eller utstikk | Verktøymatching, klaring og relevant måling |
| Emne, jigg eller klemmeplassering | Oppsettkontroll, klaring og relevante nullpunktmålinger |
| Målmaskin eller firmware/postprosessor | Kompatibilitetskontroll og maskinbinding |
| Målt nullpunkt eller ankere | Oppsettets plassering og startkontroll |
| Navn eller beskrivende merknad | Ingen maskinrelatert kontroll, så lenge kjøreinnholdet er identisk |

Ingen automatisk overskriving av fysisk målte verdier med gamle CAD-verdier. CAD beskriver intensjonen; kontrolleren beskriver observerte maskinverdier. Uenighet krever en konkret forklaring og et valg av hvilken endring som skal utføres.

## 9. Teknisk produktgrense

FreeCAD eier modellen, CAM-operasjonene og postprosesseringen. Broen eier overlevering, kildereferanser, revisjoner og kvitteringer. OpenSpindle eier operatørens maskinoppsett, maskinforbindelsen og kjøretilstanden. Bare én kontroller skal eie maskinforbindelsen i en sesjon.

Første integrasjon kan eksportere en NC-fil og åpne den i OpenSpindle. Windows-koden på main håndterer filargumenter og videresender dem til en eksisterende instans. Dette bekrefter bare overlevering til appens importflyt, ikke at importen lykkes. Et fullverdig statuspanel trenger en eksplisitt importkvittering. [4]

Neste nivå er en versjonert, lokal integrasjon. Foretrukket retning er å bidra med en generell CAM-kildeadapter i OpenSpindle, inspirert av Fusion-integrasjonen. Dagens Fusion-løsning har en lokal tjeneste i Fusion som OpenSpindle spør om programmer og eksport; den er ikke et ferdig generisk HTTP-endepunkt som tar imot FreeCAD-filer. Protokollen må utformes eller generaliseres før den gjenbrukes. [5]

En fremtidig jobboverlevering bør inneholde:

- Jobb-ID, kilde-ID, oppsett-ID, revisjon og eksporttidspunkt.
- Eksakt NC-innhold, hash, enheter, postprosessorversjon og kompatibilitetsprofil.
- Operasjoner med stabile ID-er og kobling til NC-seksjoner der dette er tilgjengelig.
- Verktøynummer og verktøygeometri med tydelig kilde og versjon.
- Emne, koordinattransformasjoner, oppspenning og modell/miniatyr som valgfrie ressurser.
- Målmaskinbinding og kontrollrapport med «kontrollert», «ukjent» og «ikke støttet».

Dette er et foreslått format, ikke et eksisterende OpenSpindle-filformat. Tidlig versjon kan bruke dokumenterte `@OPENSPINDLE`-kommentarer for stock, work origin og fixture, med en separat manifestfil for kildereferanser. Hele FreeCAD-dokumentet skal ikke være påkrevd for import. Alle transformasjoner må definere enheter, akser og referanser eksplisitt. [5]

Lokale API-er må autentiseres, ha størrelsesgrenser og avvise uventede nettleserforespørsler. Pairing skal være enkelt, uten at brukeren kopierer tokens. Eksport/import får aldri implisitt rett til å starte fresing.

Hver callback og hendelse bindes til forespørsel, revisjon og maskinsesjon. Repetert import er idempotent. Maskinstart gjentas ikke automatisk ved ukjent utfall. Dette følger direkte av feilene funnet i vår eksisterende mottaker.

## 10. Kontrollnivåer som skal vises ærlig

**Nivå 1 – innhold:** Filen kan leses, enheter er entydige, kjent dialekt, identifiserbare verktøy og ingen ugyldige eksportresultater.

**Nivå 2 – oppsett:** Jobbens nullpunkt, stock, verktøy og målmaskin er konsistente. Nødvendige opplysninger er kjent eller eksplisitt markert som manglende.

**Nivå 3 – bevegelse:** Støttede bevegelser og maskinrutiner er simulert, arbeidsområde vurdert og relevante risikobevegelser funnet.

**Nivå 4 – geometri:** Kollision mot modellert oppspenning, holder og maskin er vurdert innenfor dokumenterte grenser. Skal ikke hevdes før en faktisk motor og tester finnes.

En fin animasjon oppfyller ikke automatisk nivå 3 eller 4. Ukjente kommandoer skal vises med konsekvensen «denne delen av programmet er ikke validert». En synlig kontrollrapport følger revisjonen.

## 11. Avgrensning og prioriteringer

Første versjon støtter tre-akset fresing, ett oppsett per jobb og eksplisitt start. FreeCADs tabs/dressups beholdes gjennom postprosessorens G-kode. Broen skal ikke legge til nye tabs eller omskrive skjærestrategier på egen hånd.

Senere: flere oppsett for vendte deler, et delt verktøybibliotek med konflikthåndtering, jiggmaler, bedre estimater og eventuelt fjerde akse. Fjerde akse krever egen støtte i post, simulering, transformasjoner og fysisk testing; en tegnet roterende del er ikke tilstrekkelig.

AI kan senere forklare problemer, foreslå relevante innstillinger og oppsummere endringer. Forslag til mating, hastighet eller G-kode må vises som endringer, valideres og aksepteres. AI skal ikke være en skjult komponent i den deterministiske startkontrollen.

## 12. Leveranseplan med beslutningsporter

| Trinn | Leveranse | Kriterium for å gå videre |
|---|---|---|
| 0. Pålitelig grunnlag | Rett callback-/tilstandsfeil, stabil kø og eksplisitte utfall; velg testet FreeCAD/post/firmware/Controller-kombinasjon | Feilsimuleringene gir korrekt resultat; gjentatt forespørsel gir ingen feil jobbvalg |
| 1. Enkel overlevering | «Klargjør på Z1», NC-eksport og åpning i OpenSpindle, tydelig importstatus eller ærlig «åpning forespurt» | En representativ FreeCAD-jobb kan importeres og inspiseres uten å lete i mapper |
| 2. Jobb med kontekst | Metadata, stabil kildekobling, revisjoner og oppdateringsoversikt | Oppdatering bevarer riktig oppsett og ugyldiggjør akkurat berørte kontroller |
| 3. Validert kjøreflate | Maskinbinding, probingflyt, overføring, verktøybytte, start/stopp og gjenoppkobling | Simulator og dokumentert fysisk testmatrise bestått på støttede kombinasjoner |
| 4. Gjenbruk og læring | Jiggmaler, historikk, gjenta jobb og flere oppsett | Brukerne gjenbruker riktig revisjon og oppdager fysisk endret oppsett |

OpenSpindle velges som full kjørebackend først etter trinn 3. Frem til da kan det evalueres som import- og forhåndsvisningsflate. Dersom brukeren vil kjøre via Community Controller, må den eksakte eksporterte kjørerevisjonen identifiseres tydelig; en kontroll av annen G-kode skal ikke gjenbrukes som godkjenning.

Det settes ingen kalenderdatoer før omfang, vedlikeholderdialog, Windows-distribusjon og maskintesting er avklart. Prioriteringene er en foreslått rekkefølge, ikke et estimat på antall utviklingsdager.

## 13. Verifikasjon og målbar brukeropplevelse

Foreslått første brukertest: 5–8 personer fordelt mellom CNC-nybegynnere og erfarne FreeCAD-brukere. De utfører en første eksport, endrer en lomme, håndterer et ukjent verktøy, får en frakobling og gjentar en ferdig jobb. Testlederen registrerer feil valg og behov for hjelp, ikke bare hvor mange klikk som brukes.

Målene under er foreløpige akseptansemål, ikke dokumenterte resultater:

| Mål | Første akseptansemål |
|---|---|
| Forstå forskjellen mellom import og maskinoverføring | Minst 90 % forklarer status riktig i brukertest |
| Åpne ferdig beregnet jobb i mottaker | Høyst to eksplisitte brukerhandlinger etter førstegangsoppsett, unntatt nødvendige importavklaringer |
| Respons på handling | Synlig respons innen 200 ms; langvarig arbeid har fremdrift eller konkret ventestatus |
| Endret revisjon | Alle tester hindrer at ny revisjon arver ugyldig kontrollstatus |
| Sen callback / omstart / duplikat | Ingen feil fullføring, feil jobbvalg eller automatisk start |
| Manglende simuleringstøtte | Alle ukjente bevegelseskommandoer gir synlig begrensning |
| Tilkoblingstap under jobb | Ingen falsk «fullført», ingen automatisk omstart |

Testkorpuset bør inkludere profil med tabs, pocket, boring, V-carve, flere verktøy, buer, inngang/utgang og store filer. Feiltilfeller inkluderer utdatert verktøybane, tom eksport, inch/mm, endret WCS, feil maskin, frakobling ved hvert overføringstrinn og kontrollert appkrasj. Fysisk testing går fra import uten maskinbevegelse til kontrollert tomkjøring og enkle kutt; resultater føres per firmware, postprosessor og appversjon.

## 14. Åpne beslutninger

1. Vil OpenSpindle vedlikeholde en generell FreeCAD/CAM-adapter, eller må vi vedlikeholde en separat utvidelse? Foretrekk et lite upstream-bidrag fremfor en varig full fork.
2. Hvilken Windows-pakke og FreeCAD-versjon blir første støttede kombinasjon? Main-kode må ikke forveksles med en utgitt installer.
3. Hvilke verktøymetadata leses direkte fra vår nåværende Makera-post, og hvilke trenger adapter? Dette må testes med ekte eksempeljobber.
4. Hvilken maskinidentitet og hvilke ferskhetsdata tilbyr Z1-protokollen på aktuelle firmwareversjoner?
5. Hvem eier kalibrerte ankere og målt nullpunkt når begge apper har lagrede prosjektverdier? Anbefaling: maskinmålinger beholdes i kontrolleren og sammenlignes med CAD-intensjonen.
6. Hvilken simuleringsdekning kan vi dokumentere, og hvor må vi vise «ikke kontrollert»?

## 15. Kilder

Alle kilder ble undersøkt 7. november 2026. Produktfunksjoner er beskrevet etter dokumentasjon, ikke verifisert ved praktisk bruk. Resten av dokumentet er våre egne designforslag.

1. [FreeCAD Makera Bridge](https://github.com/passeride/FreeCadMakeraBridge/tree/7a4b69a5151c2b18b530698657d1a5d0ce53312e).
2. [Controller: inbox-mottaker og tester](https://github.com/passeride/Carvera_Controller/tree/185ba615ae408c84986e83e16d0eb529ab79b978).
3. [OpenSpindle: funksjoner og fysisk valideringsstatus](https://github.com/openspindle/openspindle/blob/c2e055b389cca7fd85ac6948b0affd297f07bce3/README.md).
4. [OpenSpindle: filåpning og eksisterende appinstans](https://github.com/openspindle/openspindle/blob/c2e055b389cca7fd85ac6948b0affd297f07bce3/electron/main/index.ts).
5. [OpenSpindle: Fusion-kildeintegrasjon, metadata og postkompatibilitet](https://github.com/openspindle/openspindle/blob/c2e055b389cca7fd85ac6948b0affd297f07bce3/docs/fusion360.md).
6. [OpenSpindle: kjøretransaksjon og tilstander](https://github.com/openspindle/openspindle/blob/c2e055b389cca7fd85ac6948b0affd297f07bce3/docs/device-jobs.md) og [v0.3.0](https://github.com/openspindle/openspindle/releases/tag/v0.3.0).
7. [Bambu Studio: offisiell funksjonsbeskrivelse](https://github.com/bambulab/BambuStudio/blob/master/README.md).
8. [Prusa: sending og integrert Connect-fane](https://help.prusa3d.com/article/sending-g-codes-to-printer-via-network-prusa-connect-prusalink-octoprint_196761?product=prusa-connect).
9. [Prusa Connect: kø, opplasting og overvåkning](https://blog.prusa3d.com/prusa-connect-a-network-solution-for-remote-control-of-3d-printers_90364/).
10. [OctoPrint: filoperasjoner](https://docs.octoprint.org/en/main/api/files.html) og [jobboperasjoner](https://docs.octoprint.org/en/main/api/job.html).
11. [Autodesk: Simulation for manufacturing](https://help.autodesk.com/cloudhelp/ENU/Fusion-CAM/files/GUID76F8D8EF-2725-4203-944B-B9345936DDDB.htm).
12. [Autodesk: Check for issues during simulation](https://help.autodesk.com/view/fusion360/ENU/?contextId=MFG-SIMULATE-MACHINE-COLLISION-DETECTION-PREVIEW). En annen eldre/inkonsistent supportartikkel sa at maskinsimulering ikke finnes; vurderingen bygger på den detaljerte produktdokumentasjonen over.
13. [Makera Studio: programvareoversikt](https://www.makera.com/pages/software).
14. [Makera Z1: Quick Start](https://wiki.makera.com/en/Z1/QuickStart).
15. [Community Fusion Plugin](https://github.com/Carvera-Community/Carvera_Community_FusionPlugin).
16. [CNC-Proxy](https://github.com/einaros/CNC-Proxy).
