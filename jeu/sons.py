"""Sons et musiques du jeu, tous synthétisés avec NumPy au lancement : aucun fichier audio.

Boîte à outils : enveloppes, bruit filtré (dans le domaine de Fourier), synthèse additive (cloches, marimba,
piano, cuivres, cordes), cordes pincées (Karplus-Strong), voix (formants), réverbération par convolution, stéréo.
Les boucles (musiques, ambiances) se raccordent sans clic : tout y est calculé « en rond » (FFT circulaire).
Les musiques des missions sont préparées en arrière-plan pendant qu'on est dans le menu.
Sans carte son (machine virtuelle, serveur...), le jeu tourne quand même, en silence."""

import math
import random
import threading

import numpy as np
import pygame

R = 44100  # échantillons par seconde (pygame.mixer.pre_init l'impose dans app.py)
CRETE = 0.7  # crête de chaque son : pygame additionne les canaux et sature au-delà de 1, il faut de la marge

# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------


def temps(duree):
    return np.arange(int(R * duree)) / R


def midi(note):
    return 440.0 * 2 ** ((note - 69) / 12)


def enveloppe(t, attaque=0.004, chute=0.3):
    return (1 - np.exp(-t / attaque)) * np.exp(-t / chute)


def bruit(forme, graine=None):
    return np.random.default_rng(graine).standard_normal(forme)


def filtre(x, bas=None, haut=None, ordre=2):
    """Filtre doux (gain d'un Butterworth, appliqué dans le domaine de Fourier) : garde bas < f < haut."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / R)
    g = np.ones_like(f)
    if haut:
        g /= np.sqrt(1 + (f / haut) ** (2 * ordre))
    if bas:
        g /= np.sqrt(1 + (bas / np.maximum(f, 1e-3)) ** (2 * ordre))
    return np.fft.irfft(np.fft.rfft(x, axis=0) * (g[:, None] if x.ndim > 1 else g), n, axis=0)


def formants(f, voyelle, largeur=1.0):
    """Gain en fonction de la fréquence pour une voyelle (trois résonances de la bouche)."""
    g = np.zeros_like(f)
    for k, (centre, bande) in enumerate(zip(VOYELLES[voyelle], (80, 110, 160))):
        g += (1.0, 0.6, 0.3)[k] / (1 + ((f - centre) / (bande * largeur)) ** 2)
    return g


VOYELLES = {"a": (730, 1090, 2440), "e": (530, 1840, 2480), "i": (300, 2200, 2950), "o": (520, 860, 2410),
            "u": (320, 870, 2240), "é": (400, 2000, 2600), "m": (260, 1100, 2200)}


def filtre_variable(x, gains, trame=2048):
    """Filtre qui change au cours du temps : `gains(t, f)` donne le gain à l'instant t (fenêtres de Hann à 50 %)."""
    n, pas = len(x), trame // 2
    fenetre = np.hanning(trame + 1)[:-1]
    f = np.fft.rfftfreq(trame, 1 / R)
    y = np.zeros(n + trame)
    xp = np.concatenate([x, np.zeros(trame)])
    for debut in range(0, n, pas):
        morceau = xp[debut:debut + trame] * fenetre
        y[debut:debut + trame] += np.fft.irfft(np.fft.rfft(morceau) * gains(debut / R, f), trame)
    return y[:n]


def stereo(x, pan=0.0):
    """Mono -> stéréo, placé de -1 (gauche) à 1 (droite) à puissance constante."""
    if x.ndim == 2:
        return x
    a = (pan + 1) * math.pi / 4
    return np.column_stack([x * math.cos(a), x * math.sin(a)]) * math.sqrt(2)


def reponse(duree, graine=1, clair=5000):
    """Réponse impulsionnelle d'une salle : bruit qui s'éteint (différent à gauche et à droite)."""
    t = temps(duree)
    ir = filtre(bruit((len(t), 2), graine) * np.exp(-6.9 * t / duree)[:, None], haut=clair)
    ir[: int(R * 0.012)] *= np.linspace(0, 1, int(R * 0.012))[:, None]  # un léger délai avant l'écho
    return ir / np.sqrt((ir ** 2).sum(0))


def reverb(x, duree=1.6, humide=0.3, boucle=False, clair=5000):
    """Ajoute l'écho d'une salle. En boucle, la queue de l'écho revient au début (convolution circulaire)."""
    x = stereo(x)
    ir = reponse(duree, clair=clair)
    n = len(x) if boucle else len(x) + len(ir)
    if boucle and len(ir) > n:
        ir = ir[:n] * np.linspace(1, 0, n)[:, None]
    X, H = np.fft.rfft(x, n, axis=0), np.fft.rfft(ir, n, axis=0)
    humide_ = np.fft.irfft(X * H, n, axis=0) * 0.5
    sec = x if boucle else np.concatenate([x, np.zeros((n - len(x), 2))])
    return sec * (1 - humide * 0.5) + humide_ * humide


def normaliser(x, crete=0.95):
    return x / (np.abs(x).max() + 1e-9) * crete


def poser(piste, debut, onde, gain=1.0, pan=0.0):
    """Ajoute un son dans une piste qui boucle (ce qui dépasse de la fin revient au début)."""
    o = stereo(onde, pan) * gain
    n, i = len(piste), int(round(debut * R)) % len(piste)
    while len(o):
        k = min(len(o), n - i)
        piste[i:i + k] += o[:k]
        o, i = o[k:], 0


def piste(duree):
    return np.zeros((int(R * duree), 2))


def melanger(*ondes):
    """Additionne des sons mono de longueurs différentes."""
    total = np.zeros(max(len(o) for o in ondes))
    for o in ondes:
        total[:len(o)] += o
    return total


# ---------------------------------------------------------------------------
# Instruments
# ---------------------------------------------------------------------------


def partiels(f, duree, liste, attaque=0.002):
    """Synthèse additive : liste de (rapport de fréquence, amplitude, durée d'extinction)."""
    t = temps(duree)
    onde = sum(a * np.sin(2 * np.pi * f * r * t + r) * np.exp(-t / d) for r, a, d in liste if f * r < R / 2.2)
    fin = np.clip((duree - t) / 0.02, 0, 1)
    return onde * (1 - np.exp(-t / attaque)) * fin


def cloche(f, duree=2.0):
    return partiels(f, duree, [(1, 1, duree * 0.45), (2.0, 0.35, duree * 0.25), (2.76, 0.4, duree * 0.18),
                               (5.4, 0.2, duree * 0.08), (8.93, 0.1, duree * 0.05)])


def verre(f, duree=1.6):
    """Tintement cristallin (verre, joyau)."""
    return partiels(f, duree, [(1, 1, duree * 0.5), (2.32, 0.45, duree * 0.3), (4.25, 0.25, duree * 0.15),
                               (6.63, 0.12, duree * 0.08)], attaque=0.001)


