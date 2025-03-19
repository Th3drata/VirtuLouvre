# VirtuLouvre

VirtuLouvre est un jeu vidéo 3D qui permet d'explorer le musée du Louvre de manière virtuelle. Le projet utilise Pygame et OpenGL pour créer une expérience immersive.

## Prérequis

- Python 3.8 ou supérieur
- Pygame
- OpenGL
- NumPy
- OpenCV

## Installation

1. Clonez le dépôt :

```bash
git clone https://github.com/Th3drata/VirtuLouvre.git
cd VirtuLouvre
```

2. Installez les dépendances requises :

Option 1 - Installation automatique avec requirements.txt :

```bash
pip install -r requirements.txt
```

Option 2 - Installation manuelle des dépendances :

```bash
pip install pygame
pip install numpy
pip install opencv-python
pip install PyOpenGL
pip install PyOpenGL_accelerate
```

## Structure du projet

```
VirtuLouvre/
├── src/
│   ├── media/         # Fichiers audio et vidéo
│   ├── models/        # Modèles 3D
│   ├── textures/      # Textures
│   └── icons/         # Icônes de l'interface
├── config/            # Fichiers de configuration
├── main.py           # Point d'entrée du programme
├── requirements.txt  # Liste des dépendances
├── README.md         # Ce fichier
└── licence.txt       # Licence du projet
```

## Lancement du projet

Pour lancer le projet, exécutez simplement :

```bash
python main.py
```

## Contrôles

- Z/S : Avancer/Reculer
- Q/D : Se déplacer à gauche/droite
- ESPACE : Voler
- SHIFT : Descendre
- G : Atterrir
- V : Sprint
- ÉCHAP : Menu
- F11 : Plein écran

## Configuration

Les paramètres du jeu (contrôles, volume, résolution) sont sauvegardés automatiquement dans le dossier `config/`.

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou à soumettre une pull request.

## Licence

Ce projet est sous licence GPL v3+. Voir le fichier `licence.txt` pour plus de détails.

## Documentation technique

### Structure du code

#### Fichiers principaux

- `main.py` : Point d'entrée du programme. Contient la logique principale du jeu, la gestion des états (menu, jeu, paramètres) et l'initialisation de l'environnement 3D.

#### Classes principales

1. `Player` : Gère le joueur et la caméra

   - Gestion des mouvements
   - Gestion de la caméra
   - Gestion des collisions
   - Gestion du vol et de la gravité

2. `Button` : Gère les boutons de l'interface
   - Création et affichage des boutons
   - Gestion des interactions
   - Styles et animations

#### Systèmes

1. Système de rendu 3D

   - Utilisation d'OpenGL pour le rendu 3D
   - Gestion des textures et des modèles
   - Système de caméra

2. Système de menu

   - Menu principal
   - Menu de paramètres
   - Menu de crédits

3. Système de configuration
   - Sauvegarde/chargement des paramètres
   - Gestion des contrôles
   - Gestion du volume

### Architecture

Le projet suit une architecture modulaire avec :

- Une séparation claire entre l'interface utilisateur et la logique de jeu
- Un système d'états pour gérer les différentes vues (menu, jeu, paramètres)
- Une gestion centralisée des ressources (textures, modèles, sons)

### Ressources

Les ressources sont organisées dans le dossier `src/` :

- `media/` : Fichiers audio et vidéo
- `models/` : Modèles 3D
- `textures/` : Textures
- `icons/` : Icônes de l'interface
