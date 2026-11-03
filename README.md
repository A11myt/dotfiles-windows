# dotfiles-windows

Windows 11 · komorebi + whkd (Kacheln) · oh-my-posh · Windows Terminal · VS Code –
**Farben automatisch aus dem Wallpaper** mit `wintheme` (wie Matugen auf dem Linux-Laptop, gleiche Palette).

## Installieren (ohne Administratorrechte)

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

| Was | Wie | Ziel |
|---|---|---|
| komorebi, komorebi-bar, Apps | Hardlink | `%USERPROFILE%\komorebi*.json`, `applications.json` |
| whkd | Hardlink | `%USERPROFILE%\.config\whkdrc` |
| PowerShell-Profil | kleine Ladedatei (`. '<repo>\…\profile.ps1'`) – auch für OneDrive-Dokumente | Profile von Windows PowerShell **und** PowerShell 7 |
| VS Code Tastenkürzel | Hardlink | `%APPDATA%\Code\User\keybindings.json` |
| VS Code / Windows Terminal `settings.json` | **einmal kopiert** (wintheme schreibt dort die Farben hinein – das Repo bleibt sauber) | wie oben |
| VS-Code-Erweiterungen | `code --install-extension` | aus `.config/vscode/extensions.txt` |
| wintheme | eigene Python-Umgebung, Befehl `wintheme`, Rechtsklick-Menü, Autostart | `%LOCALAPPDATA%\wintheme` |

**Nur installierte Werkzeuge werden eingerichtet** – fehlt z. B. komorebi oder whkd, wird es übersprungen
(am Ende steht, was ausgelassen wurde; nach dem Nachinstallieren `install.ps1` einfach erneut ausführen).
Fehlt Python, wird es per `winget` für deinen Benutzer installiert. Danach wird einmal mit dem aktuellen Wallpaper eingefärbt.

## wintheme – Farben aus dem Wallpaper

```powershell
wintheme C:\Bilder\wallpaper.jpg     # als Wallpaper setzen und alles einfärben
wintheme --scheme vibrant             # tonal-spot, vibrant, expressive, fidelity, content, fruit-salad, rainbow, neutral, monochrome
wintheme --mode light                 # hell/dunkel
wintheme --sources                    # die 4 Ausgangsfarben des aktuellen Wallpapers
wintheme --color 2                    # Ausgangsfarbe 2 für dieses Bild
wintheme --titlebars on               # Akzentfarbe auch in Titelleisten
wintheme --look off                   # nur Farben, Aussehen (Schrift, Abstände, Rahmen) nicht anfassen
wintheme --dry-run                    # nur anzeigen
```

Eingefärbt werden: **Windows** (Akzentpalette für Startmenü, Taskleiste, Fensterrahmen; Hell/Dunkel; Wallpaper),
**Windows Terminal** (Schema „Matugen“), **VS Code** (markierter Block, Kommentare bleiben),
**oh-my-posh** (aus `wintheme/templates/ohmyposh.json`) und **komorebi** (Fensterrahmen live über `komorebic`).
Was nicht installiert ist, lässt wintheme aus.

- **Rechtsklick auf ein Bild** → „Weitere Optionen anzeigen“ → „Als Hintergrund mit Farben (wintheme)“
- **Automatisch:** `wintheme --watch` läuft im Autostart und färbt neu ein, wenn du das Wallpaper in den Windows-Einstellungen wechselst.
- Einstellungen merkt sich wintheme in `%APPDATA%\wintheme\config.json`.

### Aussehen wie auf dem Laptop

`wintheme` bringt außer den Farben auch das Aussehen mit (abschaltbar mit `--look off`):

- **Windows Terminal** wie Alacritty: Iosevka NF 10, Innenabstand 18/20, 90 % Deckkraft mit Acryl, Strich-Cursor, keine Bildlaufleiste, Tab-Leiste in Wallpaper-Farben
- **komorebi** wie Hyprland: Lücken 5 (außen) / 2 (zwischen Fenstern), runde Rahmen 2 px, weiche Animationen

### Leiste anpassen – `winbar`

`install.ps1` richtet komorebi so ein, dass es mit Leiste (und whkd, falls installiert) bei der Anmeldung startet, und startet es gleich.

Die komorebi-Leiste sieht aus wie auf dem Laptop (40 px, Arbeitsflächen mit Nummer + Icon, Fenstertitel in der Mitte, rechts Medien/CPU/RAM/Netz/Akku/Tray/Datum/Uhr). Änderungen wirken sofort:

```powershell
winbar                          # was ist wo
winbar reset                    # zurück zur Laptop-Vorlage (install.ps1 setzt sie beim ersten Mal selbst)
winbar add storage              # Widget einblenden (rechts) …
winbar add tray left            # … oder auf eine Seite: left | center | right
winbar remove cpu               # ausblenden
winbar move time center 1       # verschieben (Position ab 1)
winbar set height 36            # height · font "Iosevka NF" · size 12 · alpha 0–255 · round 10 · spacing 10 · groups on|off
winbar workspaces both          # icons | text | both
winbar taskbar hide             # Windows-Taskleiste automatisch ausblenden (show = zurück)
```

Widgets: workspaces, layout, window, media, cpu, memory, network, battery, storage, tray, date, time, keyboard, update.

### Rückgängig

```powershell
wintheme --undo        # letzten Schritt zurück (mehrmals = weiter zurück, bis 20)
wintheme --original    # wie vor der ersten Benutzung (selbst wieder mit --undo zurücknehmbar)
wintheme --history     # gespeicherte Stände
```

`install.ps1 -Uninstall` stellt vorher den Originalzustand wieder her (`-KeepColors` behält die Farben).

### Vorlagen

`wintheme/templates/*.json` dürfen Platzhalter wie Matugen enthalten (`{{colors.primary.default.hex}}`) oder die
kurzen Namen der früheren Farbdatei (`{{primary}}`, `{{surface_dark}}`, `{{accent_muted}}` …).
Die VS-Code-Vorlage kommt aus den Linux-Dotfiles: `wintheme/sync-templates.sh` (erwartet `../dotfiles` daneben).

## Fehlersuche

```powershell
powershell -ExecutionPolicy Bypass -File .\diagnose.ps1
```

Sammelt Werkzeuge, wintheme-Installation, PATH, Profile, Einstellungen, einen Probelauf sowie die Protokolle
(`%APPDATA%\wintheme\wintheme.log`, `%LOCALAPPDATA%\wintheme-logs\install.log`) in `logs\diagnose-<zeit>.log`
und lädt den Bericht hoch (commit + push; `-NoPush` nur lokal). Benutzer- und Rechnername werden geschwärzt.

## Tastenkürzel

- **komorebi/whkd – wie Hyprland (Win = SUPER):** [docs/keybindings-windows.md](docs/keybindings-windows.md)
- Windows Terminal (tmux-Ersatz): [docs/keybindings-terminal.md](docs/keybindings-terminal.md)
- VS Code (Vim-Plugin): [docs/keybindings-vscode.md](docs/keybindings-vscode.md)