def marimba(f, duree=0.9):
    t = temps(duree)
    maillet = filtre(bruit(len(t), 5) * np.exp(-t / 0.003), haut=2500) * 0.15
    return partiels(f, duree, [(1, 1, 0.35), (3.93, 0.3, 0.07), (9.2, 0.1, 0.025)], 0.001) + maillet


def piano(f, duree=2.5, force=0.7):
    """Piano : partiels un peu désaccordés (corde raide), deux cordes qui battent, coup de marteau."""
    t = temps(duree)
    onde = np.zeros_like(t)
    tenue = 2.8 * (220 / f) ** 0.35
    for k in range(1, 9):
        fk = f * k * math.sqrt(1 + 0.0004 * k * k)
        if fk > 9000:
            break
        a = force ** (0.4 * k) / k ** 1.2
        d = tenue / (1 + 0.45 * (k - 1))
        for ecart in (-0.0007, 0.0007):
            onde += a * np.sin(2 * np.pi * fk * (1 + ecart) * t + k) * (0.6 * np.exp(-t / (d * 0.2)) + 0.4 * np.exp(-t / d))
    marteau = filtre(bruit(len(t), int(f)) * np.exp(-t / 0.004), haut=2500 + 2500 * force) * 0.08
    fin = np.clip((duree - t) / 0.08, 0, 1)
    return (onde * (1 - np.exp(-t / 0.0015)) + marteau) * fin * 0.25


def pince(f, duree=1.5, clarte=0.6, graine=0):
    """Corde pincée (Karplus-Strong) : harpe, pizzicato, luth. Calculé une période à la fois."""
    n = int(R * duree)
    p = max(2, int(round(R / f)))
    lissage = max(1, int(1 + (1 - clarte) * 6))
    debut = np.convolve(np.random.default_rng(graine).uniform(-1, 1, p + lissage), np.ones(lissage) / lissage, "valid")[:p]
    debut -= debut.mean()  # sans composante continue (sinon la corde « pousse » le haut-parleur)
    amort = math.exp(-p / (R * duree * 0.3))
    y = np.zeros(n + p)
    y[:p] = debut
    for i in range(p, n + p, p):
        avant = y[i - p:i]
        suite = (0.5 * (avant + np.concatenate([[y[i - p - 1] if i > p else 0.0], avant[:-1]])) * amort)
        y[i:i + p] = suite[:len(y[i:i + p])]
    t = temps(duree)
    return y[p:p + n] * np.clip((duree - t) / 0.05, 0, 1)


def scie(phase, harmoniques):
    """Onde en dents de scie sans repliement (somme de sinusoïdes)."""
    return sum(np.sin(2 * np.pi * k * phase) / k for k in range(1, harmoniques + 1))


def cordes(f, duree, attaque=0.25, relache=0.4, clarte=1.0):
    """Ensemble de cordes : trois dents de scie légèrement désaccordées, vibrato, attaque lente."""
    t = temps(duree + relache)
    vibrato = 1 + 0.003 * np.sin(2 * np.pi * 5.3 * t) * np.clip(t / 0.4, 0, 1)
    h = max(1, min(14, int(3500 * clarte / f)))
    onde = sum(scie(np.cumsum(f * (1 + e) * vibrato) / R, h) for e in (-0.004, 0.0, 0.0045))
    env = np.clip(t / attaque, 0, 1) * np.clip((duree + relache - t) / relache, 0, 1)
    return onde * env * 0.25


def cuivre(f, duree, relache=0.15):
    """Cuivres : plus on souffle fort, plus le son est brillant (harmoniques aiguës qui montent avec l'enveloppe)."""
    t = temps(duree + relache)
    env = np.clip(t / 0.05, 0, 1) * (0.8 + 0.2 * np.exp(-t / 0.1)) * np.clip((duree + relache - t) / relache, 0, 1)
    phase = np.cumsum(f * (1 + 0.004 * np.sin(2 * np.pi * 5 * t) * np.clip(t - 0.2, 0, 1))) / R
    return sum(np.sin(2 * np.pi * k * phase) * env ** (1 + 0.45 * k) / k ** 0.7 for k in range(1, 13) if f * k < 9000) * 0.3


def grosse_caisse(duree=0.5):
    t = temps(duree)
    f = 48 + 90 * np.exp(-t / 0.035)
    return np.sin(2 * np.pi * np.cumsum(f) / R) * np.exp(-t / 0.2) + filtre(bruit(len(t), 1) * np.exp(-t / 0.003), haut=3000) * 0.3


def caisse_claire(duree=0.3):
    t = temps(duree)
    return filtre(bruit(len(t), 2), bas=900) * np.exp(-t / 0.08) * 0.6 + np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.04)


def charleston(duree=0.08, graine=3):
    t = temps(duree)
    return filtre(bruit(len(t), graine), bas=7000) * np.exp(-t / 0.018) * 0.5


def tambour_sur_cadre(grave=True, duree=0.6):
    """Tambour sur cadre : « doum » grave au centre, « tek » claquant sur le bord."""
    t = temps(duree)
    if grave:
        return np.sin(2 * np.pi * np.cumsum(85 + 30 * np.exp(-t / 0.02)) / R) * np.exp(-t / 0.18)
    return filtre(bruit(len(t), 8), bas=1800, haut=6000) * np.exp(-t / 0.03) + 0.4 * np.sin(2 * np.pi * 420 * t) * np.exp(-t / 0.05)


def bloc_de_bois(f=1100, duree=0.12):
    t = temps(duree)
    return partiels(f, duree, [(1, 1, 0.03), (2.4, 0.3, 0.01)], 0.0005) + filtre(bruit(len(t), 4), bas=2000) * np.exp(-t / 0.002) * 0.3


def voix(duree, f0, syllabes, souffle=0.08, graine=0):
    """Voix synthétique : une source (la glotte) filtrée par les formants des voyelles.
    `f0` : fonction t -> hauteur ; `syllabes` : [(début, fin, voyelle)]."""
    t = temps(duree)
    phase = np.cumsum(f0(t)) / R
    source = (2 * (phase % 1) - 1) + bruit(len(t), graine) * souffle
    amplitude = np.zeros_like(t)
    for a, b, _ in syllabes:
        m = (t >= a) & (t < b)
        amplitude[m] = np.sin(np.pi * (t[m] - a) / (b - a)) ** 0.6

    def gains(instant, f):
        voyelle = next((v for a, b, v in syllabes if a <= instant < b), "m")
        return formants(f, voyelle)
    return filtre_variable(source * amplitude, gains)


