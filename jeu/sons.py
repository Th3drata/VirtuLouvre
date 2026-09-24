"""Sons et musique, tous fabriqués avec NumPy (sauf les bruits de pas du joueur).
Sans carte son (machine virtuelle, serveur...), le jeu tourne quand même, en silence."""

import math

import numpy as np
import pygame

from .base import chemin


class Audio:
    def __init__(self, volume, musique):
        self.sounds, self.musiques = {}, {}
        self.walk = self.channel = self.music_channel = None
        self.volume, self.musique, self.morceau = volume, musique, None
        if not pygame.mixer.get_init():
            print("Pas de son disponible : le jeu continue sans audio.")
            return
        self.rate = pygame.mixer.get_init()[0]
        pygame.mixer.set_num_channels(24)
        pygame.mixer.set_reserved(2)  # canal 0 : pas du joueur ; canal 1 : musique
        self.channel, self.music_channel = pygame.mixer.Channel(0), pygame.mixer.Channel(1)
        notes = self.notes
        self.sounds = {  # nom : (son, volume relatif)
            "beep_near": (notes([1480], 0.07, 25), 0.35),
            "beep_mid": (notes([1175], 0.07, 25), 0.3),
            "beep_far": (notes([880], 0.07, 25), 0.25),
            "pickup": (notes([1047, 1319, 1568, 2093], 0.09, 9), 0.5),
            "win": (notes([523, 659, 784, 1047, 784, 1047, 1319], 0.13, 5), 0.5),
            "lose": (notes([392, 349, 294, 196], 0.24, 4), 0.5),
            "tick": (notes([1250], 0.035, 30), 0.3),
            "click": (notes([720], 0.03, 40), 0.25),
            "loupe": (notes([880, 1320], 0.12, 8), 0.4),
            "erreur": (self.son(self.carre(140, 0.35) * 0.4), 0.4),
            "alarme": (self.son(np.concatenate([self.carre(f, 0.22) for f in (880, 660) * 3]) * 0.35), 0.45),
            "sifflet": (self.son(self.sifflet()), 0.4),
            "grondement": (self.son(self.bruit_filtre(1.4, 90) * np.exp(-np.linspace(0, 3, int(self.rate * 1.4))) * 2.5), 0.7),
            "tiroir": (self.son(self.bruit_filtre(1.6, 400) * np.sin(np.linspace(0, math.pi, int(self.rate * 1.6))) * 1.5), 0.5),
            "pas": (self.son(self.bruit_filtre(0.09, 250) * np.exp(-np.linspace(0, 6, int(self.rate * 0.09))) * 3), 0.6),
            "arrestation": (notes([392, 523, 659, 784, 1047], 0.1, 6), 0.5),
        }
        for k, f in enumerate((293.7, 349.2, 392.0, 440.0)):  # les quatre notes du Sphinx
            self.sounds[f"note{k}"] = (self.cloche(f, 0.7), 0.5)
        try:
            self.walk = pygame.mixer.Sound(chemin("src", "media", "walk.mp3"))
        except pygame.error as erreur:
            print("Bruits de pas indisponibles :", erreur)
        self.musiques = {"menu": self.son(self.creer_musique()), "mission": self.son(self.creer_ambiance())}
        self.set_volume(volume, musique)

    # --- Fabrication des sons ---

    def son(self, onde):
        onde = (np.clip(onde, -1, 1) * 32767 * 0.8).astype(np.int16)
        return pygame.sndarray.make_sound(np.ascontiguousarray(np.column_stack([onde, onde])))

    def notes(self, hauteurs, duree, amortissement=6.0):
        t = np.arange(int(self.rate * duree)) / self.rate
        enveloppe = np.exp(-amortissement * t) * (1 - np.exp(-t * 400))  # attaque douce, puis extinction
        return self.son(np.concatenate([np.sin(2 * np.pi * f * t) * enveloppe for f in hauteurs]))

    def cloche(self, f, duree):
        t = np.arange(int(self.rate * duree)) / self.rate
        onde = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-6 * t)
        return self.son(onde * np.exp(-3.5 * t) * (1 - np.exp(-t * 300)) * 0.7)

    def carre(self, f, duree):
        t = np.arange(int(self.rate * duree)) / self.rate
        return np.sign(np.sin(2 * np.pi * f * t)) * 0.6 * (1 - np.exp(-t * 200)) * np.exp(-t * 0.5)

    def sifflet(self):
        t = np.arange(int(self.rate * 0.6)) / self.rate
        f = 2600 + 120 * np.sin(2 * np.pi * 28 * t)  # roulement de la bille du sifflet
        return np.sin(2 * np.pi * np.cumsum(f) / self.rate) * np.clip(t * 30, 0, 1) * np.clip((0.6 - t) * 12, 0, 1) * 0.5

    def bruit_filtre(self, duree, coupure, graine=0):
        """Bruit blanc dont on garde les fréquences graves (filtre dans le domaine de Fourier)."""
        n = int(self.rate * duree)
        spectre = np.fft.rfft(np.random.default_rng(graine).normal(size=n))
        spectre[np.fft.rfftfreq(n, 1 / self.rate) > coupure] = 0
        onde = np.fft.irfft(spectre, n)
        return onde / (np.abs(onde).max() + 1e-9)

    def boucle(self, duree, voix):
        """Onde de `duree` secondes qui boucle sans raccord : les fréquences sont arrondies pour faire
        un nombre entier de périodes, et l'écho est calculé « en boucle » (convolution circulaire)."""
        n = int(self.rate * duree)
        t = np.arange(n) / self.rate
        onde = voix(t, lambda f: round(f * duree) / duree)
        echo = np.random.default_rng(4).normal(size=n) * np.exp(-t / 0.9)
        echo[int(self.rate * 2):] = 0
        onde = onde + 0.35 * np.fft.irfft(np.fft.rfft(onde) * np.fft.rfft(echo), n) / 40
        return onde / (np.abs(onde).max() + 1e-9) * 0.55

    def creer_musique(self):
        """Nappe calme pour le menu : quatre accords (la mineur, fa, do, sol) et quelques notes de cloche."""
        accords = [(220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (130.8, 196.0, 329.6), (196.0, 246.9, 293.7)]

        def voix(t, juste):
            onde = np.zeros_like(t)
            for k, accord in enumerate(accords):
                d = (t - k * 4.0) % 16.0  # temps depuis le début de l'accord (en boucle)
                enveloppe = np.clip(d / 1.5, 0, 1) * np.clip((5.2 - d) / 1.5, 0, 1)
                for f in accord + (accord[0] / 2,):
                    f = juste(f)
                    onde += enveloppe * (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * juste(f * 1.004) * t)
                                         + 0.15 * np.sin(4 * np.pi * f * t))
                for pas, note in enumerate((accord[2] * 2, accord[1] * 2, accord[0] * 4)):
                    d2 = (t - k * 4.0 - pas * 1.3 - 0.4) % 16.0
                    onde += 0.8 * np.sin(2 * np.pi * juste(note) * t) * np.exp(-d2 * 1.8) * (d2 < 3.5)
            return onde

        return self.boucle(16.0, voix)

    def creer_ambiance(self):
        """Bourdon sombre pour les missions : notes graves qui respirent et souffle d'air."""
        def voix(t, juste):
            respiration = 0.6 + 0.4 * np.sin(2 * np.pi * t / 12.0)
            onde = respiration * (np.sin(2 * np.pi * juste(55) * t) + 0.6 * np.sin(2 * np.pi * juste(82.5) * t)
                                  + 0.25 * np.sin(2 * np.pi * juste(110.2) * t))
            spectre = np.fft.rfft(np.random.default_rng(9).normal(size=len(t)))
            frequences = np.fft.rfftfreq(len(t), 1 / self.rate)
            spectre[(frequences < 150) | (frequences > 700)] = 0
            souffle = np.fft.irfft(spectre, len(t))
            return onde + 2.0 * souffle / (np.abs(souffle).max() + 1e-9) * (0.5 + 0.5 * np.sin(2 * np.pi * t / 6.0))

        return self.boucle(12.0, voix)

    # --- Lecture ---

    def set_volume(self, volume, musique=None):
        self.volume = volume
        if musique is not None:
            self.musique = musique
        for son, relatif in self.sounds.values():
            son.set_volume(volume * relatif)
        if self.walk:
            self.walk.set_volume(volume * 0.6)
        if self.music_channel:
            self.music_channel.set_volume(self.volume * self.musique * 0.6)

    def play(self, nom):
        if nom in self.sounds:
            self.sounds[nom][0].play()

    def spatial(self, nom, position, ecoute, lacet, portee=14.0):
        """Son placé dans l'espace : plus faible au loin, plus fort dans l'oreille du bon côté."""
        if nom not in self.sounds:
            return
        dx, dz = position[0] - ecoute[0], position[2] - ecoute[2]
        distance = math.hypot(dx, dz)
        if distance > portee:
            return
        volume = (1 - distance / portee) ** 1.5
        a = math.radians(lacet)
        cote = (dx * -math.sin(a) + dz * math.cos(a)) / (distance or 1.0)  # > 0 : à droite
        canal = self.sounds[nom][0].play()
        if canal:
            canal.set_volume(volume * min(1.0, 1 - cote), volume * min(1.0, 1 + cote))

    def music(self, morceau):
        """Change de musique en fondu ("menu", "mission" ou None pour le silence)."""
        if not self.music_channel or morceau == self.morceau:
            return
        self.morceau = morceau
        if morceau is None:
            self.music_channel.fadeout(800)
        else:
            self.music_channel.play(self.musiques[morceau], loops=-1, fade_ms=1500)
            self.music_channel.set_volume(self.volume * self.musique * 0.6)

    def walking(self, en_marche):
        """Le fichier de pas dure 24 s : on le joue en boucle et on le met en pause à l'arrêt."""
        if not self.channel or not self.walk:
            return
        if not en_marche:
            self.channel.pause()
        elif self.channel.get_busy():
            self.channel.unpause()
        else:
            self.channel.play(self.walk, loops=-1)
