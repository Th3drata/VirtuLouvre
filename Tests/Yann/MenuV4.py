import pygame
import os
import cv2

# Initialisation de Pygame
pygame.init()

# Paramètres modifiables
defaut_controls = {
    "avancer": pygame.K_w,
    "reculer": pygame.K_s,
    "gauche": pygame.K_a,
    "droite": pygame.K_d
}
screen_width, screen_height = 800, 600
volume_levels = [0, 20, 40, 60, 80, 100]
current_volume_index = 3  # Par défaut : 60%

# Fonction pour afficher les paramètres
def display_settings(screen, font, background_image, back_button_image):
    global screen_width, screen_height, current_volume_index, defaut_controls
    
    screen.blit(background_image, (0, 0))
    
    settings_text = [
        "Paramètres :",
        "1. Modifier touches",
        "2. Modifier dimensions",
        "3. Modifier volume"
    ]
    
    start_y = 150
    for i, line in enumerate(settings_text):
        text_surface = font.render(line, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(400, start_y + i * 40))
        screen.blit(text_surface, text_rect)
    
    # Afficher les touches actuelles
    key_text = f"Touches : ZQSD / {pygame.key.name(defaut_controls['avancer'])}, {pygame.key.name(defaut_controls['reculer'])}, {pygame.key.name(defaut_controls['gauche'])}, {pygame.key.name(defaut_controls['droite'])}"
    key_surface = font.render(key_text, True, (255, 255, 255))
    key_rect = key_surface.get_rect(center=(400, 300))
    screen.blit(key_surface, key_rect)
    
    # Afficher la résolution actuelle
    res_text = f"Résolution : {screen_width}x{screen_height}"
    res_surface = font.render(res_text, True, (255, 255, 255))
    res_rect = res_surface.get_rect(center=(400, 350))
    screen.blit(res_surface, res_rect)
    
    # Afficher le volume actuel
    vol_text = f"Volume : {volume_levels[current_volume_index]}%"
    vol_surface = font.render(vol_text, True, (255, 255, 255))
    vol_rect = vol_surface.get_rect(center=(400, 400))
    screen.blit(vol_surface, vol_rect)
    
    return vol_rect

# Fonction principale du menu
def main_menu():
    global screen_width, screen_height, current_volume_index, defaut_controls
    
    pygame.init()
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Menu principal")
    font = pygame.font.Font(None, 36)
    
    settings_background = pygame.Surface((screen_width, screen_height))
    settings_background.fill((50, 50, 50))
    
    back_button_image = pygame.Surface((50, 50))
    back_button_image.fill((200, 0, 0))
    
    running = True
    current_state = "menu"
    
    while running:
        screen.fill((0, 0, 0))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if current_state == "settings":
                    if event.key == pygame.K_1:  # Modifier les touches
                        defaut_controls['avancer'] = pygame.K_UP
                        defaut_controls['reculer'] = pygame.K_DOWN
                        defaut_controls['gauche'] = pygame.K_LEFT
                        defaut_controls['droite'] = pygame.K_RIGHT
                    elif event.key == pygame.K_2:  # Modifier la résolution
                        screen_width, screen_height = 1024, 768
                        screen = pygame.display.set_mode((screen_width, screen_height))
                    elif event.key == pygame.K_3:  # Modifier le volume
                        current_volume_index = (current_volume_index + 1) % len(volume_levels)
        
        if current_state == "settings":
            display_settings(screen, font, settings_background, back_button_image)
        
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main_menu()
