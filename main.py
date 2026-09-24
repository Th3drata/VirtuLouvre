# Projet : VirtuLouvre
# Auteurs : Albert Oscar, Moors Michel, Rinckenbach Yann
"""VirtuLouvre : six nuits pour sauver les trésors du Louvre.

Campagne de six missions dans six salles du musée (galerie d'Apollon, salle des États, Grande Galerie,
salle des Cariatides, crypte du Sphinx, escalier Daru), et visite libre de chaque salle.
Fonctionne sous Windows, macOS et Linux (Python 3.9+, pygame-ce, PyOpenGL, NumPy).

Lancer le jeu : python main.py        Auto-test sans fenêtre : python main.py --test
"""

import math
import os
import random
import sys
import tempfile

import jeu  # vérifie pygame-ce et règle PyOpenGL avant tout le reste


def self_test():
    """Vérifications sans fenêtre ni carte graphique : réglages, modèles, salles, et chaque mission jouable."""
    import numpy as np
    import pygame

    from jeu import base, missions, modeles, salles
    from jeu.acteurs import PNJ, Player

    pygame.init()
    p = np.array

    # Réglages d'une ancienne version ou modifiés à la main
    fichier = os.path.join(tempfile.gettempdir(), "virtulouvre_test_settings.json")
    ancien, base.FICHIER_CONFIG = base.FICHIER_CONFIG, fichier
    try:
        with open(fichier, "w", encoding="utf-8") as f:
            f.write('{"volume": 0.0, "best_time": 25.08, "fov": 500, "sensitivity": 1e999, "controls": [["Z", "Avancer"]]}')
        r = base.load_settings()
    finally:
        os.remove(fichier)
        base.FICHIER_CONFIG = ancien
    assert r["volume"] == 0.0 and r["fov"] == 100 and r["sensitivity"] == 0.12
    assert r["controls"] == base.DEFAULT_SETTINGS["controls"]
    assert r["progress"]["apollon"] == {"stars": 3, "best": 25.08}, "l'ancien record devient celui de la nuit 1"
    assert base.fmt_time(125.3) == "2:05"
    assert abs(base.seg_seg_distance(p((0, 0, 0.)), p((0, 2, 0.)), p((-1, 1, 1.)), p((1, 1, 1.))) - 1.0) < 1e-9

    # Modèles : géométrie valide
    noms = [f"humain:{t}" for t in modeles.TENUES] + [f"joyau:{k}" for k in range(8)] + list(modeles.FABRIQUES) + \
           [f"stele:{s}" for s in modeles.SYMBOLES] + ["statue:0", "buste:0"]
    triangles = 0
    for nom in noms:
        for forme in modeles.modele(nom).parties.values():
            for mat, (tris, norms) in forme.tableaux().items():
                assert mat in modeles.MATERIAUX and np.isfinite(tris).all(), nom
                assert (abs(np.linalg.norm(norms, axis=-1) - 1) < 1e-3).all(), nom
                triangles += len(tris)

    # Salles : on part d'un endroit libre et chaque salle est éclairée
    toutes = {nom: salles.construire(nom) for nom in salles.SALLES}
    for nom, s in toutes.items():
        x, y, z, _ = s.depart
        assert s.libre(x, z, y) and s.lumieres, nom

    # Nuit 1 : chaque joyau peut être ramassé depuis une case accessible
    apollon = toutes["apollon"]
    spots, vitrine = missions.cachettes_apollon(apollon)
    X, Z = apollon.centres()
    accessibles = np.column_stack([X[apollon.atteint], Z[apollon.atteint]])
    for graine in range(100):
        cachettes = missions.placer_joyaux(spots, vitrine, random.Random(graine))
        assert len(set(cachettes)) == 8
        for x, _, z in cachettes:
            assert np.hypot(accessibles[:, 0] - x, accessibles[:, 1] - z).min() < missions.PICK_RADIUS - 0.1, (x, z)
    joueur = Player(0.2, 0.0, 18.2, yaw=180.0)  # face au mur de gauche : on avance mais on ne le traverse pas
    for _ in range(300):
        joueur.update(1 / 60, lambda action: action == "forward", apollon)
    assert -3.0 < joueur.pos[0] < -1.8 and abs(joueur.pos[1]) < 1e-9

    # Nuit 6 : on monte l'escalier Daru jusqu'au palier de la Victoire
    daru = toutes["daru"]
    joueur = Player(0.0, 0.0, 14.5)
    for _ in range(600):
        joueur.update(1 / 60, lambda action: action == "forward", daru)
    assert abs(joueur.pos[1] - salles.PALIER) < 0.01, joueur.pos

    class FauxApp:
        """Ce dont une mission a besoin de l'application, sans fenêtre ni son."""
        t, toast, torche = 0.0, None, False

        def __init__(self, salle, joueur):
            self.salle, self.player, self.resultat = salle, joueur, None
            self.audio = type("Silence", (), {"play": lambda *a: None, "spatial": lambda *a: None})()

        def notice(self, *a):
            pass

        def burst(self, *a):
            pass

        def fin_mission(self, gagne, texte):
            self.resultat = gagne

    # Nuit 4 : les points de contrôle ne sont pas sur un laser fixe
    lasers = missions.MissionLasers(FauxApp(toutes["cariatides"], Player(0, 0, 0)))
    lasers.demarrer()
    for x, z in lasers.POINTS:
        corps = (p((x, 0.05, z)), p((x, base.BODY, z)))
        for l, a, b, actif in lasers.segments():
            if l["type"] == "fixe":
                assert base.seg_seg_distance(*corps, a, b) > 0.5, (x, z)

    # Nuit 3 : un robot qui court après le voleur (en gérant son souffle) doit le rattraper
    salle = toutes["grande_galerie"]
    salle.reset()
    x, y, z, lacet = salle.depart
    app = FauxApp(salle, Player(x, y, z, lacet))
    poursuite = missions.MissionPoursuite(app)
    poursuite.demarrer()
    route, dt = missions.ROUTE_VOLEUR, 1 / 60
    for _ in range(int(60 / dt)):
        j, v = app.player, poursuite.voleur
        if math.hypot(v.pos[0] - j.pos[0], v.pos[2] - j.pos[2]) < 5:
            cible = v.pos
        else:  # il suit le même chemin que le voleur (qui contourne les bancs)
            k = next((i for i, (_, zr) in enumerate(route) if zr < j.pos[2] - 1.0), len(route) - 1)
            cible = (route[k][0], 0, route[k][1])
        voulu = base.angle_vers(cible[0] - j.pos[0], cible[2] - j.pos[2])
        for ecart in (0, 30, -30, 60, -60, 90, -90):  # contourne les chariots renversés
            a = math.radians(voulu + ecart)
            if salle.libre(j.pos[0] + math.cos(a) * 0.9, j.pos[2] + math.sin(a) * 0.9, j.pos[1]):
                j.yaw = voulu + ecart
                break
        j.update(dt, lambda a: a in ("forward", "sprint"), salle, endurance=True)
        poursuite.temps += dt
        poursuite.update(dt)
        if app.resultat is not None:
            break
    assert app.resultat is True, "le voleur doit pouvoir être rattrapé"
    temps_poursuite = poursuite.temps

    # Nuit 6 : la proue de la Victoire cache le joueur ; une caisse cache le joueur accroupi, pas debout
    daru.reset()
    guetteur = PNJ("guetteur", -5.2, -12.5, yaw=0.0, salle=daru)
    assert not guetteur.voit(p((4.0, salles.PALIER + 1.6, -12.5)), daru, 12)
    guetteur = PNJ("guetteur", -5.2, -9.0, yaw=0.0, salle=daru)
    daru.bloquer_rect(-0.5, -9.4, 0.5, -8.6, salles.PALIER + 1.25)
    assert not guetteur.voit(p((1.2, salles.PALIER + base.CROUCH_BODY - 0.1, -9.0)), daru, 12)
    assert guetteur.voit(p((1.2, salles.PALIER + base.BODY - 0.1, -9.0)), daru, 12)
    for s in toutes.values():
        s.reset()
    print(f"Auto-test OK : {len(noms)} modèles ({triangles} triangles), {len(toutes)} salles, "
          f"voleur rattrapé en {temps_poursuite:.1f} s")


if __name__ == "__main__":
    if "--test" in sys.argv:
        self_test()
    else:
        from jeu.app import App

        App().run()