# ---------------------------------------------------------------------------
# Bruitages
# ---------------------------------------------------------------------------


def pas(sol, graine):
    """Un pas (talon puis pointe) sur du parquet, du marbre ou de la pierre."""
    h = np.random.default_rng(graine)
    t = temps(0.35)

    def impact(force, graine2):
        b = bruit(len(t), graine2)
        if sol == "parquet":  # bois creux : un « toc » grave et sourd
            f = h.uniform(150, 230)
            son = filtre(b, haut=900) * np.exp(-t / 0.018) * 0.8 + np.sin(2 * np.pi * f * t) * np.exp(-t / 0.035) \
                + 0.3 * np.sin(2 * np.pi * f * 3.1 * t) * np.exp(-t / 0.012)
        elif sol == "marbre":  # talon sur une pierre polie : un claquement net qui résonne
            son = filtre(b, bas=1500, haut=9000) * np.exp(-t / 0.006) + 0.25 * partiels(h.uniform(1800, 2600), 0.35, [
                (1, 1, 0.03), (1.6, 0.5, 0.02)], 0.0005) + 0.5 * np.sin(2 * np.pi * 110 * t) * np.exp(-t / 0.02)
        else:  # pierre, poussière : un frottement granuleux
            grains = (h.random(len(t)) < 0.02) * h.standard_normal(len(t))
            son = filtre(b * 0.4 + grains * 3, bas=300, haut=3500) * np.exp(-t / 0.045) \
                + 0.6 * np.sin(2 * np.pi * 95 * t) * np.exp(-t / 0.025)
        return son * force * (1 - np.exp(-t / 0.0008))
    onde = impact(1.0, graine * 2 + 1)
    decale = int(R * h.uniform(0.055, 0.085))
    onde[decale:] += impact(0.55, graine * 2 + 2)[:len(t) - decale]
    salle = {"parquet": (1.3, 0.22), "marbre": (1.9, 0.3), "pierre": (1.6, 0.25)}[sol]
    return reverb(onde * np.clip((0.35 - t) / 0.05, 0, 1), *salle)


def atterrissage(sol):
    """Retomber d'un saut : un pas appuyé et un choc sourd."""
    onde = pas(sol, 10) * 1.4
    t = temps(0.25)
    onde[:len(t)] += (np.sin(2 * np.pi * np.cumsum(70 + 60 * np.exp(-t / 0.02)) / R) * np.exp(-t / 0.06) * 0.8)[:, None]
    return onde


def grondement(duree=1.8, graine=6):
    """La pierre qui gronde : bruit très grave, irrégulier, avec des craquements."""
    t = temps(duree)
    fond = filtre(bruit(len(t), graine), bas=45, haut=140, ordre=3) * 6
    craquements = filtre((np.random.default_rng(graine).random(len(t)) < 0.003) * bruit(len(t), graine + 1), bas=200, haut=1500) * 2
    houle = 0.6 + 0.4 * np.sin(2 * np.pi * 2.3 * t) * np.sin(2 * np.pi * 0.7 * t)
    env = np.clip(t / 0.15, 0, 1) * np.exp(-t / (duree * 0.45))
    return reverb((fond * houle + craquements + 0.4 * np.sin(2 * np.pi * 52 * t)) * env, 2.5, 0.35, clair=2000)


def raclement(duree=2.2):
    """Un bloc de pierre qui glisse (le tiroir du Sphinx), puis se cale avec un choc sourd."""
    t = temps(duree)
    h = np.random.default_rng(12)
    accroche = np.repeat(h.random(int(duree * 45) + 1), int(R / 45) + 1)[:len(t)] ** 2  # glisse, accroche, glisse...
    frottement = filtre(bruit(len(t), 13), bas=250, haut=2200) * (0.35 + accroche)
    env = np.clip(t / 0.2, 0, 1) * np.clip((duree - 0.3 - t) / 0.2, 0, 1)
    choc_t = temps(0.6)
    choc = np.sin(2 * np.pi * 58 * choc_t) * np.exp(-choc_t / 0.12) * 1.5 + filtre(bruit(len(choc_t), 14), haut=600) * np.exp(-choc_t / 0.05)
    onde = np.concatenate([frottement * env, np.zeros(len(choc_t))])
    onde[len(t) - int(R * 0.28):len(t) - int(R * 0.28) + len(choc_t)] += choc
    return reverb(onde, 2.2, 0.35, clair=3000)


def fracas():
    """Un chariot renversé : métal qui s'entrechoque, bois, objets qui roulent."""
    t = temps(1.4)
    h = np.random.default_rng(21)
    onde = np.zeros_like(t)
    for k in range(9):
        d = int(R * (k * 0.07 + h.uniform(0, 0.05)))
        f = h.uniform(300, 1400)
        metal = partiels(f, 0.8, [(1, 1, 0.25), (2.71, 0.6, 0.15), (5.03, 0.4, 0.08), (7.4, 0.2, 0.05)], 0.0005)
        onde[d:d + len(metal)] += (metal[:len(t) - d] * 0.9 ** k)
    onde += filtre(bruit(len(t), 22), bas=400) * np.exp(-t / 0.15) * 0.8 + np.sin(2 * np.pi * 70 * t) * np.exp(-t / 0.1)
    return reverb(onde, 2.0, 0.35)


def sonnerie(duree=1.4):
    """Sonnerie d'alarme : une cloche électrique frappée 20 fois par seconde."""
    t = temps(duree)
    coups = np.zeros_like(t)
    coups[(np.arange(0, duree, 1 / 20) * R).astype(int)] = 1.0
    timbre = partiels(1650, 0.12, [(1, 1, 0.04), (2.1, 0.6, 0.02), (3.9, 0.3, 0.015)], 0.0003)
    onde = np.convolve(coups, timbre)[:len(t)] * np.clip((duree - t) / 0.1, 0, 1)
    sirene = np.sin(2 * np.pi * np.cumsum(700 + 250 * np.sin(2 * np.pi * 1.4 * t)) / R) * 0.25
    return reverb(onde + sirene, 1.5, 0.25)


def sifflet(coups=((0.0, 0.22), (0.32, 0.75))):
    """Sifflet à roulette : deux sons proches qui battent, la bille qui roule, le souffle."""
    t = temps(coups[-1][1] + 0.05)
    roulette = 1 + 0.035 * np.sin(2 * np.pi * 34 * t + 3 * np.sin(2 * np.pi * 3 * t))
    onde = (np.sin(2 * np.pi * np.cumsum(2850 * roulette) / R) + 0.7 * np.sin(2 * np.pi * np.cumsum(3180 * roulette) / R))
    souffle = filtre(bruit(len(t), 31), bas=2000, haut=5000) * 0.35
    env = np.zeros_like(t)
    for a, b in coups:
        env += np.clip((t - a) / 0.012, 0, 1) * np.clip((b - t) / 0.03, 0, 1)
    return reverb((onde + souffle) * np.clip(env, 0, 1) * 0.5, 1.6, 0.3)


