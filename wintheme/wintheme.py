#!/usr/bin/env python3
"""wintheme – Matugen für Windows 11: Farben aus dem Wallpaper für Windows, Windows Terminal, VS Code,
oh-my-posh und komorebi (Teil von dotfiles-windows).

  wintheme [bild]               Bild als Wallpaper setzen und alles einfärben
                                (ohne Bild: aktuelles Windows-Wallpaper nur einfärben)
  wintheme --mode light|dark    Hell/Dunkel (wird gemerkt)
  wintheme --scheme NAME        tonal-spot, vibrant, expressive, fidelity, content,
                                fruit-salad, rainbow, neutral, monochrome (wird gemerkt)
  wintheme --color 1-4|auto     Ausgangsfarbe für dieses Bild (wird pro Bild gemerkt)
  wintheme --sources [bild]     die 4 Ausgangsfarben eines Bildes anzeigen
  wintheme --watch              im Hintergrund: bei jedem Wallpaper-Wechsel neu einfärben
  wintheme --dry-run            nur anzeigen, nichts ändern
  wintheme --undo               letzten Schritt rückgängig (mehrmals = weiter zurück, bis 20)
  wintheme --original           Zustand vor der allerersten Benutzung wiederherstellen
  wintheme --history            gespeicherte Stände anzeigen
  wintheme --only windows,terminal,vscode,ohmyposh,komorebi   nur Teile anwenden

Farbberechnung wie Matugen (Material You, Spezifikation 2021, Quantisierung auf 112 px):
gleiches Bild + gleiche Einstellungen → gleiche Farben wie auf dem Linux-Laptop.
Einstellungen: %APPDATA%\\wintheme\\config.json
"""
import argparse
import base64
import json
import os
import re
import sys
import time
from pathlib import Path

from PIL import Image
from materialyoucolor.dynamiccolor.dynamic_color import DynamicColor
from materialyoucolor.dynamiccolor.material_dynamic_colors import MaterialDynamicColors
from materialyoucolor.hct import Hct
from materialyoucolor.quantize import QuantizeCelebi
from materialyoucolor.score.score import Score

IS_WIN = sys.platform == "win32"
HERE = Path(__file__).resolve().parent
APPDATA = Path(os.environ.get("APPDATA", Path.home() / ".config"))
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share"))
CONFIG = APPDATA / "wintheme" / "config.json"
HOME = Path(os.environ.get("USERPROFILE", Path.home()))
OHMYPOSH = HOME / ".config/ohmyposh/theme.omp.json"          # vom PowerShell-Profil geladen
KOMOREBI_LAST = APPDATA / "wintheme" / "komorebi.json"     # zuletzt gesetzte Rahmenfarben (für Rückgängig)
PARTS = "windows,terminal,vscode,ohmyposh,komorebi"
HISTORY = APPDATA / "wintheme" / "history"          # Stände vor jedem Einfärben (max. KEEP)
ORIGINAL = APPDATA / "wintheme" / "original.json"   # Stand vor der allerersten Benutzung (nie überschrieben)
KEEP = 20
LOGFILE = APPDATA / "wintheme" / "wintheme.log"       # für diagnose.ps1 (wird bei 200 KB gekürzt)
DEFAULTS = {"mode": "dark", "scheme": "tonal-spot", "contrast": 0.0, "pick": {}, "titlebars": False}

SCHEMES = {
    "tonal-spot": "scheme_tonal_spot.SchemeTonalSpot", "vibrant": "scheme_vibrant.SchemeVibrant",
    "expressive": "scheme_expressive.SchemeExpressive", "fidelity": "scheme_fidelity.SchemeFidelity",
    "content": "scheme_content.SchemeContent", "fruit-salad": "scheme_fruit_salad.SchemeFruitSalad",
    "rainbow": "scheme_rainbow.SchemeRainbow", "neutral": "scheme_neutral.SchemeNeutral",
    "monochrome": "scheme_monochrome.SchemeMonochrome",
}
# Windows-Akzentpalette: 8 Stufen (hell3 … Akzent … dunkel3, letzte unbenutzt) als Tonwerte
ACCENT_TONES = [90, 77, 62, 50, 42, 28, 14, 60]


