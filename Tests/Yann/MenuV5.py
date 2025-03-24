import pygame
import os
import cv2

# Initialisation de Pygame
pygame.init()

# Obtenir les résolutions disponibles
def size_screen():
    largeur, hauteur = pygame.display.Info().current_w, pygame.display.Info().current_h
    resolutions_16_9 = [(800, 600), (426, 240), (640, 360), (854, 480), (960, 540),
                        (1280, 720), (1366, 768), (1600, 900), (1920, 1080),
                        (2560, 1440), (3840, 2160)]
    return [(w, h) for w, h in resolutions_16_9 if w <= largeur and h <= hauteur] + [(0, 0)]

resolutions = size_screen()
current_resolution_index = 0

# Fonction pour changer la résolution
def change_resolution(index):
    global screen, current_resolution_index, settings_background
    current_resolution_index = index
    width, height = resolutions[index]
    if width == 0 and height == 0:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        width, height = pygame.display.Info().current_w, pygame.display.Info().current_h
    else:
        screen = pygame.display.set_mode((width, height))
    settings_background = pygame.transform.scale(pygame.image.load("src/settings_bg.jpg").convert(), (width, height))

# Charger la vidéo locale
def load_local_video(file_path):
    if not os.path.exists(file_path):
        return None
    return cv2.VideoCapture(file_path)

def apply_blur(frame):
    return cv2.GaussianBlur(frame, (21, 21), 0)

# Classe pour les boutons
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

# Fonction pour afficher les paramètres
def display_settings(screen, font, back_button_image):
    screen.blit(settings_background, (0, 0))
    text = font.render("Paramètres", True, (255, 255, 255))
    screen.blit(text, (screen.get_width() // 2 - 50, 100))
    back_rect = back_button_image.get_rect(center=(100, screen.get_height() - 50))
    screen.blit(back_button_image, back_rect)
    return back_rect

# Fonction pour afficher les crédits
def display_credits(screen, font, back_button_image):
    screen.fill((0, 0, 0))
    credits_text = ["Crédits :", "Développé par", "Albert Oscar, Moors Michel, Rinckenbach Yann"]
    for i, line in enumerate(credits_text):
        text_surface = font.render(line, True, (255, 255, 255))
        screen.blit(text_surface, (screen.get_width() // 2 - 100, 200 + i * 40))
    back_rect = back_button_image.get_rect(center=(100, screen.get_height() - 50))
    screen.blit(back_button_image, back_rect)
    return back_rect

# Fonction principale du menu
def main_menu():
    global screen, settings_background
    screen_width, screen_height = 800, 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Menu Principal")
    
    # Charger les images
    settings_background = pygame.image.load("src/settings_bg.jpg").convert()
    settings_background = pygame.transform.scale(settings_background, (screen_width, screen_height))
    back_button_image = pygame.image.load("src/back_arrow.png").convert_alpha()
    back_button_image = pygame.transform.scale(back_button_image, (50, 50))
    
    # Charger la vidéo
    video_capture = load_local_video("src/bg.mp4")
    
    # Création des boutons
    font = pygame.font.Font(None, 36)
    buttons = [
        Button(screen_width // 2 - 100, 200, 200, 50, "Jouer", font, (100, 200, 255), (50, 150, 255)),
        Button(screen_width // 2 - 100, 300, 200, 50, "Paramètres", font, (100, 200, 255), (50, 150, 255)),
        Button(screen_width // 2 - 100, 400, 200, 50, "Crédits", font, (100, 200, 255), (50, 150, 255))
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
                        current_state = ["game", "settings", "credits"][i]
            elif event.type == pygame.MOUSEBUTTONDOWN and current_state in ["settings", "credits"]:
                back_rect = display_settings(screen, font, back_button_image) if current_state == "settings" else display_credits(screen, font, back_button_image)
                if back_rect.collidepoint(event.pos):
                    current_state = "menu"
        
        screen.fill((0, 0, 0))
        if current_state == "menu" and video_capture:
            ret, frame = video_capture.read()
            if ret:
                frame = apply_blur(cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (screen_width, screen_height)))
                screen.blit(pygame.transform.rotate(pygame.surfarray.make_surface(frame), -90), (0, 0))
            else:
                video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            for button in buttons:
                button.draw(screen)
        elif current_state == "settings":
            display_settings(screen, font, back_button_image)
        elif current_state == "credits":
            display_credits(screen, font, back_button_image)
        
        pygame.display.flip()
        clock.tick(30)
    
    if video_capture:
        video_capture.release()
    pygame.quit()

if __name__ == "__main__":
    main_menu()
