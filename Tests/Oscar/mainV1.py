import os
import time
import keyboard 

width, height = 64, 64 
player_x, player_y = width // 2, height // 2 

GREEN = '\033[92m'
RESET = '\033[0m'

def draw_screen(player_x, player_y):
    os.system('cls' if os.name == 'nt' else 'clear')  
    

    for y in range(height):
        for x in range(width):
            if x == player_x and y == player_y:
                print(f'{GREEN}O{RESET}', end=' ')  
            else:
                print('@', end=' ')  
        print()

def move_player(player_x, player_y, direction):
    if direction == 'left' and player_x > 0:
        player_x -= 1
    elif direction == 'right' and player_x < width - 1:
        player_x += 1
    elif direction == 'up' and player_y > 0:
        player_y -= 1
    elif direction == 'down' and player_y < height - 1:
        player_y += 1
    return player_x, player_y

loop = True
while loop:
    draw_screen(player_x, player_y)

    if keyboard.is_pressed('q'):
        loop = False  
    elif keyboard.is_pressed('left'):
        player_x, player_y = move_player(player_x, player_y, 'left')
    elif keyboard.is_pressed('right'):
        player_x, player_y = move_player(player_x, player_y, 'right')
    elif keyboard.is_pressed('up'):
        player_x, player_y = move_player(player_x, player_y, 'up')
    elif keyboard.is_pressed('down'):
        player_x, player_y = move_player(player_x, player_y, 'down')