# ── Protokoll ────────────────────────────────────────────────────────────────
class Tee:
    """Ausgaben zusätzlich ins Protokoll schreiben (auch unter pythonw ohne Konsole)."""
    def __init__(self, stream):
        self.stream = stream
    def write(self, text):
        log_raw(text)
        if self.stream:
            try:
                self.stream.write(text)
            except Exception:
                pass
    def flush(self):
        if self.stream:
            try:
                self.stream.flush()
            except Exception:
                pass


def log_raw(text: str) -> None:
    try:
        LOGFILE.parent.mkdir(parents=True, exist_ok=True)
        if LOGFILE.exists() and LOGFILE.stat().st_size > 200_000:
            LOGFILE.write_text(LOGFILE.read_text(encoding="utf-8", errors="replace")[-100_000:], encoding="utf-8")
        with LOGFILE.open("a", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass


# ── Einstellungen ────────────────────────────────────────────────────────────
def load_config() -> dict:
    try:
        return {**DEFAULTS, **json.loads(CONFIG.read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def save_config(cfg: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Farben ───────────────────────────────────────────────────────────────────
def hexc(argb: int) -> str:
    return "#%06x" % (argb & 0xFFFFFF)


def source_colors(image: Path) -> list[int]:
    img = Image.open(image).convert("RGBA").resize((112, 112), Image.Resampling.BILINEAR)
    pixels = list(img.get_flattened_data()) if hasattr(img, "get_flattened_data") else list(img.getdata())
    return Score.score(QuantizeCelebi(pixels, 128))[:4]


def scheme_class(name: str):
    mod, cls = SCHEMES[name].split(".")
    module = __import__(f"materialyoucolor.scheme.{mod}", fromlist=[cls])
    return getattr(module, cls)


def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def palette(image: Path, cfg: dict) -> dict:
    sources = source_colors(image)
    pick = cfg["pick"].get(image.name)
    src = sources[min(int(pick), len(sources) - 1)] if isinstance(pick, int) else sources[0]
    dark = cfg["mode"] != "light"
    s = scheme_class(cfg["scheme"])(Hct.from_int(src), dark, float(cfg["contrast"]), spec_version="2021")
    colors = {}
    for n in dir(MaterialDynamicColors):
        dc = getattr(MaterialDynamicColors, n)
        if n.startswith("_") or not isinstance(dc, DynamicColor):
            continue
        try:
            colors[snake(n)] = hexc(dc.get_argb(s))
        except Exception:          # Rollen, die es nur in der 2025-Spezifikation gibt
            pass
    return {"colors": colors, "dark": dark, "sources": [hexc(c) for c in sources], "source": hexc(src),
            "accent": [hexc(s.primary_palette.tone(t)) for t in ACCENT_TONES[:7]] + [hexc(s.tertiary_palette.tone(60))]}


# ── Windows (Registry) ───────────────────────────────────────────────────────
def rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def abgr(h: str, a: int = 0xFF) -> int:
    r, g, b = rgb(h)
    return (a << 24) | (b << 16) | (g << 8) | r


def current_wallpaper() -> Path | None:
    if not IS_WIN:
        return None
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as k:
        p = winreg.QueryValueEx(k, "WallPaper")[0]
    if p and Path(p).is_file():
        return Path(p)
    t = APPDATA / "Microsoft/Windows/Themes/TranscodedWallpaper"   # z. B. bei Diashow/Spotlight
    return t if t.is_file() else None


# Registry-Werte, die wintheme ändert (für Sicherung und Rückgängig)
ACCENT = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent"
DWM = r"Software\Microsoft\Windows\DWM"
THEMES = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
DESKTOP = r"Control Panel\Desktop"
REG_VALUES = [(ACCENT, "AccentPalette"), (ACCENT, "AccentColorMenu"), (ACCENT, "StartColorMenu"),
              (DWM, "AccentColor"), (DWM, "ColorizationColor"), (DWM, "ColorizationAfterglow"), (DWM, "ColorPrevalence"),
              (THEMES, "AppsUseLightTheme"), (THEMES, "SystemUsesLightTheme"), (DESKTOP, "AutoColorization")]


def reg_get(path: str, name: str):
    """→ (Wert, Typ) oder None, wenn es den Wert nicht gibt."""
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as k:
            return winreg.QueryValueEx(k, name)
    except OSError:
        return None


def reg_set(path: str, name: str, kind: int, value) -> None:
    import winreg
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, name, 0, kind, value)


def reg_del(path: str, name: str) -> None:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, name)
    except OSError:
        pass


def set_wallpaper(image: Path) -> None:
    import ctypes
    ctypes.windll.user32.SystemParametersInfoW(20, 0, str(image), 3)   # SPI_SETDESKWALLPAPER, speichern + melden


def broadcast() -> None:
    """Allen Fenstern melden, dass sich Farben geändert haben (Taskleiste, Startmenü, Apps live)."""
    import ctypes
    res = ctypes.c_ulong()
    for area in ("ImmersiveColorSet", "WindowsThemeElement"):
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, area, 0x0002, 3000, ctypes.byref(res))


def apply_windows(pal: dict, image: Path | None, set_wall: bool, titlebars: bool, dry: bool) -> str:
    acc = pal["accent"]
    if dry or not IS_WIN:
        return f"Windows: Akzent {acc[3]}, {'dunkel' if pal['dark'] else 'hell'}" + (" (nur Vorschau)" if dry else " (nicht Windows – übersprungen)")
    import winreg
    if set_wall and image:
        set_wallpaper(image)
    r, g, b = rgb(acc[3])
    colorization = (0xC4 << 24) | (r << 16) | (g << 8) | b
    light = 0 if pal["dark"] else 1
    reg_set(ACCENT, "AccentPalette", winreg.REG_BINARY, b"".join(bytes([*rgb(c), 0]) for c in acc))
    reg_set(ACCENT, "AccentColorMenu", winreg.REG_DWORD, abgr(acc[3]))
    reg_set(ACCENT, "StartColorMenu", winreg.REG_DWORD, abgr(acc[5]))
    reg_set(DWM, "AccentColor", winreg.REG_DWORD, abgr(acc[3]))
    reg_set(DWM, "ColorizationColor", winreg.REG_DWORD, colorization)
    reg_set(DWM, "ColorizationAfterglow", winreg.REG_DWORD, colorization)
    reg_set(DWM, "ColorPrevalence", winreg.REG_DWORD, 1 if titlebars else 0)
    reg_set(THEMES, "AppsUseLightTheme", winreg.REG_DWORD, light)
    reg_set(THEMES, "SystemUsesLightTheme", winreg.REG_DWORD, light)
    reg_set(DESKTOP, "AutoColorization", winreg.REG_DWORD, 0)      # Windows soll nicht selbst wählen
    broadcast()
    return f"Windows: Akzent {acc[3]}, {'dunkel' if pal['dark'] else 'hell'}"


def write_file(f: Path, text: str) -> None:
    """Atomar über eine neue Datei ersetzen – trennt dabei einen Hardlink (die Repo-Datei bleibt unverändert)."""
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".wintheme-tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, f)


# ── JSON mit Kommentaren (Windows Terminal, VS Code) ─────────────────────────
def strip_jsonc(text: str) -> str:
    """Entfernt // und /* */ außerhalb von Strings sowie Kommas vor } oder ]."""
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1]); i += 2; continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True; out.append(c)
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
            continue
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        else:
            out.append(c)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


