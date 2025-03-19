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

# Vérifier si pip est installé
verifier_pip() {
    afficher_message "Vérification de l'installation de pip..." "$JAUNE"
    if command -v pip3 &> /dev/null; then
        afficher_message "pip est installé" "$VERT"
        return 0
    else
        afficher_message "Erreur : pip n'est pas installé" "$ROUGE"
        return 1
    fi
}

# Installer les dépendances
installer_dependances() {
    afficher_message "Installation des dépendances en cours..." "$JAUNE"
    
    # Liste des dépendances avec leurs versions
    dependances=(
        "pygame==2.5.2"
        "numpy==1.24.3"
        "opencv-python==4.8.0.74"
        "PyOpenGL==3.1.7"
        "PyOpenGL-accelerate==3.1.7"
    )
    
    for dep in "${dependances[@]}"; do
        afficher_message "Installation de $dep..." "$JAUNE"
        pip3 install "$dep"
        if [ $? -eq 0 ]; then
            afficher_message "Installation réussie de $dep" "$VERT"
        else
            afficher_message "Échec de l'installation de $dep" "$ROUGE"
            return 1
        fi
    done
    
    afficher_message "Toutes les dépendances ont été installées avec succès !" "$VERT"
    return 0
}

# Fonction principale
main() {
    afficher_message "Démarrage de l'installation des dépendances..." "$JAUNE"
    
    # Vérifier Python
    if ! verifier_python; then
        afficher_message "Veuillez installer Python 3 en premier" "$ROUGE"
        exit 1
    fi
    
    # Vérifier pip
    if ! verifier_pip; then
        afficher_message "Veuillez installer pip en premier" "$ROUGE"
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