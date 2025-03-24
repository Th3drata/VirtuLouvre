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

def apply_blur(frame):
    return cv2.GaussianBlur(frame, (21, 21), 0)

# Classe pour gérer les boutons
class Button:
    def __init__(self, x, y, width, height, text, font, color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = hover_color

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        button_color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(surface, button_color, self.rect, border_radius=10)
        text_surface = self.font.render(self.text, True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos)

# Fonction pour afficher les paramètres avec onglets
def display_settings(screen, font, background_image, back_button_image, current_tab):
    screen.blit(background_image, (0, 0))
    tabs = ["Vidéo", "Audio", "JSP"]
    tab_buttons = []
    tab_width = 250
    tab_height = 40
    tab_spacing = -13
    start_x = (screen.get_width() - (len(tabs) * (tab_width + tab_spacing) - tab_spacing)) // 2
    start_y = 20

    for i, tab in enumerate(tabs):
        tab_buttons.append(Button(start_x + i * (tab_width + tab_spacing), start_y, tab_width, tab_height, tab, font, (200, 200, 200), (150, 150, 150)))
        tab_buttons[i].draw(screen)
    
    # Affichage du contenu selon l'onglet actif
    if current_tab == "Vidéo":
        text = font.render("Bla", True, (255, 255, 255))
    elif current_tab == "Audio":
        text = font.render("BloBlo", True, (255, 255, 255))
    else:
        text = font.render("NoLNol", True, (255, 255, 255))
    
    text_rect = text.get_rect(center=(screen.get_width() // 2, 200))
    screen.blit(text, text_rect)
    back_rect = back_button_image.get_rect(center=(100, screen.get_height() - 50))
    screen.blit(back_button_image, back_rect)
    return back_rect, tab_buttons

# Fonction principale du menu
def main_menu():
    pygame.init()
    screen_width, screen_height = 800, 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Menu principal")
    settings_background = pygame.image.load("src/settings_bg.jpg").convert()
    settings_background = pygame.transform.scale(settings_background, (screen_width, screen_height))
    back_button_image = pygame.image.load("src/back_arrow.png").convert_alpha()
    back_button_image = pygame.transform.scale(back_button_image, (50, 50))
    font = pygame.font.Font(None, 36)
    blue = (100, 200, 255)
    hover_blue = (50, 150, 255)
    buttons = [
        Button(screen_width // 2 - 100, 300, 200, 50, "Paramètres", font, blue, hover_blue)
    ]
    clock = pygame.time.Clock()
    running = True
    current_state = "menu"
    current_tab = "A"
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if current_state == "menu":
                for button in buttons:
                    if button.is_clicked(event):
                        current_state = "settings"
            elif current_state == "settings":
                back_rect, tab_buttons = display_settings(screen, font, settings_background, back_button_image, current_tab)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if back_rect.collidepoint(event.pos):
                        current_state = "menu"
                    for tab_button in tab_buttons:
                        if tab_button.is_clicked(event):
                            current_tab = tab_button.text
        screen.fill((0, 0, 0))
        if current_state == "menu":
            for button in buttons:
                button.draw(screen)
        elif current_state == "settings":
            display_settings(screen, font, settings_background, back_button_image, current_tab)
        pygame.display.flip()
        clock.tick(30)
    pygame.quit()

if __name__ == "__main__":
    main_menu()
