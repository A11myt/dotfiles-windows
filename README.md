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
wintheme --dry-run                    # nur anzeigen
```

Eingefärbt werden: **Windows** (Akzentpalette für Startmenü, Taskleiste, Fensterrahmen; Hell/Dunkel; Wallpaper),
**Windows Terminal** (Schema „Matugen“), **VS Code** (markierter Block, Kommentare bleiben),
**oh-my-posh** (aus `wintheme/templates/ohmyposh.json`) und **komorebi** (Fensterrahmen live über `komorebic`).
Was nicht installiert ist, lässt wintheme aus.

- **Rechtsklick auf ein Bild** → „Weitere Optionen anzeigen“ → „Als Hintergrund mit Farben (wintheme)“
- **Automatisch:** `wintheme --watch` läuft im Autostart und färbt neu ein, wenn du das Wallpaper in den Windows-Einstellungen wechselst.
- Einstellungen merkt sich wintheme in `%APPDATA%\wintheme\config.json`.

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

- Windows Terminal (tmux-Ersatz): [docs/keybindings-terminal.md](docs/keybindings-terminal.md)
- komorebi/whkd: direkt in [.config/whkd/whkdrc](.config/whkd/whkdrc)
- VS Code (Vim-Plugin): [docs/keybindings-vscode.md](docs/keybindings-vscode.md)