# ── Windows Terminal ─────────────────────────────────────────────────────────
def terminal_settings() -> list[Path]:
    pk = LOCALAPPDATA / "Packages"
    cands = [pk / "Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState/settings.json",
             pk / "Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe/LocalState/settings.json",
             LOCALAPPDATA / "Microsoft/Windows Terminal/settings.json"]
    return [p for p in cands if p.is_file()]


def terminal_scheme(c: dict) -> dict:
    # wie die Alacritty-Vorlage auf dem Laptop
    return {
        "name": "Matugen",
        "background": c["background"], "foreground": c["on_surface"],
        "cursorColor": c["on_surface_variant"], "selectionBackground": c["primary"],
        "black": "#181818", "red": c["error"], "green": c["primary"], "yellow": c["inverse_primary"],
        "blue": c["primary"], "purple": c["tertiary"], "cyan": c["secondary"], "white": "#BAC2DE",
        "brightBlack": "#585B70", "brightRed": "#F38BA8", "brightGreen": "#A6E3A1", "brightYellow": "#F9E2AF",
        "brightBlue": "#89B4FA", "brightPurple": "#F5C2E7", "brightCyan": "#94E2D5", "brightWhite": "#A6ADC8",
    }


def apply_terminal(pal: dict, dry: bool) -> str:
    files = terminal_settings()
    if not files:
        return None
    scheme = terminal_scheme(pal["colors"])
    for f in files:
        raw = f.read_text(encoding="utf-8-sig")
        data = json.loads(strip_jsonc(raw))
        data["schemes"] = [s for s in data.get("schemes", []) if s.get("name") != "Matugen"] + [scheme]
        data.setdefault("profiles", {})
        if isinstance(data["profiles"], list):           # sehr alte Form
            data["profiles"] = {"list": data["profiles"]}
        data["profiles"].setdefault("defaults", {})["colorScheme"] = "Matugen"
        if dry:
            continue
        backup = f.with_name(f.name + ".wintheme-backup")
        if not backup.exists():
            backup.write_text(raw, encoding="utf-8")
        write_file(f, json.dumps(data, indent=4, ensure_ascii=False))   # Terminal lädt Änderungen sofort
    return f"Windows Terminal: Schema „Matugen“ ({len(files)} Datei{'en' if len(files) > 1 else ''})" + (" (nur Vorschau)" if dry else "")


