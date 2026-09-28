# howcom-radar-feed

Daily data for the HowCom office screen (Bauer DOOH, 1080×1920).

- `today.json`: this week's biggest Stockholm events and a 6-day forecast. The screen reads it from
  https://jonathanavigdor.github.io/howcom-radar-feed/today.json
- `events.json`: events added by hand (football, fixed dates, team events). Edit this file to add more.
- `.github/workflows/daily.yml`: runs every morning, fetches Ticketmaster and Open-Meteo, rebuilds `today.json`.
- The Ticketmaster key is stored as the repository secret `TM_KEY`, never in the code.
