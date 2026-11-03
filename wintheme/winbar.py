#!/usr/bin/env python3
"""winbar – komorebi-Leiste anpassen (wie die Leisten-Einstellungen auf dem Laptop).

  winbar                         Übersicht: Widgets links/Mitte/rechts, Größe, Schrift
  winbar add <widget> [seite]    Widget einblenden (seite: left|center|right, Standard right)
  winbar remove <widget>         Widget ausblenden
  winbar move <widget> <seite> [pos]   Widget verschieben (pos ab 1, sonst ans Ende)
  winbar set <name> <wert>       height 40 · font "Iosevka NF" · size 12 · alpha 0–255 (Durchsicht)
                                 · round 10 (Ecken) · spacing 10 · groups on|off
  winbar workspaces <art>        icons | text | both (Nummer + Icon, wie Laptop)
  winbar reset                   Laptop-Vorlage aus dem Repo (Farben bleiben)
  winbar taskbar hide|show       Windows-Taskleiste automatisch ausblenden / wieder zeigen

Widgets: workspaces, layout, window, media, cpu, memory, network, battery, storage,
         tray, date, time, keyboard, update
Die Leiste lädt Änderungen sofort neu; Farben setzt weiterhin wintheme.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOME = Path(os.environ.get("USERPROFILE", Path.home()))
BAR = HOME / "komorebi.bar.json"
PRESET = HERE / "komorebi.bar.json"           # von install.ps1 neben winbar.py gelegt
SIDES = {"left": "left_widgets", "center": "center_widgets", "right": "right_widgets",
         "links": "left_widgets", "mitte": "center_widgets", "rechts": "right_widgets"}
SIDE_NAME = {"left_widgets": "links", "center_widgets": "Mitte", "right_widgets": "rechts"}

# Name → (Widget-Typ, Teil des Komorebi-Widgets oder None, Standard-Einstellungen)
WIDGETS = {
    "workspaces": ("Komorebi", "workspaces", {"enable": True, "hide_empty_workspaces": False, "display": "AllIconsAndText"}),
    "layout":     ("Komorebi", "layout", {"enable": True, "display": "Icon"}),
    "window":     ("Komorebi", "focused_container", {"enable": True, "show_icon": True, "display": "IconAndText"}),
    "media":      ("Media", None, {"enable": True}),
    "cpu":        ("Cpu", None, {"enable": True}),
    "memory":     ("Memory", None, {"enable": True}),
    "network":    ("Network", None, {"enable": True, "show_activity": False, "show_total_activity": False}),
    "battery":    ("Battery", None, {"enable": True}),
    "storage":    ("Storage", None, {"enable": True}),
    "tray":       ("Systray", None, {"enable": True}),
    "date":       ("Date", None, {"enable": True, "format": "DayDateMonthYear"}),
    "time":       ("Time", None, {"enable": True, "format": "TwentyFourHourWithoutSeconds"}),
    "keyboard":   ("Keyboard", None, {"enable": True}),
    "update":     ("Update", None, {"enable": True}),
}
ALIASES = {"ram": "memory", "systray": "tray", "uhr": "time", "datum": "date", "akku": "battery",
           "netz": "network", "fenster": "window", "titel": "window", "arbeitsflächen": "workspaces",
           "medien": "media", "speicher": "storage", "tastatur": "keyboard"}
WS_DISPLAY = {"icons": "AllIcons", "text": "Text", "both": "AllIconsAndText"}


def num(v: str) -> float | int:
    f = float(v)
    return int(f) if f.is_integer() else f


def die(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def load() -> dict:
    if not BAR.is_file():
        die(f"{BAR} fehlt – erst install.ps1 ausführen (oder: winbar reset)")
    d = json.loads(BAR.read_text(encoding="utf-8-sig"))
    for side in SIDE_NAME:                      # alter Name (bis komorebi 0.1.3x) → neuer
        for w in d.get(side, []):
            k = w.get("Komorebi", {})
            if "focused_window" in k and "focused_container" not in k:
                k["focused_container"] = k.pop("focused_window")
    return d


def save(d: dict) -> None:
    # in-place schreiben: komorebi-bar beobachtet die Datei und lädt sofort neu
    with open(BAR, "w", encoding="utf-8") as f:
        f.write(json.dumps(d, indent=2, ensure_ascii=False) + "\n")


def widget(name: str) -> tuple[str, str | None, dict]:
    name = ALIASES.get(name.lower(), name.lower())
    if name not in WIDGETS:
        die(f"unbekanntes Widget „{name}“ – möglich: {', '.join(WIDGETS)}")
    return name, *WIDGETS[name][:2], WIDGETS[name][2]


def find(d: dict, typ: str, part: str | None):
    """→ (Seite, Index) des Eintrags, der dieses Widget enthält (aktiv oder nicht)."""
    for side in SIDE_NAME:
        for i, w in enumerate(d.get(side, [])):
            if typ in w and (part is None or part in w[typ]):
                return side, i
    return None, None


def is_on(d: dict, typ: str, part: str | None) -> bool:
    side, i = find(d, typ, part)
    if side is None:
        return False
    conf = d[side][i][typ]
    return bool((conf[part] if part else conf).get("enable"))


def detach(d: dict, typ: str, part: str | None) -> dict | None:
    """Widget aus seiner Seite lösen und dessen Einstellungen zurückgeben."""
    side, i = find(d, typ, part)
    if side is None:
        return None
    entry = d[side][i]
    if part is None:
        d[side].pop(i)
        return entry[typ]
    conf = entry[typ].pop(part)
    if not any(k in entry[typ] for k in ("workspaces", "layout", "focused_container", "focused_window",
                                         "locked_container", "configuration_switcher", "workspace_layer")):
        d[side].pop(i)
    return conf


def attach(d: dict, side: str, typ: str, part: str | None, conf: dict, pos: int | None) -> None:
    lst = d.setdefault(side, [])
    entry = {typ: {part: conf}} if part else {typ: conf}
    lst.insert(len(lst) if pos is None else max(0, min(pos - 1, len(lst))), entry)


def show(d: dict) -> None:
    rev = {(t, p): n for n, (t, p, _) in WIDGETS.items()}
    for side, label in SIDE_NAME.items():
        names = []
        for w in d.get(side, []):
            for typ, conf in w.items():
                if typ == "Komorebi":
                    names += [rev.get(("Komorebi", k), k) for k, v in conf.items()
                              if isinstance(v, dict) and v.get("enable")]
                elif conf.get("enable"):
                    names.append(rev.get((typ, None), typ))
        print(f"  {label:7} {', '.join(names) or '–'}")
    g = d.get("grouping") or {}
    print(f"  Höhe {d.get('height', 50)} · Schrift {d.get('font_family', 'Standard')} {d.get('font_size', '')}"
          f" · Durchsicht {d.get('transparency_alpha', 200)}/255 · Gruppen {'an' if g.get('kind', 'None') != 'None' else 'aus'}")
    unused = [n for n, (t, p, _) in WIDGETS.items() if not is_on(d, t, p)]
    if unused:
        print(f"  verfügbar: {', '.join(unused)}")


def taskbar(hide: bool) -> None:
    if sys.platform != "win32":
        die("nur unter Windows")
    import subprocess
    import winreg
    key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StuckRects3"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_READ | winreg.KEY_WRITE) as k:
        blob = bytearray(winreg.QueryValueEx(k, "Settings")[0])
        blob[8] = (blob[8] | 0x01) if hide else (blob[8] & ~0x01)    # Bit 0 = automatisch ausblenden
        winreg.SetValueEx(k, "Settings", 0, winreg.REG_BINARY, bytes(blob))
    subprocess.run(["taskkill", "/f", "/im", "explorer.exe"], capture_output=True)
    subprocess.Popen(["explorer.exe"])
    print("Windows-Taskleiste " + ("blendet sich jetzt automatisch aus" if hide else "wird wieder angezeigt"))


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("show", "list"):
        show(load())
        return 0
    cmd, args = argv[0], argv[1:]
    if cmd in ("-h", "--help", "help"):
        print(__doc__.strip())
        return 0
    if cmd == "taskbar" and args and args[0] in ("hide", "show"):
        taskbar(args[0] == "hide")
        return 0
    if cmd == "reset":
        if not PRESET.is_file():
            die(f"Vorlage {PRESET} fehlt – install.ps1 erneut ausführen")
        preset = json.loads(PRESET.read_text(encoding="utf-8-sig"))
        if BAR.is_file():
            preset["theme"] = load().get("theme", preset.get("theme"))   # Wallpaper-Farben behalten
        save(preset)
        print("Leiste auf Laptop-Vorlage gesetzt")
        show(preset)
        return 0

    d = load()
    if cmd in ("add", "remove", "move"):
        if not args:
            die(f"winbar {cmd} <widget> …")
        name, typ, part, default = widget(args[0])
        old_side, old_i = find(d, typ, part)
        if cmd == "add" and len(args) == 1 and old_side:     # schon da → an seinem Platz einblenden
            holder = d[old_side][old_i][typ]
            if part:
                holder[part] = {**default, **holder[part], "enable": True}
            else:
                d[old_side][old_i][typ] = {**default, **holder, "enable": True}
            save(d)
            print(f"„{name}“ eingeblendet ({SIDE_NAME[old_side]})")
            return 0
        conf = detach(d, typ, part)
        if cmd == "remove":
            if conf is None:
                die(f"„{name}“ ist nicht in der Leiste")
            conf["enable"] = False
            attach(d, old_side, typ, part, conf, None)      # Einstellungen behalten, nur ausblenden
            print(f"„{name}“ ausgeblendet")
        else:
            side_arg = args[1] if len(args) > 1 else ("right" if cmd == "add" else None)
            if side_arg is None:
                die("winbar move <widget> <left|center|right> [pos]")
            side = SIDES.get(side_arg.lower()) or die(f"Seite „{side_arg}“? left|center|right")
            pos = int(args[2]) if len(args) > 2 else None
            conf = {**default, **(conf or {}), "enable": True}
            attach(d, side, typ, part, conf, pos)
            print(f"„{name}“ → {SIDE_NAME[side]}" + (f", Position {pos}" if pos else ""))
    elif cmd == "set" and len(args) == 2:
        k, v = args
        try:
            if k == "height":
                d["height"] = num(v)
            elif k == "font":
                d["font_family"] = v
            elif k == "size":
                d["font_size"] = num(v)
            elif k == "alpha":
                d["transparency_alpha"] = max(0, min(255, int(v)))
            elif k == "spacing":
                d["widget_spacing"] = num(v)
            elif k == "round":
                d.setdefault("grouping", {"kind": "Alignment", "style": "Default"})["rounding"] = num(v)
            elif k == "groups":
                d["grouping"] = ({"kind": "Alignment", "style": "Default", "rounding": 10, "transparency_alpha": 220}
                                 if v == "on" else {"kind": "None"})
            else:
                die("set: height | font | size | alpha | spacing | round | groups")
        except ValueError:
            die(f"„{v}“ ist keine gültige Zahl")
        print(f"{k} = {v}")
    elif cmd == "workspaces" and args and args[0] in WS_DISPLAY:
        side, i = find(d, "Komorebi", "workspaces")
        if side is None:
            die("Arbeitsflächen sind nicht in der Leiste – erst: winbar add workspaces left")
        d[side][i]["Komorebi"]["workspaces"]["display"] = WS_DISPLAY[args[0]]
        print(f"Arbeitsflächen: {args[0]}")
    else:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    save(d)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