def menottes():
    """Clic-clic-clic des menottes, puis le verrou."""
    t = temps(0.7)
    onde = np.zeros_like(t)
    for k in range(7):
        d = int(R * (0.03 * k + (0.18 if k == 6 else 0)))
        clic = partiels(3200 + 120 * k, 0.08, [(1, 1, 0.012), (1.47, 0.7, 0.01), (2.3, 0.4, 0.006)], 0.0002)
        clic += filtre(bruit(len(clic), 40 + k), bas=3000) * np.exp(-temps(0.08) / 0.002) * 0.5
        onde[d:d + len(clic)] += clic * (1.4 if k == 6 else 0.6)
    return reverb(onde, 1.0, 0.2)


def interrupteur(double=True):
    """Clic de la lampe torche (ou d'un bouton)."""
    t = temps(0.12)
    clic = partiels(2400, 0.12, [(1, 1, 0.006), (1.8, 0.5, 0.004)], 0.0002) + filtre(bruit(len(t), 50), bas=1500) * np.exp(-t / 0.002)
    if double:
        clic[int(R * 0.05):] += clic[:len(t) - int(R * 0.05)] * 0.6
    return clic


def coeur():
    """Battement de cœur : « poum-poum » grave."""
    t = temps(0.6)

    def coup(f, d):
        return np.sin(2 * np.pi * np.cumsum(f * (1 + 0.5 * np.exp(-t / 0.02))) / R) * np.exp(-t / d) * (1 - np.exp(-t / 0.004))
    onde = coup(66, 0.07)
    onde[int(R * 0.17):] += 0.7 * coup(58, 0.08)[:len(t) - int(R * 0.17)]
    return filtre(onde, haut=320)


def radio():
    """Grésillement de talkie-walkie : déclic, voix nasillarde, souffle."""
    duree = 1.5
    h = random.Random(7)
    syllabes, instant = [], 0.15
    while instant < duree - 0.3:
        d = h.uniform(0.08, 0.2)
        syllabes.append((instant, instant + d, h.choice("aeiouéa")))
        instant += d + h.choice([0.0, 0.0, 0.03, 0.15])
    parole = voix(duree, lambda t: 150 + 25 * np.sin(2 * np.pi * 1.7 * t), syllabes, 0.2, 3)
    parole = np.tanh(filtre(parole, bas=500, haut=2800) * 6) * 0.5
    t = temps(duree)
    souffle = filtre(bruit(len(t), 60), bas=800, haut=5000) * 0.12
    onde = parole + souffle
    onde[:int(R * 0.02)] += interrupteur(False)[:int(R * 0.02)]
    fin = int(R * (duree - 0.12))
    onde[fin:] += filtre(bruit(len(t) - fin, 61), bas=1000) * 0.6  # « kshht » en relâchant le bouton
    return onde * np.clip((duree - t) / 0.02, 0, 1)


def voix_sphinx():
    """Le Sphinx parle : une voix d'outre-tombe, très grave, qui fait vibrer la crypte."""
    duree = 3.2
    syllabes = [(0.1, 0.9, "m"), (0.9, 1.7, "o"), (1.8, 2.3, "a"), (2.35, 3.1, "u")]
    parole = voix(duree, lambda t: 62 + 6 * np.sin(2 * np.pi * 0.8 * t) - 8 * t / duree, syllabes, 0.05, 9)
    t = temps(duree)
    return reverb(filtre(parole, haut=2500) * 3 + 0.6 * np.sin(2 * np.pi * 55 * t) * np.clip(t / 0.5, 0, 1) * np.clip((duree - t) / 0.4, 0, 1),
                  3.0, 0.45, clair=2500)


# ---------------------------------------------------------------------------
# Musiques (boucles) et ambiances
# ---------------------------------------------------------------------------


def musique_menu():
    """Piano seul, à trois temps, dans l'esprit des Gymnopédies : ré majeur, tendre et un peu nostalgique."""
    temps_s = 60 / 66
    accords = [(43, (59, 62, 66)), (38, (57, 61, 66)), (43, (59, 62, 66)), (38, (57, 61, 66)), (40, (55, 59, 62)),
               (42, (57, 61, 64)), (35, (57, 62, 66)), (33, (55, 61, 64)), (43, (59, 62, 66)), (42, (57, 62, 66)),
               (40, (55, 59, 62)), (33, (57, 62, 64))]
    melodie = [[(1, 78, 2)], [(0, 81, 1), (1, 78, 1), (2, 76, 1)], [(0, 74, 2), (2, 71, 1)], [(0, 73, 1), (1, 74, 1), (2, 69, 1)],
               [(0, 71, 1.5), (1.5, 74, 0.5), (2, 76, 1)], [(0, 73, 2), (2, 69, 1)], [(0, 74, 1), (1, 78, 1), (2, 81, 1)],
               [(0, 79, 1.5), (1.5, 76, 1.5)], [(0, 78, 3)], [(0, 81, 1), (1, 83, 1), (2, 81, 1)], [(0, 79, 1), (1, 78, 1), (2, 76, 1)],
               [(0, 74, 1.5), (1.5, 73, 1.5)]]
    p = piste(len(accords) * 3 * temps_s)
    h = random.Random(1)
    cache = {}

    def note(m, duree, force):
        cle = (m, round(duree, 1), round(force, 1))
        if cle not in cache:
            cache[cle] = piano(midi(m), duree, force)
        return cache[cle]
    for mesure, (basse, accord) in enumerate(accords):
        debut = mesure * 3 * temps_s
        poser(p, debut, note(basse, 3.2, 0.6), 0.9, -0.3)
        for k, m in enumerate(accord):
            poser(p, debut + temps_s + k * 0.018, note(m, 2.2, 0.4), 0.45, -0.1 + 0.1 * k)
        for battement, m, duree in melodie[mesure]:
            poser(p, debut + battement * temps_s + h.uniform(-0.01, 0.01), note(m, duree * temps_s + 1.2, 0.7), 0.75, 0.2)
    return reverb(p, 2.6, 0.4, boucle=True)


