import pygame
pygame.init()
from pygame.locals import *
from random import randint
import math as m
import copy
import asyncio

EM = 1
ER = 1
G = 0.0007
C = 4.07e6

winSize = (1000, 600)
display = pygame.display.set_mode(winSize)
# CHANGE: Set window title for debugging
pygame.display.set_caption("Gravity Simulator - Press E,V,M,J,S,B to spawn")
fps = 27
clock = pygame.time.Clock()

# CHANGE: Initialize font for debug text
font = pygame.font.Font(None, 36)

stars = [((randint(150, 200), randint(150, 200), randint(150, 200)),
          (randint(1, winSize[0]), randint(1, winSize[1])),
          randint(1, 2)) for _ in range(275)]

data = {}
_next_planet_id = 0

# Planet Types:
# 0 - Solid Planet
# 1 - Gas Planet
# 2 - Star
# 3 - Black Hole
# -1 - Nothing

planet_templates = {
    "sun": {
        "col": (255, 255, 0),
        "rad": 109 * ER,
        "mass": 333000 * EM,
        "vel": [0, 0],
        "type": 2,
        "density": 0.25
    },
    "earth": {
        "col": (100, 100, 255),
        "rad": 1 * ER,
        "mass": 1 * EM,
        "vel": [0, 0],
        "type": 0,
        "density": 1.0
    },
    "venus": {
        "col": (255, 50, 50),
        "rad": 0.95 * ER,
        "mass": 0.815 * EM,
        "vel": [0, 0],
        "type": 0,
        "density": 0.95
    },
    "mars": {
        "col": (255, 0, 0),
        "rad": 0.53 * ER,
        "mass": 0.107 * EM,
        "vel": [0, 0],
        "type": 0,
        "density": 0.71
    },
    "jupiter": {
        "col": (255, 150, 150),
        "rad": 11.21 * ER,
        "mass": 317.8 * EM,
        "vel": [0, 0],
        "type": 1,
        "density": 0.24
    },
    "blackhole": {
        "col": (0, 0, 0),
        "rad": 5 * ER,
        "mass": 500000 * EM,
        "vel": [0, 0],
        "type": 3,
        "density": 10.0
    }
}

def spawn_planet(name, pos):
    global _next_planet_id
    if name not in planet_templates:
        return
    base = copy.deepcopy(planet_templates[name])
    base["pos"] = [float(pos[0]), float(pos[1])]
    base["vel"] = [0.0, 0.0]
    key = f"{name}_{_next_planet_id}"
    data[key] = base
    _next_planet_id += 1

def collision_outcome(oPlanet, planet):
    type1 = data[oPlanet]["type"]
    type2 = data[planet]["type"]
    if type1 == 0:
        if type2 == 0:
            return -1
        elif type2 == 1:
            return 1
        elif type2 == 2:
            return 2
        elif type2 == 3:
            return 3
    elif type1 == 1:
        if type2 in (0, 1):
            return 1
        elif type2 == 2:
            return 2
        elif type2 == 3:
            return 3
    elif type1 == 2:
        if type2 in (0, 1):
            return 2
        else:
            return 3
    else:
        return 3

def draw_stars():
    for star in stars:
        pygame.draw.circle(display, star[0], star[1], star[2])