# ── VS Code ──────────────────────────────────────────────────────────────────
BEGIN = "  // >>> wintheme (generiert – wird beim nächsten Einfärben ersetzt)"
END = "  // <<< wintheme"


def legacy(c: dict) -> dict:
    """Farbnamen der früheren Handdatei colors/matugen.json → Material-Rollen (für alte Vorlagen)."""
    return {
        "background": c["background"], "foreground": c["on_surface"], "cursor": c["on_surface_variant"],
        "primary": c["primary"], "secondary": c["secondary"], "tertiary": c["tertiary"],
        "surface": c["surface_container_high"], "surface_dark": c["surface_container_lowest"],
        "error": c["error"], "on_primary": c["on_primary"], "on_surface": c["on_surface"],
        "accent_muted": c["outline"],
    }


def render(template: str, colors: dict) -> str:
    """{{colors.<rolle>.default.hex}} (wie Matugen) und {{<name>}} (alte Vorlagen) ersetzen."""
    old = legacy(colors)
    text = re.sub(r"\{\{\s*colors\.([a-z_]+)\.default\.hex\s*\}\}", lambda m: colors.get(m.group(1), m.group(0)), template)
    return re.sub(r"\{\{\s*([a-z_]+)\s*\}\}", lambda m: old.get(m.group(1), m.group(0)), text)