def musique_enquete():
    """Enquête nocturne : pizzicati en ré mineur, nappe de cordes grave, quelques notes de célesta."""
    temps_s = 60 / 84
    grille = [(50, 53, 57), (50, 53, 57), (46, 50, 53), (46, 50, 53), (43, 46, 50), (43, 46, 50), (45, 49, 52), (45, 49, 52)]
    p = piste(len(grille) * 4 * temps_s)
    for mesure, (a, b, c) in enumerate(grille):
        debut = mesure * 4 * temps_s
        if mesure % 2 == 0:
            for m in (a - 12, a, b):
                poser(p, debut, cordes(midi(m), 8 * temps_s - 0.3, 1.2, 1.0, 0.5), 0.2)
        motif = (a + 12, c, b + 12, c, a + 12, c, b + 12, c + 12)
        for k, m in enumerate(motif):
            poser(p, debut + k * temps_s / 2, pince(midi(m), 0.9, 0.35, k), 0.5 if k % 4 == 0 else 0.3, (-0.4, 0.4)[k % 2])
    for mesure, battement, m in ((1, 2, 81), (3, 1, 86), (5, 2.5, 82), (7, 0, 85), (7, 2, 88)):
        poser(p, (mesure * 4 + battement) * temps_s, cloche(midi(m), 2.0), 0.12, 0.3)
    return reverb(p, 2.4, 0.35, boucle=True)


def musique_poursuite():
    """Poursuite : batterie à 150, basse qui galope en mi mineur, cordes haletantes, coups de cuivres."""
    temps_s = 60 / 150
    grille = [40, 40, 36, 38, 40, 40, 36, 35]
    p = piste(len(grille) * 4 * temps_s)
    gc, cc = grosse_caisse(), caisse_claire()
    for mesure, racine in enumerate(grille):
        debut = mesure * 4 * temps_s
        for b in (0, 1.5, 2.5) if mesure != 7 else (0, 1.5, 2.5, 3.25, 3.5, 3.75):
            poser(p, debut + b * temps_s, gc, 0.8)
        for b in (1, 3):
            poser(p, debut + b * temps_s, cc, 0.5, 0.1)
        for k in range(8):
            poser(p, debut + k * temps_s / 2, charleston(graine=k), 0.35 if k % 2 else 0.2, 0.4)
        for k, ecart in enumerate((0, 0, 12, 0, 10, 0, 7, 12)):
            f = midi(racine + ecart)
            t = temps(temps_s / 2)
            basse = filtre(scie(f * t, 12) * np.exp(-t / 0.15), haut=900)
            poser(p, debut + k * temps_s / 2, basse, 0.35)
        for k in range(16):
            m = racine + 36 + (0, 7, 3, 7)[k % 4] + (0 if racine != 35 else 1)
            poser(p, debut + k * temps_s / 4, cordes(midi(m), 0.07, 0.01, 0.05), 0.12, -0.3)
        if mesure in (0, 4):
            for m in (racine + 12, racine + 19, racine + 24):
                poser(p, debut, cuivre(midi(m), 0.5), 0.3, 0.2)
    return reverb(p, 1.6, 0.25, boucle=True)


def musique_lasers():
    """Labyrinthe laser : arpèges électroniques en la mineur, battement sourd, éclairs de laser."""
    temps_s = 60 / 112
    grille = [(57, 60, 64), (57, 60, 64), (53, 57, 60), (53, 57, 60), (48, 52, 55), (48, 52, 55), (55, 59, 62), (55, 59, 62)]
    p = piste(len(grille) * 4 * temps_s)
    gc = grosse_caisse(0.4)
    for mesure, (a, b, c) in enumerate(grille):
        debut = mesure * 4 * temps_s
        for k, m in enumerate((a, b, c, a + 12, c, b, a + 12, c + 12) * 2):
            t = temps(temps_s / 4 + 0.05)
            f = midi(m)
            onde = sum(np.sin(2 * np.pi * f * j * t) / j * np.exp(-t * j * 9) for j in (1, 3, 5, 7))  # onde carrée qui s'assourdit
            poser(p, debut + k * temps_s / 4, onde * np.clip((len(t) / R - t) / 0.01, 0, 1), 0.2, (-0.5, 0.5)[k % 2])
        for b in range(4):
            poser(p, debut + b * temps_s, gc, 0.4)
            poser(p, debut + (b + 0.5) * temps_s, charleston(0.05, b), 0.2, 0.3)
        if mesure % 2 == 0:
            for m in (a - 12, a, b):
                poser(p, debut, cordes(midi(m), 8 * temps_s - 0.3, 0.8, 0.8, 0.4), 0.13)
        if mesure in (3, 7):
            t = temps(0.4)
            eclair = np.sin(2 * np.pi * np.cumsum(2400 * np.exp(-t / 0.08) + 180) / R) * np.exp(-t / 0.12)
            poser(p, debut + 3.5 * temps_s, eclair, 0.12, 0.6)
    return reverb(p, 1.8, 0.3, boucle=True)


def musique_sphinx():
    """La crypte : bourdon de ré, harpe en mode oriental (ré, mi bémol, fa dièse...), tambour sur cadre."""
    temps_s = 60 / 96
    mesures = 8
    p = piste(mesures * 4 * temps_s)
    duree = len(p) / R
    t = temps(duree)
    houle = 0.7 + 0.3 * np.sin(2 * np.pi * t / duree * 2)
    for m in (38, 45, 50):
        f = round(midi(m) * duree) / duree  # un nombre entier de périodes : la boucle ne claque pas
        poser(p, 0, scie(f * t, 8) * houle * 0.08, 0.5)
    doum, tek = tambour_sur_cadre(True), tambour_sur_cadre(False)
    for mesure in range(mesures):
        debut = mesure * 4 * temps_s
        for b in (0, 1.5):
            poser(p, debut + b * temps_s, doum, 0.7)
        for b in (1, 2.5, 3):
            poser(p, debut + b * temps_s, tek, 0.3, 0.3)
    phrase = [(0, 74), (1, 75), (2, 78), (3, 79), (4, 78), (5, 75), (6, 74), (8, 81), (9, 79), (10, 78), (11, 75),
              (12, 74), (16, 79), (17, 81), (18, 82), (19, 81), (20, 79), (20.5, 78), (21, 75), (22, 74), (24, 72),
              (25, 74), (26, 75), (27, 78), (28, 74)]
    for k, (b, m) in enumerate(phrase):
        poser(p, b * temps_s, pince(midi(m), 1.6, 0.8, k), 0.45, -0.2)
        poser(p, b * temps_s + 0.01, pince(midi(m - 12), 1.2, 0.5, k + 50), 0.15, 0.3)
    return reverb(p, 3.0, 0.4, boucle=True, clair=3500)


