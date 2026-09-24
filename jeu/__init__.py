"""VirtuLouvre : moteur, salles, personnages et missions du jeu.

Ce fichier est exécuté avant tout le reste du paquet : il vérifie pygame-ce et règle PyOpenGL.
"""

import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")  # pas de message de pygame dans la console

import OpenGL
import pygame

if not getattr(pygame, "IS_CE", False):  # pygame « classique » et pygame-ce s'installent au même endroit
    sys.exit("VirtuLouvre a besoin de pygame-ce (et pas de pygame) : pip uninstall pygame pygame-ce, "
             "puis pip install -r requirements.txt")

OpenGL.ERROR_CHECKING = False  # plus rapide, et un pilote graphique capricieux ne fait pas planter le jeu