def apply_vscode(pal: dict, dry: bool) -> str:
    files = vscode_settings()
    if not files:
        return None
    colors = json.loads(render((HERE / "templates/vscode-colors.json").read_text(encoding="utf-8"), pal["colors"]))
    for f in files:
        text = f.read_text(encoding="utf-8-sig")
        theme = re.search(r'"workbench\.colorTheme"\s*:\s*"([^"]+)"', text)
        value = {f"[{theme.group(1)}]": colors} if theme else colors
        body = json.dumps(value, indent=2).replace("\n", "\n  ")
        block = f'{BEGIN}\n  "workbench.colorCustomizations": {body},\n{END}'
        pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
        text = pattern.sub(lambda _: block, text) if pattern.search(text) else text.replace("{", "{\n" + block, 1)
        if not dry:
            write_file(f, text)
    return f"VS Code: Farben gesetzt ({len(files)}×)" + (" (nur Vorschau)" if dry else "")


# ── oh-my-posh ───────────────────────────────────────────────────────────────
def apply_ohmyposh(pal: dict, dry: bool) -> str:
    import shutil
    tpl = HERE / "templates/ohmyposh.json"
    if not tpl.is_file() or not shutil.which("oh-my-posh"):
        return None
    if not dry:
        write_file(OHMYPOSH, render(tpl.read_text(encoding="utf-8"), pal["colors"]))
    return "oh-my-posh: Theme erzeugt (neue PowerShell-Fenster)" + (" (nur Vorschau)" if dry else "")


# ── komorebi (Fensterrahmen, live) ───────────────────────────────────────────
def komorebic(*args: str) -> bool:
    import shutil
    import subprocess
    exe = shutil.which("komorebic")
    if not exe:
        return False
    flags = 0x08000000 if IS_WIN else 0                    # CREATE_NO_WINDOW: kein aufblitzendes Fenster
    return subprocess.run([exe, *args], capture_output=True, creationflags=flags).returncode == 0


def set_borders(kinds: dict) -> bool:
    ok = True
    for kind, color in kinds.items():
        r, g, b = rgb(color)
        ok &= komorebic("border-colour", "--window-kind", kind, str(r), str(g), str(b))
    return ok


def apply_komorebi(pal: dict, dry: bool) -> str:
    c = pal["colors"]
    kinds = {"single": c["primary"], "stack": c["secondary"], "monocle": c["tertiary"], "unfocused": c["outline_variant"]}
    import shutil
    if not shutil.which("komorebic"):
        return None
    if dry:
        return f"komorebi: Rahmen {c['primary']} (nur Vorschau)"
    if not set_borders(kinds):
        return "komorebi: komorebic meldet einen Fehler (läuft komorebi?)"
    KOMOREBI_LAST.parent.mkdir(parents=True, exist_ok=True)
    KOMOREBI_LAST.write_text(json.dumps(kinds), encoding="utf-8")
    return f"komorebi: Rahmen {c['primary']}"


# ── Sicherung / Rückgängig ───────────────────────────────────────────────────
def vscode_settings() -> list[Path]:
    return [f for f in (APPDATA / d / "User/settings.json" for d in ("Code", "Code - Insiders", "VSCodium")) if f.is_file()]


def snapshot(label: str) -> dict:
    """Aktueller Zustand aller Dinge, die wintheme ändert."""
    snap = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "label": label, "registry": [], "files": {}, "wallpaper": None}
    if IS_WIN:
        for path, name in REG_VALUES:
            got = reg_get(path, name)
            if got is None:
                snap["registry"].append({"path": path, "name": name, "missing": True})
            else:
                value, kind = got
                if isinstance(value, bytes):
                    value = {"b64": base64.b64encode(value).decode()}
                snap["registry"].append({"path": path, "name": name, "kind": kind, "value": value})
        wp = reg_get(DESKTOP, "WallPaper")
        snap["wallpaper"] = wp[0] if wp else None
    for f in terminal_settings() + vscode_settings() + ([OHMYPOSH] if OHMYPOSH.is_file() else []):
        snap["files"][str(f)] = f.read_text(encoding="utf-8-sig")
    snap["komorebi"] = json.loads(KOMOREBI_LAST.read_text(encoding="utf-8")) if KOMOREBI_LAST.is_file() else None
    return snap


