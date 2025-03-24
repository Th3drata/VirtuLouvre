import pygame
import os
import cv2

# Initialisation de Pygame et de la police
pygame.init()

version_text = "Version 1.0.0"
try:
    version_font = pygame.font.Font(None, 24)  # Police par défaut
except:
    print("Erreur lors de l'initialisation de la police, utilisation de la police par défaut.")
    version_font = pygame.font.SysFont('Arial', 24)  # Si 'None' échoue, utiliser Arial comme fallback

# Fonction pour charger une vidéo locale
def load_local_video(file_path):
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Le fichier vidéo '{file_path}' n'existe pas.")
        return cv2.VideoCapture(file_path)
    except Exception as e:
        print(f"Erreur: Impossible de charger la vidéo depuis le fichier '{file_path}'. {e}")
        return None

# Fonction pour appliquer un flou gaussien sur une image
def apply_blur(frame):
    return cv2.GaussianBlur(frame, (21, 21), 0)  # Le second paramètre doit être un tuple impair, ex : (21, 21)

# Classe pour gérer les boutons
class Button:
    def __init__(self, x, y, width, height, text, font, color, hover_color, border_radius=10):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.border_radius = border_radius

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        button_color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(surface, button_color, self.rect, border_radius=self.border_radius)
        text_surface = self.font.render(self.text, True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos)

# Fonction pour afficher les crédits
def display_credits(screen, font, background_image, back_button_image):
    screen.blit(background_image, (0, 0))

    credits_text = [
        "Crédits :",
        "Développé par",
        "Albert Oscar, Moors Michel, Rinckenbach Yann"
    ]

    start_y = 200
    line_spacing = 40

    for i, line in enumerate(credits_text):
        text_surface = font.render(line, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(400, start_y + i * line_spacing))
        screen.blit(text_surface, text_rect)

    # Afficher la flèche pour revenir
    back_rect = back_button_image.get_rect(center=(100, screen.get_height() - 50))
    screen.blit(back_button_image, back_rect)
    
    return back_rect

# Fonction pour afficher les paramètres
def display_settings(screen, font, background_image, back_button_image):
    screen.blit(background_image, (0, 0))
    text = font.render("Paramètres : Personnalisez votre jeu ici", True, (255, 255, 255))
    text_rect = text.get_rect(center=(400, 300))
    screen.blit(text, text_rect)

    # Afficher la flèche pour revenir
    back_rect = back_button_image.get_rect(center=(100, screen.get_height() - 50))
    screen.blit(back_button_image, back_rect)
    
    return back_rect

# Fonction pour démarrer le jeu
def start_game(screen, font, background_image):
    screen.blit(background_image, (0, 0))
    text = font.render("Jeu en cours... (Simulation)", True, (255, 255, 255))
    text_rect = text.get_rect(center=(400, 300))
    screen.blit(text, text_rect)

    back_button = font.render("Appuyez sur 'Retour' pour revenir", True, (200, 200, 200))
    back_rect = back_button.get_rect(center=(400, 500))
    screen.blit(back_button, back_rect)

# Fonction principale du menu
def main_menu():
    pygame.init()

    # Paramètres d'écran
    screen_width, screen_height = 800, 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Menu principal")

    # Charger les images d'arrière-plan
    credits_background = pygame.image.load("credits_bg.jpg").convert()
    settings_background = pygame.image.load("settings_bg.jpg").convert()
    game_background = pygame.image.load("game_bg.jpg").convert()

    credits_background = pygame.transform.scale(credits_background, (screen_width, screen_height))
    settings_background = pygame.transform.scale(settings_background, (screen_width, screen_height))
    game_background = pygame.transform.scale(game_background, (screen_width, screen_height))

    # Charger la vidéo de fond pour le menu principal
    local_video_path = "bg.mp4"
    video_capture = load_local_video(local_video_path)

    # Charger l'image de la flèche pour le retour
    back_button_image = pygame.image.load("back_arrow.png").convert_alpha()
    back_button_image = pygame.transform.scale(back_button_image, (50, 50))

    # Couleurs et police
    blue = (100, 200, 255)
    hover_blue = (50, 150, 255)
    font = pygame.font.Font(None, 36)

    buttons = [
        Button(screen_width // 2 - 100, 200, 200, 50, "Jouer", font, blue, hover_blue),
        Button(screen_width // 2 - 100, 300, 200, 50, "Paramètres", font, blue, hover_blue),
        Button(screen_width // 2 - 100, 400, 200, 50, "Crédits", font, blue, hover_blue),
    ]

    clock = pygame.time.Clock()
    running = True
    current_state = "menu"

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if current_state == "menu":
                for i, button in enumerate(buttons):
                    if button.is_clicked(event):
                        if i == 0:
                            current_state = "game"
                        elif i == 1:
                            current_state = "settings"
                        elif i == 2:
                            current_state = "credits"

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    current_state = "menu"
                elif event.key == pygame.K_LEFT:  # Flèche gauche pour revenir au menu
                    current_state = "menu"

        # Afficher l'état courant
        if current_state == "menu":
            if video_capture:
                ret, frame = video_capture.read()
                if ret:
                    frame = cv2.resize(frame, (screen_width, screen_height))
                    frame = apply_blur(frame)  # Appliquer le flou ici
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_surface = pygame.surfarray.make_surface(frame)
                    screen.blit(pygame.transform.rotate(frame_surface, -90), (0, 0))
                else:
                    video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            for button in buttons:
                button.draw(screen)

            # Afficher la version en bas à droite
            version_surface = version_font.render(version_text, True, (255, 255, 255))
            version_rect = version_surface.get_rect(bottomright=(screen_width - 10, screen_height - 10))
            screen.blit(version_surface, version_rect)

        elif current_state == "credits":
            back_rect = display_credits(screen, font, credits_background, back_button_image)
            if event.type == pygame.MOUSEBUTTONDOWN and back_rect.collidepoint(event.pos):
                current_state = "menu"
        elif current_state == "settings":
            back_rect = display_settings(screen, font, settings_background, back_button_image)
            if event.type == pygame.MOUSEBUTTONDOWN and back_rect.collidepoint(event.pos):
                current_state = "menu"
        elif current_state == "game":
            start_game(screen, font, game_background)

        pygame.display.flip()
        clock.tick(30)

    if video_capture:
        video_capture.release()
    pygame.quit()

if __name__ == "__main__":
    main_menu()