def musique_infiltration():
    """Infiltration : pouls grave, cordes aiguës qui tremblent, notes de piano isolées, horloge."""
    temps_s = 60 / 72
    mesures = 8
    p = piste(mesures * 4 * temps_s)
    duree = len(p) / R
    t = temps(duree)
    for m, pan in ((79, -0.4), (80, 0.4)):  # deux notes aiguës à un demi-ton : la tension
        f = round(midi(m) * duree) / duree
        tremolo = 0.6 + 0.4 * np.sin(2 * np.pi * round(7 * duree) / duree * t)
        poser(p, 0, np.sin(2 * np.pi * f * t) * tremolo * (0.5 + 0.5 * np.sin(2 * np.pi * t / duree * 2 + pan)) * 0.05, 1, pan)
    battement = coeur()
    for mesure in range(mesures):
        debut = mesure * 4 * temps_s
        for b in (0, 2):
            poser(p, debut + b * temps_s, battement, 0.8)
        for b in range(4):
            poser(p, debut + b * temps_s, bloc_de_bois(1300 if b % 2 else 1000), 0.06, 0.5)
        if mesure % 2 == 0:
            poser(p, debut + 0.02, piano(midi((48, 51, 43, 44)[mesure // 2]), 5.0, 0.5), 0.5, -0.2)
        else:
            poser(p, debut + 2 * temps_s, pince(midi(55), 1.0, 0.4, mesure), 0.25, 0.2)
            poser(p, debut + 2.5 * temps_s, pince(midi(56), 1.0, 0.4, mesure + 9), 0.25, 0.2)
    return reverb(p, 2.8, 0.4, boucle=True)


def boucle_bruit(duree, graine, gain_f):
    """Bruit dont le spectre est `gain_f(f)`, qui boucle parfaitement (fabriqué directement en fréquences)."""
    n = int(R * duree)
    f = np.fft.rfftfreq(n, 1 / R)
    h = np.random.default_rng(graine)
    spectre = (h.standard_normal((len(f), 2)) + 1j * h.standard_normal((len(f), 2))) * gain_f(np.maximum(f, 1))[:, None]
    onde = np.fft.irfft(spectre, n, axis=0)
    return onde / (np.abs(onde).max() + 1e-9)


def evenements(duree, nombre, son, graine, gain=(0.3, 1.0)):
    """Petits sons semés au hasard dans une boucle (gouttes, crépitements, craquements)."""
    p = piste(duree)
    h = random.Random(graine)
    for _ in range(nombre):
        poser(p, h.uniform(0, duree), son(h), h.uniform(*gain), h.uniform(-0.9, 0.9))
    return p


def ambiance_nuit():
    """Musée fermé : souffle grave de la ventilation, très loin un bourdonnement électrique."""
    duree = 16.0
    air = boucle_bruit(duree, 70, lambda f: 1 / (1 + (f / 300) ** 2) / (1 + (70 / f) ** 4) / np.sqrt(f)) * 0.5
    t = temps(duree)[:, None]
    return air + 0.015 * np.sin(2 * np.pi * 100 * t) + 0.008 * np.sin(2 * np.pi * 200 * t)


def ambiance_pluie():
    """La pluie sur la verrière : un ruissellement doux et des milliers de gouttes."""
    duree = 16.0
    nappe = boucle_bruit(duree, 71, lambda f: 1 / (1 + (f / 5000) ** 2) / (1 + (600 / f) ** 2)) * 0.35

    def goutte(h):
        t = temps(0.03)
        return np.sin(2 * np.pi * h.uniform(2500, 6000) * t) * np.exp(-t / 0.004)
    gouttes = evenements(duree, 900, goutte, 72, (0.05, 0.25))
    grave = boucle_bruit(duree, 73, lambda f: 1 / (1 + (f / 120) ** 2)) * 0.25
    return reverb(nappe + gouttes + grave, 1.2, 0.3, boucle=True)


def ambiance_crypte():
    """La crypte : vent dans les couloirs, feu des braseros qui crépite, gouttes d'eau qui résonnent."""
    duree = 18.0
    t = temps(duree)[:, None]
    vent = boucle_bruit(duree, 80, lambda f: np.exp(-((np.log(f) - np.log(350)) ** 2) / 0.5) / np.sqrt(f))
    vent *= 0.55 + 0.45 * np.sin(2 * np.pi * t * 3 / duree + np.array((0, 1.3)))

    def crepitement(h):
        tt = temps(0.02)
        return filtre(bruit(len(tt), h.randrange(999)), bas=1200) * np.exp(-tt / 0.003)
    feu = evenements(duree, 260, crepitement, 81, (0.05, 0.4)) + boucle_bruit(duree, 82, lambda f: 1 / (1 + (f / 400) ** 2)) * 0.1

    def goutte(h):
        tt = temps(0.12)
        return np.sin(2 * np.pi * np.cumsum(h.uniform(900, 1400) * (1 + 0.8 * tt / 0.12)) / R) * np.exp(-tt / 0.03)
    gouttes = evenements(duree, 9, goutte, 83, (0.2, 0.45))
    return reverb(vent * 0.6 + feu + gouttes, 2.8, 0.45, boucle=True)


def ambiance_foule():
    """Visiteurs : le murmure d'une foule qui parle bas, dans une grande salle qui résonne."""
    duree = 18.0
    p = piste(duree)
    h = random.Random(90)
    for k in range(11):
        syllabes, instant = [], 0.3
        while instant < duree - 1.0:  # des phrases, puis des silences
            fin_phrase = min(duree - 1.0, instant + h.uniform(1.2, 4.0))
            while instant < fin_phrase:
                d = h.uniform(0.09, 0.24)
                syllabes.append((instant, instant + d, h.choice("aeiouéa")))
                instant += d + h.choice([0, 0, 0.02, 0.06])
            instant += h.uniform(0.4, 2.0)
        base = h.choice([105, 120, 135, 190, 210, 230])
        phase_i = h.uniform(0, 6)
        parole = voix(duree, lambda t, b=base, ph=phase_i: b * (1 + 0.1 * np.sin(2 * np.pi * 0.9 * t + ph)
                                                                 + 0.05 * np.sin(2 * np.pi * 3.1 * t)), syllabes, 0.25, k)
        loin = h.uniform(0.3, 1.0)
        parole = filtre(parole, bas=150, haut=1200 + 2000 * loin)
        poser(p, h.uniform(0, duree), parole / (np.abs(parole).max() + 1e-9), 0.25 * loin, h.uniform(-0.8, 0.8))
    brouhaha = boucle_bruit(duree, 91, lambda f: np.exp(-((np.log(f) - np.log(500)) ** 2) / 0.6)) * 0.12
    return reverb(p + brouhaha, 2.6, 0.55, boucle=True, clair=3000)


MUSIQUES = {"menu": musique_menu, "enquete": musique_enquete, "poursuite": musique_poursuite, "lasers": musique_lasers,
            "sphinx": musique_sphinx, "infiltration": musique_infiltration}
AMBIANCES = {"nuit": ambiance_nuit, "pluie": ambiance_pluie, "crypte": ambiance_crypte, "foule": ambiance_foule}


def laser_bourdon():
    """Le bourdonnement électrique des lasers (boucle de 2 s)."""
    t = temps(2.0)
    onde = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((100, 1), (200, 0.5), (300, 0.35), (400, 0.2), (1000, 0.05)))
    onde *= 0.8 + 0.2 * np.sin(2 * np.pi * 7 * t)
    return onde * 0.3 + boucle_bruit(2.0, 99, lambda f: np.exp(-((f - 7000) / 800) ** 2))[:, 0] * 0.03


# ---------------------------------------------------------------------------
# Le lecteur
# ---------------------------------------------------------------------------


def suite(notes, instrument):
    """Quelques notes à la suite : [(début, note midi), ...]."""
    return melanger(*(np.concatenate([np.zeros(int(R * d)), instrument(m)]) for d, m in notes))


def etincelles():
    t = temps(1.2)
    return filtre(bruit(len(t), 44), bas=6000) * np.exp(-t / 0.3) * (0.5 + 0.5 * np.sin(2 * np.pi * 17 * t)) * 0.15


def detecteur(f):
    """Le « ping » du détecteur de joyaux, comme un sonar."""
    t = temps(0.5)
    return reverb(partiels(f, 0.5, [(1, 1, 0.12), (2.0, 0.15, 0.05), (3.01, 0.08, 0.03)], 0.003) * (1 + 0.3 * np.exp(-t / 0.01)), 1.2, 0.35)


def fanfare():
    """Victoire : appel de cuivres (do, mi, sol... do !), roulement de timbales et cymbale."""
    p = piste(3.6)
    for d, notes, duree in ((0.0, (60, 64), 0.16), (0.2, (64, 67), 0.16), (0.4, (67, 72), 0.16), (0.6, (60, 64, 67, 72), 1.8)):
        for m in notes:
            poser(p, d, cuivre(midi(m), duree), 0.35, (m - 66) / 12)
    for d in np.arange(0.6, 1.1, 0.06):
        poser(p, d, tambour_sur_cadre(True, 0.5) * 0.4, 0.5)
    poser(p, 0.6, grosse_caisse(1.0), 0.6)
    t = temps(2.5)
    poser(p, 0.6, filtre(bruit(len(t), 45), bas=5000) * np.exp(-t / 0.6) * 0.4, 0.5, 0.3)
    return reverb(p, 2.4, 0.35)


def complainte():
    """Échec : cordes graves qui descendent en ré mineur, coup sourd."""
    p = piste(4.0)
    for d, notes in ((0.0, (50, 53, 57)), (0.9, (49, 52, 57)), (1.8, (46, 50, 53))):
        for m in notes:
            poser(p, d, cordes(midi(m), 0.8 if d < 1.8 else 1.6, 0.1, 0.5, 0.6), 0.4)
    poser(p, 1.8, grosse_caisse(1.5) * 0.8, 0.7)
    poser(p, 1.8, piano(midi(38), 2.0, 0.6), 0.6)
    return reverb(p, 2.4, 0.35)


def coupure():
    """Le courant se coupe : le bourdonnement descend et s'éteint, avec un clac."""
    t = temps(1.2)
    f = 120 * np.exp(-t / 0.4) + 25
    onde = sum(np.sin(2 * np.pi * k * np.cumsum(f) / R) / k for k in (1, 2, 3, 5)) * np.exp(-t / 0.35) * 0.5
    onde[:int(R * 0.12)] += interrupteur(False)
    return reverb(onde, 1.5, 0.3)


def note_sphinx(m, k):
    """Les quatre notes du Sphinx : une harpe dans la crypte."""
    return reverb(melanger(pince(midi(m), 2.0, 0.85, k), 0.4 * pince(midi(m + 12), 1.5, 0.9, k + 9)), 2.5, 0.4)


EFFETS = {  # nom : (fabrique -> liste de variantes, volume). Dans l'ordre de fabrication (les plus utiles d'abord).
    "click": (lambda: [reverb(interrupteur(False) * 0.6, 0.5, 0.1)], 0.25),
    "lampe": (lambda: [interrupteur(True)], 0.4),
    "tick": (lambda: [reverb(bloc_de_bois(1200), 0.8, 0.2), reverb(bloc_de_bois(950), 0.8, 0.2)], 0.45),
    "musique:menu": (musique_menu, 1.0),
    **{f"pas_{sol}": (lambda sol=sol: [pas(sol, k) for k in range(6)], 0.5) for sol in ("parquet", "marbre", "pierre")},
    **{f"atterrir_{sol}": (lambda sol=sol: [atterrissage(sol)], 0.6) for sol in ("parquet", "marbre", "pierre")},
    "saut": (lambda: [filtre(bruit(int(R * 0.18), 30), bas=400, haut=2500) * np.sin(np.pi * temps(0.18) / 0.18) ** 2], 0.25),
    "sonar_loin": (lambda: [detecteur(740)], 0.35), "sonar_moyen": (lambda: [detecteur(990)], 0.35),
    "sonar_proche": (lambda: [detecteur(1320)], 0.4),
    "joyau": (lambda: [reverb(melanger(suite([(0.0, 88), (0.07, 92), (0.14, 95), (0.21, 100)], lambda m: verre(midi(m))),
                                       etincelles()), 2.0, 0.4)], 0.55),
    "loupe": (lambda: [reverb(suite([(0, 79), (0.1, 86)], lambda m: marimba(midi(m))), 1.4, 0.3)], 0.5),
    "erreur": (lambda: [reverb(suite([(0, 51), (0.14, 48)], lambda m: marimba(midi(m), 0.6)), 1.2, 0.25)], 0.6),
    "victoire": (lambda: [fanfare()], 0.6), "echec": (lambda: [complainte()], 0.55),
    "alarme": (lambda: [sonnerie()], 0.4), "sifflet": (lambda: [sifflet()], 0.45),
    "grondement": (lambda: [grondement()], 0.8), "tiroir": (lambda: [raclement()], 0.7),
    "fracas": (lambda: [fracas()], 0.6), "menottes": (lambda: [menottes()], 0.6), "coupure": (lambda: [coupure()], 0.5),
    "coeur": (lambda: [coeur()], 0.8), "radio": (lambda: [radio()], 0.5), "sphinx_voix": (lambda: [voix_sphinx()], 0.8),
    **{f"note{k}": (lambda k=k, m=m: [note_sphinx(m, k)], 0.6) for k, m in enumerate((62, 65, 67, 69))},
    "boucle:lasers": (laser_bourdon, 0.5),
    **{f"ambiance:{nom}": (f, 0.5) for nom, f in AMBIANCES.items()},
    **{f"musique:{nom}": (f, 1.0) for nom, f in MUSIQUES.items() if nom != "menu"},
}


class Audio:
    """Joue les sons. Tout est calculé par un fil d'exécution en arrière-plan (quelques secondes) : le jeu démarre
    tout de suite, et un son pas encore prêt est simplement sauté (une musique démarre dès qu'elle est prête).
    Canaux réservés : 0 et 1 pour la musique (fondu enchaîné), 2 pour l'ambiance, 3 pour une boucle d'effet."""

    def __init__(self, volume, musique):
        global R
        self.sounds, self.pretes = {}, {}
        self.volume, self.musique = volume, musique
        self.morceau = self.voulu = self.ambiance_nom = self.ambiance_voulue = None
        self.canaux_musique = self.canal_ambiance = self.canal_boucle = None
        self.sol, self.pied, self.courant = "parquet", 0, 0
        if not pygame.mixer.get_init():
            print("Pas de son disponible : le jeu continue sans audio.")
            return
        R = pygame.mixer.get_init()[0]
        pygame.mixer.set_num_channels(32)
        pygame.mixer.set_reserved(4)
        self.canaux_musique = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
        self.canal_ambiance, self.canal_boucle = pygame.mixer.Channel(2), pygame.mixer.Channel(3)
        self.fil = threading.Thread(target=self.preparer, daemon=True)
        self.fil.start()

    def preparer(self):
        for nom, (fabrique, _) in EFFETS.items():
            ondes = fabrique()
            self.pretes[nom] = [self.convertir(o) for o in (ondes if isinstance(ondes, list) else [ondes])]

    @staticmethod
    def convertir(onde):
        """Onde -> tableau 16 bits stéréo : sans infra-basses (inaudibles, elles font distordre les haut-parleurs)
        ni composante continue, et avec de la marge sous la saturation."""
        onde = filtre(stereo(np.asarray(onde, float)), bas=45)
        return np.ascontiguousarray(normaliser(onde, CRETE) * 32767).astype(np.int16)

    def attendre(self):
        """Attend la fin de la préparation (pour les tests)."""
        if self.canaux_musique:
            self.fil.join()

    def _sons(self, nom):
        """Les variantes d'un son, converties pour pygame à la première utilisation (None si pas encore prêt)."""
        if nom not in self.sounds and nom in self.pretes:
            self.sounds[nom] = [pygame.sndarray.make_sound(onde) for onde in self.pretes.pop(nom)]
            self._regler(nom)
        return self.sounds.get(nom)

    def _regler(self, nom):
        for son in self.sounds[nom]:
            son.set_volume(self.volume * EFFETS[nom][1] if ":" not in nom or nom.startswith("boucle") else 1.0)

    def set_volume(self, volume, musique=None):
        self.volume = volume
        if musique is not None:
            self.musique = musique
        for nom in self.sounds:
            self._regler(nom)
        if self.canaux_musique:
            self.canaux_musique[self.courant].set_volume(self.volume * self.musique * 0.6)
            self.canal_ambiance.set_volume(self.volume * 0.4)

    def update(self):
        """À chaque image : démarre la musique ou l'ambiance demandée dès qu'elle est prête."""
        if not self.canaux_musique:
            return
        if self.voulu != self.morceau and (self.voulu is None or self._sons("musique:" + self.voulu)):
            self.morceau = self.voulu
            self.canaux_musique[self.courant].fadeout(1500)
            self.courant = 1 - self.courant
            if self.voulu:
                canal = self.canaux_musique[self.courant]
                canal.set_volume(self.volume * self.musique * 0.6)
                canal.play(self.sounds["musique:" + self.voulu][0], loops=-1, fade_ms=2000)
        if self.ambiance_voulue != self.ambiance_nom and (self.ambiance_voulue is None or self._sons("ambiance:" + self.ambiance_voulue)):
            self.ambiance_nom = self.ambiance_voulue
            if self.ambiance_nom:
                self.canal_ambiance.set_volume(self.volume * 0.4)
                self.canal_ambiance.play(self.sounds["ambiance:" + self.ambiance_nom][0], loops=-1, fade_ms=1500)
            else:
                self.canal_ambiance.fadeout(800)

    def music(self, morceau):
        """Change de musique en fondu enchaîné : "menu", "enquete", "poursuite", "lasers", "sphinx",
        "infiltration", ou None pour le silence."""
        self.voulu = morceau
        self.update()

    def ambiance(self, nom):
        """Fond sonore : "nuit", "pluie", "crypte", "foule" ou None."""
        self.ambiance_voulue = nom
        self.update()

    def play(self, nom, gauche=1.0, droite=None):
        """Joue un son (une variante au hasard). Le volume du canal est réglé avant de jouer : sinon le début
        du son part avec le volume et la position gauche/droite du son précédent sur ce canal."""
        sons = self._sons(nom) if self.canaux_musique else None
        canal = pygame.mixer.find_channel() if sons else None
        if canal:
            canal.set_volume(min(1.0, gauche), min(1.0, gauche if droite is None else droite))
            canal.play(random.choice(sons))
        return canal

    def pas(self, sol, force=1.0):
        """Un pas du joueur : sol "parquet", "marbre" ou "pierre" ; force 0.3 (accroupi) à 1.3 (course)."""
        self.pied = 1 - self.pied
        cote = 0.15 if self.pied else -0.15
        self.play("pas_" + sol, force * (1 - cote), force * (1 + cote))

    def spatial(self, nom, position, ecoute, lacet, portee=14.0):
        """Son placé dans l'espace : plus faible au loin, plus fort dans l'oreille du bon côté.
        "pas" prend le bruit de pas du sol de la salle ; "pas_visiteur" est plus léger."""
        doux = nom == "pas_visiteur"
        if nom in ("pas", "pas_visiteur"):
            nom = "pas_" + self.sol
        dx, dz = position[0] - ecoute[0], position[2] - ecoute[2]
        distance = math.hypot(dx, dz)
        if distance > portee:
            return
        volume = (1 - distance / portee) ** 1.5 * (0.35 if doux else 1.0)
        a = math.radians(lacet)
        cote = (dx * -math.sin(a) + dz * math.cos(a)) / (distance or 1.0)  # > 0 : à droite
        self.play(nom, volume * min(1.0, 1 - cote), volume * min(1.0, 1 + cote))

    def boucle(self, nom, volume):
        """Boucle d'effet dont on règle le volume à chaque image (bourdonnement des lasers) ; 0 l'arrête."""
        if not self.canal_boucle:
            return
        if volume <= 0.01:
            self.canal_boucle.stop()
            return
        sons = self._sons("boucle:" + nom)
        self.canal_boucle.set_volume(min(1.0, volume))
        if sons and not self.canal_boucle.get_busy():
            self.canal_boucle.play(sons[0], loops=-1)