def remember(label: str) -> None:
    snap = snapshot(label)
    HISTORY.mkdir(parents=True, exist_ok=True)
    if not ORIGINAL.exists():
        ORIGINAL.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    (HISTORY / f"{time.time_ns()}.json").write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    for old in sorted(HISTORY.glob("*.json"))[:-KEEP]:
        old.unlink()


def restore(snap: dict) -> None:
    if IS_WIN and snap["registry"]:
        for e in snap["registry"]:
            if e.get("missing"):
                reg_del(e["path"], e["name"])          # gab es vorher nicht → wieder entfernen
            else:
                v = e["value"]
                reg_set(e["path"], e["name"], e["kind"], base64.b64decode(v["b64"]) if isinstance(v, dict) else v)
        if snap.get("wallpaper") and Path(snap["wallpaper"]).is_file():
            set_wallpaper(Path(snap["wallpaper"]))
        broadcast()
    for path, text in snap["files"].items():
        if Path(path).parent.is_dir():
            write_file(Path(path), text)
    # komorebi: frühere Rahmenfarben wieder setzen – gab es keine, Konfiguration neu laden (eigenes Theme)
    if snap.get("komorebi"):
        set_borders(snap["komorebi"])
        KOMOREBI_LAST.write_text(json.dumps(snap["komorebi"]), encoding="utf-8")
    elif "komorebi" in snap:
        komorebic("reload-configuration")
        KOMOREBI_LAST.unlink(missing_ok=True)


def undo() -> int:
    steps = sorted(HISTORY.glob("*.json")) if HISTORY.exists() else []
    if not steps:
        print("wintheme: nichts mehr rückgängig zu machen")
        return 1
    snap = json.loads(steps[-1].read_text(encoding="utf-8"))
    restore(snap)
    steps[-1].unlink()
    print(f"Rückgängig: Stand vor „{snap['label']}“ ({snap['time']}) wiederhergestellt · noch {len(steps) - 1} Schritt(e)")
    return 0


def original() -> int:
    if not ORIGINAL.exists():
        print("wintheme: kein Originalzustand gespeichert (wintheme wurde noch nie angewendet)")
        return 1
    remember("Original wiederherstellen")                # auch das lässt sich mit --undo zurücknehmen
    snap = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    restore(snap)
    print(f"Originalzustand von {snap['time']} wiederhergestellt (mit --undo zurücknehmbar)")
    return 0


def history() -> int:
    steps = sorted(HISTORY.glob("*.json")) if HISTORY.exists() else []
    if ORIGINAL.exists():
        print(f"  Original: {json.loads(ORIGINAL.read_text(encoding='utf-8'))['time']}")
    for i, f in enumerate(reversed(steps), 1):
        d = json.loads(f.read_text(encoding="utf-8"))
        print(f"  --undo ×{i}: Stand vor „{d['label']}“ ({d['time']})")
    if not steps and not ORIGINAL.exists():
        print("  noch keine Stände gespeichert")
    return 0


