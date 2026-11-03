# Ontech Control för Home Assistant

En fristående custom integration för konton på https://app.ontechcontrol.com.
Första versionen innehåller reläbrytare, interna/externa temperaturgivare och binära ingångar A/B. Enheter upptäcks automatiskt även när ny status anländer efter starten.

**Status:** experimentell. Protokollet har kartlagts från Ontechs publika webbklient och testas med en simulerad server. Verklig inloggning och fysisk styrning är ännu inte verifierade. Se [BUGS.md](BUGS.md).

## Installation

1. Kopiera mappen `custom_components/ontech` till `<config>/custom_components/ontech` på din Home Assistant-installation.
2. Starta om Home Assistant.
3. Öppna **Inställningar → Enheter och tjänster → Lägg till integration → Ontech Control**.
4. Ange samma e-postadress och lösenord som i Ontech Control.

Pythonbibliotek utöver dem som medföljer Home Assistant behövs inte. Använd en aktuell Home Assistant Core-version. Verifierad med 26 automatiska tester mot Home Assistant Core 2026.10.4 på Python 3.14.4; Ruff-kontrollen passerar. Testerna använder en lokal simulerad Ontech-server, inte ett riktigt konto.

Inloggningsuppgifterna sparas i Home Assistants vanliga config entry-lagring. Inga uppgifter ska läggas i detta repository. Ingen konfiguration i `configuration.yaml` behövs.

## Beteende

- Separat cookie-session per konto; CSRF-inloggning och krypterad WebSocket till adressen på kontosidan.
- Pushuppdateringar med anslutningskontroll varje minut och återanslutning vid avbrott. Ingen aktiv SMS-pollning av hårdvaran.
- Reläet visar rapporterat tillstånd, inte ett antaget tillstånd efter ett kommando.
- Enheter markeras som otillgängliga vid frånkoppling eller när senaste status/temperatur är mer än 30 minuter gammal, enligt webbklientens gräns.
- `nc`, `na`, tomma och ogiltiga temperaturer blir okända värden, aldrig 0 °C.
- Reläer aktiveras för identifierade modeller 9010, 9015, 9025, 9035, 9040, 9060 och 9065. Detta är en protokollbaserad lista, inte en lista över fysiskt testade modeller. 9012 och huvudenheter i garageläge får ingen reläbrytare.
- Råa ingångar exponeras utan antaganden om de representerar öppna dörrar, rörelse eller andra larm.

För att ta bort integrationen: ta bort kontoposten under Enheter och tjänster. För full avinstallation tar du därefter bort `custom_components/ontech` och startar om.

## Verifiera på din installation

Kontrollera först att enhetsnamn och temperaturer stämmer med Ontech-appen. Prova sedan ett relä på en last där till/frånslag är lämpligt och kontrollera att det rapporterade tillståndet uppdateras. Kontrollera även återanslutning efter omstart. Rapportera modell, Home Assistant-version och feltext vid problem; dela inte lösenord, cookies, ICCID eller WebSocket-URL:er som kan innehålla sessionstoken.

## Utveckling

```sh
uv venv .venv
uv pip install --python .venv/bin/python homeassistant pytest pytest-asyncio ruff
.venv/bin/python -m pytest
.venv/bin/ruff check .
```

## Protokollunderlag

Integrationen använder samma meddelanden som den [officiella webbklienten](https://app.ontechcontrol.com/js/all.js): `get_account_info`, `get_names`, `get_status`, `status`, `ping` och `sms`. Ett reläkommando är exempelvis `1*1#` (på, enhet 1) eller `0*1#` (av). `units` innehåller parallella arrayer med nollbaserade index, medan styrkommandon använder enhetsnummer 1–8. Ingen klientkod från Ontech distribueras här.

Home Assistants [config flows](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/) och [DataUpdateCoordinator](https://developers.home-assistant.io/docs/integration_fetching_data/) används för konfigurering och entitetsuppdateringar. Integrationen är inte en officiell Ontech-produkt och det privata webbprotokollet kan ändras.
