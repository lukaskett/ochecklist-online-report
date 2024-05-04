# O Checklist online report
Získej online html report se změnami ze startu orientačního závodu pomocí mobilní aplikace [O Checklist](https://play.google.com/store/apps/details?id=se.tg3.startlist) od [Anderse Löfgrena](<al@stigning.se>) a nahrávání na server přes FTP.

## Požadavky
- Přístup na server přes FTP
- Nainstalovaný [Python](https://www.python.org/)
- Nainstalovaný [Node.js](https://nodejs.org/en) (pro `live-server`) či https://pypi.org/project/reloadserver/
- Nainstalované potřebné Python balíčky (ftplib, yaml, ...)

## Potřebné kroky:
1. Stáhni si repozitář
2. Přejmenuj `example-config.py` na `config.py` a nastav si vlastní hodnoty pro ftp připojení
3. Spusť si webový server v kořenovém adresáři `ochecklist-online-report`, např. `live-server` nebo [reload-server](https://pypi.org/project/reloadserver/), který zajistí automatický reload reportu
4. Zajisti pravidelné spouštění skriptu `process_ochecklist_report.py`. Ve Windows jde využít např. `Plánovač úloh`

## V aplikaci
1. Nastavit připojení k serveru přes FTP
2. Nastavit jméno souboru a adresář (musí existovat)
3. Nastavit pravidelný automatický export na server, případně jde posílat ručně na kliknutí.

### Zpětná vazba
Dej mi vědět jak to šlo.

# EN:
 Get online html report with changes from the start of orienteering event for manual updates in the db using mobile app [O Checklist](https://play.google.com/store/apps/details?id=se.tg3.startlist) by [Anders Löfgren](<al@stigning.se>) and server upload via FTP. 

## Requirements
- Credential to the connection to the server
- Installed [Python](https://www.python.org/)
- Installed [Node.js](https://nodejs.org/en) (for `live-server`) or https://pypi.org/project/reloadserver/

## Steps:
1. Clone repository
2. Rename `example-config.py` to `config.py` and setup your credentials for ftp connection
3. Start webserver e.g. `live-server` or [reload-server](https://pypi.org/project/reloadserver/) in root folder `ochecklist-online-report`
4. Schedule regular `process_ochecklist_report.py` script execution, in Windows use e.g. `Task Scheduler`

## Mobile app setup
1. Setup FTP connection to the server
2. Set name of exported file and subfolder on the server (must exist)
3. Set regular automatic upload to your server or you can upload it by button press


### Feedback
Let me know if it helped.