def draw_planets():
    for planet in data.values():
        if planet["type"] == 3:
            disc_rad = int(planet['rad'] * 3)
            center = (int(planet['pos'][0]), int(planet['pos'][1]))
            
            for i in range(4):
                alpha_rad = disc_rad - i * (disc_rad // 8)
                color_intensity = 255 - i * 40
                disc_color = (color_intensity, int(color_intensity * 0.6), 0)
                pygame.draw.circle(display, disc_color, center, alpha_rad, width=2)
            
            pygame.draw.circle(display, (0, 0, 0), center, max(1, int(planet['rad'])))
        else:
            pygame.draw.circle(display, planet['col'], (int(planet['pos'][0]), int(planet['pos'][1])), max(1, int(planet['rad'])))

def out_of_bounds(p):
    if p["pos"][0] < 0 or p["pos"][0] > winSize[0]:
        return True
    if p["pos"][1] < 0 or p["pos"][1] > winSize[1]:
        return True
    return False

def mix_colors(col1, col2, mass1, mass2):
    total_mass = mass1 + mass2
    w1 = mass1 / total_mass
    w2 = mass2 / total_mass
    
    r = int(col1[0] * w1 + col2[0] * w2)
    g = int(col1[1] * w1 + col2[1] * w2)
    b = int(col1[2] * w1 + col2[2] * w2)
    
    return (r, g, b)

def merge_planets(p1, p2):
    m1, m2 = p1['mass'], p2['mass']
    v1 = (4/3) * 3.14 * (p1['rad']**3)
    v2 = (4/3) * 3.14 * (p2['rad']**3)
    new_mass = m1 + m2
    new_vol = v1 + v2
    new_density = new_mass / new_vol
    new_rad = ((3 * new_mass) / (4 * 3.14 * new_density))**(1/3)
    new_col = mix_colors(p1['col'], p2['col'], m1, m2)
    
    new_vel = [
        (p1['vel'][0] * m1 + p2['vel'][0] * m2) / new_mass,
        (p1['vel'][1] * m1 + p2['vel'][1] * m2) / new_mass
    ]
    
    return new_mass, new_rad, new_density, new_col, new_vel


def update_planets():
    to_delete = set()
    names = list(data.keys())
    
    for p1 in names:
        if p1 not in data or p1 in to_delete:
            continue
        planet = data[p1]
        
        for p2 in names:
            if p1 == p2 or p2 not in data or p2 in to_delete:
                continue
            other = data[p2]
    
            dx = other['pos'][0] - planet['pos'][0]
            dy = other['pos'][1] - planet['pos'][1]
            dist = m.hypot(dx, dy)
            
            if dist <= planet['rad'] + other['rad']:
                if planet['mass'] > other['mass']:
                    absorber, absorbed = planet, other
                    absorber_key, absorbed_key = p1, p2
                else:
                    absorber, absorbed = other, planet
                    absorber_key, absorbed_key = p2, p1
                
                to_delete.add(absorbed_key)
                co = collision_outcome(absorber_key, absorbed_key)
                absorber['mass'], absorber['rad'], absorber['density'], new_col, absorber['vel'] = merge_planets(absorber, absorbed)
                
                if co == -1:
                    to_delete.add(absorber_key)
                    absorber['col'] = new_col
                elif co == 1:
                    absorber['type'] = 1
                    absorber['col'] = new_col
                elif co == 2:
                    absorber['type'] = 2
                    absorber['col'] = (255, 255, 0)
                elif co == 3:
                    absorber['col'] = (20, 20, 20)
                    absorber['type'] = 3
                    # CHANGE: Ensure black holes have minimum visible radius for proper collision detection
                    schwarzschild_rad = (2 * absorber["mass"] * G) / (C ** 2)
                    absorber['rad'] = max(5, schwarzschild_rad)
                break  
    
    for p1 in names:
        if p1 not in data or p1 in to_delete:
            continue
        planet = data[p1]
        
        # CHANGE: Delete planets that become too small to see
        if planet['rad'] < 0.5:
            to_delete.add(p1)
            continue
        
        if out_of_bounds(planet):
            to_delete.add(p1)
            continue

        for p2 in names:
            if p1 == p2 or p2 not in data or p2 in to_delete:
                continue
            other = data[p2]
    
            dx = other['pos'][0] - planet['pos'][0]
            dy = other['pos'][1] - planet['pos'][1]
            dist = m.hypot(dx, dy)

            # CHANGE: Prevent extreme accelerations when planets get too close
            if dist > planet['rad'] + other['rad']:
                accel = G * other['mass'] / (dist ** 2)
                planet['vel'][0] += accel * dx / dist
                planet['vel'][1] += accel * dy / dist
        
        planet['pos'][0] += planet['vel'][0]
        planet['pos'][1] += planet['vel'][1]
    
    for p in to_delete:
        if p in data:
            del data[p]

# CHANGE: Made main loop async for Pygbag compatibility
async def main():
    run = True
    frame_count = 0
    
    # CHANGE: Spawn a sun at startup for visibility testing
    spawn_planet("sun", (500, 300))
    
    while run:
        display.fill((0, 0, 0))
        
        # CHANGE: Draw debug text to show game is running
        debug_text = font.render(f"Running | Planets: {len(data)} | Frame: {frame_count}", True, (0, 255, 0))
        display.blit(debug_text, (10, 10))
        
        # Draw instructions
        inst_text = font.render("Press E,V,M,J,S,B to spawn planets", True, (255, 255, 255))
        display.blit(inst_text, (10, 550))
        
        draw_stars()
        draw_planets()
        update_planets()
        #clock.tick(fps)
        pygame.display.update()
        
        frame_count += 1
        
        for event in pygame.event.get():
            if event.type == QUIT:
                run = False
            if event.type == KEYDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if event.key == K_e:
                    spawn_planet("earth", mouse_pos)
                elif event.key == K_v:
                    spawn_planet("venus", mouse_pos)
                elif event.key == K_m:
                    spawn_planet("mars", mouse_pos)
                elif event.key == K_j:
                    spawn_planet("jupiter", mouse_pos)
                elif event.key == K_s:
                    spawn_planet("sun", mouse_pos)
                elif event.key == K_b:
                    spawn_planet("blackhole", mouse_pos)
        await asyncio.sleep(0)
    pygame.quit()
asyncio.run(main())