#!/bin/bash

# Couleurs pour les messages
ROUGE='\033[0;31m'
VERT='\033[0;32m'
JAUNE='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
afficher_message() {
    echo -e "${2}${1}${NC}"
}

# Vérifier si Python est installé
verifier_python() {
    afficher_message "Vérification de l'installation de Python..." "$JAUNE"
    if command -v python3 &> /dev/null; then
        afficher_message "Python est installé" "$VERT"
        return 0
    else
        afficher_message "Erreur : Python n'est pas installé" "$ROUGE"
        return 1
    fi
}

# Installer les dépendances
installer_dependances() {
    afficher_message "Installation des dépendances en cours..." "$JAUNE"

    # Même environnement .venv que lancer.command (le Python du système refuse souvent
    # les installations directes : « externally-managed-environment »)
    RACINE="$(cd "$(dirname "$0")/.." && pwd)"
    if python3 -m venv "$RACINE/.venv" && "$RACINE/.venv/bin/python" -m pip install -r "$RACINE/requirements.txt"; then
        afficher_message "Toutes les dépendances ont été installées avec succès !" "$VERT"
        return 0
    fi
    afficher_message "Échec de l'installation des dépendances" "$ROUGE"
    return 1
}

# Fonction principale
main() {
    afficher_message "Démarrage de l'installation des dépendances..." "$JAUNE"
    
    # Vérifier Python
    if ! verifier_python; then
        afficher_message "Veuillez installer Python 3 en premier" "$ROUGE"
        exit 1
    fi
    
    # Installer les dépendances
    if ! installer_dependances; then
        afficher_message "Échec de l'installation de certaines dépendances" "$ROUGE"
        exit 1
    fi
    
    afficher_message "Installation terminée avec succès !" "$VERT"
}

# Exécuter le script
main 