# ── Ablauf ───────────────────────────────────────────────────────────────────
def run(image: Path, cfg: dict, set_wall: bool, only: set[str], dry: bool) -> None:
    pal = palette(image, cfg)
    if not dry:
        remember(f"{image.name} · {cfg['scheme']} · {cfg['mode']}")
    print(f"{image.name}: Ausgangsfarbe {pal['source']} · {cfg['scheme']} · {'dunkel' if pal['dark'] else 'hell'}")
    parts = [("windows", "Windows", lambda: apply_windows(pal, image, set_wall, cfg["titlebars"], dry)),
             ("terminal", "Windows Terminal", lambda: apply_terminal(pal, dry)),
             ("vscode", "VS Code", lambda: apply_vscode(pal, dry)),
             ("ohmyposh", "oh-my-posh", lambda: apply_ohmyposh(pal, dry)),
             ("komorebi", "komorebi", lambda: apply_komorebi(pal, dry))]
    skipped = []
    for key, name, fn in parts:
        if key not in only:
            continue
        msg = fn()
        if msg is None:              # Werkzeug nicht installiert → still überspringen, nur sammeln
            skipped.append(name)
        else:
            print("  " + msg)
    if skipped:
        print("  übersprungen (nicht installiert): " + ", ".join(skipped))


def watch(cfg_only: set[str]) -> None:
    """Wallpaper-Wechsel in Windows erkennen und neu einfärben (für den Autostart, pythonw)."""
    last = None
    while True:
        try:
            p = current_wallpaper()
            key = (str(p), p.stat().st_mtime) if p else None
            if key and key != last:
                if last is not None:
                    run(p, load_config(), False, cfg_only, False)
                last = key
        except Exception as e:     # nie abstürzen, nächster Versuch in 5 s
            import traceback
            print("wintheme --watch:", e, file=sys.stderr)
            log_raw(traceback.format_exc())
        time.sleep(5)


def main() -> int:
    ap = argparse.ArgumentParser(prog="wintheme", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", nargs="?", help="Bild (sonst aktuelles Wallpaper)")
    ap.add_argument("--mode", choices=["dark", "light"])
    ap.add_argument("--scheme", choices=list(SCHEMES))
    ap.add_argument("--color", help="1–4 oder auto (Ausgangsfarbe für dieses Bild)")
    ap.add_argument("--contrast", type=float, help="-1 … 1")
    ap.add_argument("--titlebars", choices=["on", "off"], help="Akzentfarbe in Titelleisten")
    ap.add_argument("--only", default=PARTS)
    ap.add_argument("--sources", action="store_true")
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--undo", action="store_true", help="letzten Schritt rückgängig")
    ap.add_argument("--original", action="store_true", help="Zustand vor der ersten Benutzung")
    ap.add_argument("--history", action="store_true", help="gespeicherte Stände anzeigen")
    a = ap.parse_args()
    if a.undo:
        return undo()
    if a.original:
        return original()
    if a.history:
        return history()

    cfg = load_config()
    changed = False
    for k in ("mode", "scheme", "contrast"):
        if getattr(a, k) is not None:
            cfg[k] = getattr(a, k); changed = True
    if a.titlebars:
        cfg["titlebars"] = a.titlebars == "on"; changed = True
    only = {x.strip() for x in a.only.split(",") if x.strip()}

    if a.watch:
        if changed:
            save_config(cfg)
        watch(only)
        return 0

    image = Path(a.image).expanduser().resolve() if a.image else current_wallpaper()
    if not image or not image.is_file():
        print("wintheme: kein Bild angegeben und kein Windows-Wallpaper gefunden", file=sys.stderr)
        return 1
    if a.sources:
        for i, c in enumerate(source_colors(image), 1):
            print(f"  {i}: {hexc(c)}")
        return 0
    if a.color:
        if a.color == "auto":
            cfg["pick"].pop(image.name, None)
        else:
            cfg["pick"][image.name] = max(1, min(4, int(a.color))) - 1
        changed = True
    if changed and not a.dry_run:
        save_config(cfg)
    run(image, cfg, set_wall=bool(a.image), only=only, dry=a.dry_run)
    return 0


if __name__ == "__main__":
    sys.stdout, sys.stderr = Tee(sys.stdout), Tee(sys.stderr)
    log_raw(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} wintheme {' '.join(sys.argv[1:])}\n")
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()          # landet über Tee auch im Protokoll
        sys.exit(1)
