#!/usr/bin/env bash
# VS-Code-Vorlage aus der Matugen-Config des Linux-Laptops übernehmen (gleiche Farbzuordnung unter Windows).
# Erwartet die Linux-Dotfiles daneben: ../../dotfiles (oder DOTFILES=/pfad)
set -euo pipefail
here=$(dirname "$(readlink -f "$0")")
src="${DOTFILES:-$here/../../dotfiles}/matugen/.config/matugen/templates/vscode-colors.json"
cp "$src" "$here/templates/"
echo "templates/vscode-colors.json aktualisiert (aus $src)"
