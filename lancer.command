#!/usr/bin/env bash
# Lance VirtuLouvre sous macOS (double-clic) ou Linux (./lancer.command).
# Au premier lancement, crée un environnement Python (.venv) et installe les dépendances.
cd "$(dirname "$0")" || exit 1

if ! .venv/bin/python -c "import pygame, OpenGL, numpy" 2>/dev/null; then
    echo "Premier lancement : installation des dépendances..."
    # --clear : repart de zéro si un ancien .venv est cassé (Python mis à jour...)
    if ! { python3 -m venv --clear .venv && .venv/bin/python -m pip install -r requirements.txt; }; then
        echo
        echo "Installation impossible. Vérifie que Python 3.9 (ou plus récent) est installé :"
        echo "  macOS : https://www.python.org/downloads/"
        echo "  Linux : sudo apt install python3 python3-venv   (ou l'équivalent de ta distribution)"
        read -r -p "Appuie sur Entrée pour fermer."
        exit 1
    fi
fi

exec .venv/bin/python main.py "$@"
