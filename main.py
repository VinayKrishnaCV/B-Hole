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
warning_message = ""
warning_start_time = 0
warning_duration = 4000  

winSize = (1000, 600)
display = pygame.display.set_mode(winSize)

paused = False
pause_button_rect = pygame.Rect(winSize[0] - 120, 10, 110, 40)

console_messages = []  
console_max_messages = 20

creator_active = False
creator_state = {
    'name': '',
    'mass': '1',
    'radius': '1',
    'density': '1.0',
    'type': 0,
    'color': [100, 100, 255],
    'active_field': None,
    'dropdown_open': False,
    'dragging_slider': None
}

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
    add_console_message(f"{key} was Spawned")

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

def show_warning(message):
    """Trigger a warning message to be displayed"""
    global warning_message, warning_start_time
    warning_message = message
    warning_start_time = pygame.time.get_ticks()
    add_console_message(f"Warning({message})",color=(110, 9, 10))

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

def toggle_pause():
    """Toggle pause state"""
    global paused
    paused = not paused

def draw_pause_button():
    """Draw the pause/resume button"""
    # Button background
    button_color = (100, 100, 100) if not paused else (50, 150, 50)
    #pygame.draw.rect(display, button_color, pause_button_rect)
    #pygame.draw.rect(display, (255, 255, 255), pause_button_rect, 2)  # White border
    
    # Button text
    button_font = pygame.font.Font(None, 67)
    text =">>" if paused else "▋▋"
    text_surface = button_font.render(text, True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=pause_button_rect.center)
    display.blit(text_surface, text_rect)

def handle_pause_click(mouse_pos):
    """Check if pause button was clicked"""
    if pause_button_rect.collidepoint(mouse_pos):
        toggle_pause()
        return True
    return False

def add_console_message(message, duration=3000, color=(200, 200, 200)):
    global console_messages
    timestamp = pygame.time.get_ticks()
    console_messages.append({
        'text': message,
        'timestamp': timestamp,
        'duration': duration,
        'color': color
    })
    
    # Keep only the last N messages
    if len(console_messages) > console_max_messages:
        console_messages.pop(0)

def draw_console():
    """Draw console messages in bottom-right corner"""
    global console_messages
    
    current_time = pygame.time.get_ticks()
    
    # Remove expired messages
    console_messages = [msg for msg in console_messages if current_time - msg['timestamp'] < msg['duration']]
    
    # Draw messages from bottom to top
    console_font = pygame.font.Font(None, 28)
    y_offset = winSize[1] - 20  # Start from bottom
    
    for msg in reversed(console_messages):  # Newest at bottom
        elapsed = current_time - msg['timestamp']
        
        # Fade out effect in last 500ms
        alpha = 255
        if elapsed > msg['duration'] - 500:
            fade_progress = (msg['duration'] - elapsed) / 500
            alpha = int(255 * fade_progress)
        
        # Render text
        text_surface = console_font.render(msg['text'], True, msg['color'])
        
        # Apply alpha (transparency)
        text_surface.set_alpha(alpha)
        
        # Calculate position (right-aligned with padding)
        text_rect = text_surface.get_rect()
        text_rect.right = winSize[0] - 10  # 10px from right edge
        text_rect.bottom = y_offset
        
        # Draw semi-transparent background
        bg_rect = text_rect.inflate(10, 4)  # Add padding
        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
        bg_surface.set_alpha(int(alpha * 0.5))  # Half transparency
        bg_surface.fill((0, 0, 0))
        display.blit(bg_surface, bg_rect.topleft)
        
        # Draw text
        display.blit(text_surface, text_rect)
        
        # Move up for next message
        y_offset -= text_rect.height + 5

#####################################################################################################################################################################3
def reset_creator_state():
    """Reset creator to default values"""
    global creator_state
    creator_state = {
        'name': '',
        'mass': '1',
        'radius': '1',
        'density': '1.0',
        'type': 0,
        'color': [100, 100, 255],
        'active_field': None,
        'dropdown_open': False,
        'dragging_slider': None
    }

def open_planet_creator():
    """Open the planet creator overlay"""
    global creator_active
    creator_active = True
    toggle_pause()
    reset_creator_state()

def close_planet_creator():
    """Close the planet creator overlay"""
    global creator_active
    creator_active = False

def create_planet_from_creator():
    """Create planet from current creator state"""
    try:
        name = creator_state['name'] or 'custom'
        custom_planet = {
            'col': tuple(creator_state['color']),
            'rad': float(creator_state['radius']) * ER,
            'mass': float(creator_state['mass']) * EM,
            'vel': [0, 0],
            'type': creator_state['type'],
            'density': float(creator_state['density'])
        }
        
        # Add to templates
        planet_templates[name] = custom_planet
        add_console_message(f"Created {name}!", 3000, (0, 255, 0))
        close_planet_creator()
        return True
    except ValueError:
        add_console_message("Invalid values!", 2000, (255, 100, 100))
        return False

def draw_planet_creator_overlay():
    """Draw the planet creator overlay"""
    if not creator_active:
        return
    
    # Semi-transparent background
    overlay = pygame.Surface((winSize[0], winSize[1]))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    display.blit(overlay, (0, 0))
    
    # Main panel
    panel_width = 600
    panel_height = 550
    panel_x = (winSize[0] - panel_width) // 2
    panel_y = (winSize[1] - panel_height) // 2
    panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
    
    pygame.draw.rect(display, (40, 40, 50), panel_rect)
    pygame.draw.rect(display, (100, 150, 255), panel_rect, 3)
    
    creator_font = pygame.font.Font(None, 32)
    label_font = pygame.font.Font(None, 28)
    small_font = pygame.font.Font(None, 24)
    
    # Title
    title = creator_font.render("Create Custom Planet", True, (255, 255, 255))
    title_rect = title.get_rect(centerx=panel_rect.centerx, y=panel_y + 15)
    display.blit(title, title_rect)
    
    # Input fields positions
    field_start_y = panel_y + 70
    field_height = 35
    field_spacing = 60
    label_x = panel_x + 30
    input_x = panel_x + 200
    input_width = 350
    
    input_fields = {
        'name': {'y': field_start_y, 'label': 'Name:', 'key': 'name'},
        'mass': {'y': field_start_y + field_spacing, 'label': 'Mass (EM):', 'key': 'mass'},
        'radius': {'y': field_start_y + field_spacing * 2, 'label': 'Radius (ER):', 'key': 'radius'},
        'density': {'y': field_start_y + field_spacing * 3, 'label': 'Density:', 'key': 'density'}
    }
    
    # Draw input fields
    for field_name, field_info in input_fields.items():
        # Label
        label = label_font.render(field_info['label'], True, (200, 200, 200))
        display.blit(label, (label_x, field_info['y'] + 5))
        
        # Input box
        field_rect = pygame.Rect(input_x, field_info['y'], input_width, field_height)
        is_active = (creator_state['active_field'] == field_name)
        color = (70, 120, 200) if is_active else (60, 60, 70)
        
        pygame.draw.rect(display, color, field_rect)
        pygame.draw.rect(display, (150, 150, 150), field_rect, 2)
        
        # Text
        text = creator_state[field_info['key']]
        if is_active:
            text += "|"  # Cursor
        text_surface = label_font.render(text, True, (255, 255, 255))
        display.blit(text_surface, (field_rect.x + 10, field_rect.y + 5))
        
        # Store rect for click detection
        field_info['rect'] = field_rect
    
    # Planet Type Dropdown
    type_y = field_start_y + field_spacing * 4
    type_label = label_font.render("Type:", True, (200, 200, 200))
    display.blit(type_label, (label_x, type_y + 5))
    
    type_rect = pygame.Rect(input_x, type_y, input_width, field_height)
    pygame.draw.rect(display, (60, 60, 70), type_rect)
    pygame.draw.rect(display, (150, 150, 150), type_rect, 2)
    
    planet_types = {0: 'Solid Planet', 1: 'Gas Giant', 2: 'Star', 3: 'Black Hole'}
    type_text = label_font.render(planet_types[creator_state['type']], True, (255, 255, 255))
    display.blit(type_text, (type_rect.x + 10, type_rect.y + 5))
    
    # Dropdown arrow
    arrow_points = [
        (type_rect.right - 30, type_rect.centery - 5),
        (type_rect.right - 20, type_rect.centery + 5),
        (type_rect.right - 10, type_rect.centery - 5)
    ]
    pygame.draw.polygon(display, (150, 150, 150), arrow_points)
    
    # Store for click detection
    creator_state['type_rect'] = type_rect
    
    # Draw dropdown menu if open
    if creator_state['dropdown_open']:
        for i, (type_id, type_name) in enumerate(planet_types.items()):
            dropdown_item_rect = pygame.Rect(
                type_rect.x,
                type_rect.bottom + i * 40,
                type_rect.width,
                40
            )
            pygame.draw.rect(display, (50, 50, 60), dropdown_item_rect)
            pygame.draw.rect(display, (150, 150, 150), dropdown_item_rect, 1)
            
            item_text = label_font.render(type_name, True, (255, 255, 255))
            display.blit(item_text, (dropdown_item_rect.x + 10, dropdown_item_rect.y + 8))
            
            # Store for click detection
            if 'dropdown_items' not in creator_state:
                creator_state['dropdown_items'] = {}
            creator_state['dropdown_items'][type_id] = dropdown_item_rect
    
    # Color Picker
    color_y = type_y + 70
    color_label = label_font.render("Color:", True, (200, 200, 200))
    display.blit(color_label, (label_x, color_y))
    
    # Color preview box
    color_box_rect = pygame.Rect(input_x, color_y, 80, 80)
    pygame.draw.rect(display, creator_state['color'], color_box_rect)
    pygame.draw.rect(display, (150, 150, 150), color_box_rect, 2)
    
    # RGB Sliders
    slider_x = input_x + 100
    slider_width = 250
    slider_height = 15
    
    rgb_labels = ['R', 'G', 'B']
    for i, (label, value) in enumerate(zip(rgb_labels, creator_state['color'])):
        slider_y = color_y + i * 25
        
        # Label with value
        slider_label = small_font.render(f"{label}: {value}", True, (200, 200, 200))
        display.blit(slider_label, (slider_x, slider_y))
        
        # Slider track
        slider_rect = pygame.Rect(slider_x + 50, slider_y, slider_width, slider_height)
        pygame.draw.rect(display, (60, 60, 70), slider_rect)
        pygame.draw.rect(display, (150, 150, 150), slider_rect, 1)
        
        # Slider handle
        handle_x = slider_rect.x + int((value / 255) * slider_width)
        handle_rect = pygame.Rect(handle_x - 5, slider_rect.y - 3, 10, slider_height + 6)
        pygame.draw.rect(display, (200, 200, 200), handle_rect)
        
        # Store for drag detection
        if 'sliders' not in creator_state:
            creator_state['sliders'] = {}
        creator_state['sliders'][i] = slider_rect
    
    # Buttons
    button_y = panel_y + panel_height - 70
    create_button = pygame.Rect(panel_x + 100, button_y, 150, 45)
    cancel_button = pygame.Rect(panel_x + 350, button_y, 150, 45)
    
    # Create button
    pygame.draw.rect(display, (50, 150, 50), create_button)
    pygame.draw.rect(display, (150, 150, 150), create_button, 2)
    create_text = creator_font.render("Create", True, (255, 255, 255))
    create_text_rect = create_text.get_rect(center=create_button.center)
    display.blit(create_text, create_text_rect)
    
    # Cancel button
    pygame.draw.rect(display, (150, 50, 50), cancel_button)
    pygame.draw.rect(display, (150, 150, 150), cancel_button, 2)
    cancel_text = creator_font.render("Cancel", True, (255, 255, 255))
    cancel_text_rect = cancel_text.get_rect(center=cancel_button.center)
    display.blit(cancel_text, cancel_text_rect)
    
    # Store button rects
    creator_state['create_button'] = create_button
    creator_state['cancel_button'] = cancel_button
    
    # Input fields dict for access
    creator_state['input_fields'] = input_fields

def handle_creator_mouse_click(pos):
    """Handle mouse clicks on creator overlay"""
    if not creator_active:
        return False
    
    # Check input fields
    if 'input_fields' in creator_state:
        clicked_any = False
        for field_name, field_info in creator_state['input_fields'].items():
            if 'rect' in field_info and field_info['rect'].collidepoint(pos):
                creator_state['active_field'] = field_name
                clicked_any = True
            
        if not clicked_any:
            creator_state['active_field'] = None
    
    # Check type dropdown
    if 'type_rect' in creator_state and creator_state['type_rect'].collidepoint(pos):
        creator_state['dropdown_open'] = not creator_state['dropdown_open']
        return True
    
    # Check dropdown items
    if creator_state['dropdown_open'] and 'dropdown_items' in creator_state:
        for type_id, rect in creator_state['dropdown_items'].items():
            if rect.collidepoint(pos):
                creator_state['type'] = type_id
                creator_state['dropdown_open'] = False
                return True
    else:
        creator_state['dropdown_open'] = False
    
    # Check sliders
    if 'sliders' in creator_state:
        for i, slider_rect in creator_state['sliders'].items():
            if slider_rect.collidepoint(pos):
                creator_state['dragging_slider'] = i
                # Update value immediately
                rel_x = pos[0] - slider_rect.x
                new_value = max(0, min(255, int((rel_x / slider_rect.width) * 255)))
                creator_state['color'][i] = new_value
                return True
    
    # Check buttons
    if 'create_button' in creator_state and creator_state['create_button'].collidepoint(pos):
        create_planet_from_creator()
        return True
    
    if 'cancel_button' in creator_state and creator_state['cancel_button'].collidepoint(pos):
        close_planet_creator()
        return True
    
    return True  # Consume click so game doesn't respond

def handle_creator_mouse_drag(pos):
    """Handle mouse dragging for sliders"""
    if not creator_active:
        return
    
    if creator_state['dragging_slider'] is not None and 'sliders' in creator_state:
        i = creator_state['dragging_slider']
        slider_rect = creator_state['sliders'][i]
        rel_x = pos[0] - slider_rect.x
        new_value = max(0, min(255, int((rel_x / slider_rect.width) * 255)))
        creator_state['color'][i] = new_value

def handle_creator_mouse_release():
    """Handle mouse button release"""
    if creator_active:
        creator_state['dragging_slider'] = None

def handle_creator_keypress(event):
    """Handle keyboard input for creator"""
    if not creator_active:
        return False
    
    active = creator_state['active_field']
    if not active:
        return True
    
    if event.key == K_BACKSPACE:
        creator_state[active] = creator_state[active][:-1]
    elif event.key == K_RETURN or event.key == K_TAB:
        creator_state['active_field'] = None
    elif event.unicode.isprintable():
        # Allow appropriate characters
        if active == 'name':
            creator_state[active] += event.unicode
        elif event.unicode.isdigit() or event.unicode == '.':
            creator_state[active] += event.unicode
    
    return True 

############################################################################################################################################################

def draw_pause_overlay():
    """Draw semi-transparent overlay when paused"""
    if paused:
        # Create semi-transparent dark overlay
        overlay = pygame.Surface((winSize[0], winSize[1]))
        overlay.set_alpha(128)  # Semi-transparent
        overlay.fill((0, 0, 0))
        display.blit(overlay, (0, 0))
        
        # Draw "PAUSED" text in center
        pause_font = pygame.font.Font(None, 100)
        pause_text = pause_font.render("PAUSED", True, (255, 255, 255))
        pause_rect = pause_text.get_rect(center=(winSize[0]//2, winSize[1]//2))
        display.blit(pause_text, pause_rect)
        
        # Draw instruction
        inst_font = pygame.font.Font(None, 36)
        inst_text = inst_font.render("Press SPACE or click >> to continue", True, (200, 200, 200))
        inst_rect = inst_text.get_rect(center=(winSize[0]//2, winSize[1]//2 + 80))
        display.blit(inst_text, inst_rect)

def draw_warning():
    """Draw flashing warning message if active"""
    global warning_message, warning_start_time
    
    if warning_message:
        current_time = pygame.time.get_ticks()
        elapsed = current_time - warning_start_time
        
        # Stop showing after 4 seconds
        if elapsed > warning_duration:
            warning_message = ""
            warning_start_time = 0
            return
        
        # Flash effect: show/hide every 500ms
        flash_interval = 500
        if (elapsed // flash_interval) % 2 == 0:  # Flash on/off
            # Create warning text
            warning_font = pygame.font.Font(None, 72)
            text = warning_font.render(warning_message, True, (255, 255, 0))  # Yellow
            
            # Create background rectangle
            text_rect = text.get_rect(center=(winSize[0]//2, winSize[1]//2))
            padding = 20
            bg_rect = pygame.Rect(
                text_rect.x - padding,
                text_rect.y - padding,
                text_rect.width + padding * 2,
                text_rect.height + padding * 2
            )
            
            # Draw red background and yellow border
            pygame.draw.rect(display, (200, 0, 0), bg_rect)
            pygame.draw.rect(display, (255, 255, 0), bg_rect, 3)
            
            # Draw centered text
            display.blit(text, text_rect)

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
    
    r = round(col1[0] * w1 + col2[0] * w2)
    g = round(col1[1] * w1 + col2[1] * w2)
    b = round(col1[2] * w1 + col2[2] * w2)
    
    return (r, g, b)

def merge_planets(p1, p2):
    m1, m2 = p1['mass'], p2['mass']
    v1 = (4/3) * m.pi * (p1['rad']**3)
    v2 = (4/3) * m.pi * (p2['rad']**3)
    new_mass = m1 + m2
    new_vol = v1 + v2
    new_density = new_mass / new_vol
    new_rad = ((3 * new_mass) / (4 * m.pi * new_density))**(1/3)
    new_col = mix_colors(p1['col'], p2['col'], m1, m2)
    
    new_vel = [
        (p1['vel'][0] * m1 + p2['vel'][0] * m2) / new_mass,
        (p1['vel'][1] * m1 + p2['vel'][1] * m2) / new_mass
    ]
    
    return new_mass, new_rad, new_density, new_col, new_vel


def update_planets():
    to_delete = set()
    names = list(data.keys())
    
    for i,p1 in enumerate(names):
        if p1 not in data or p1 in to_delete:
            continue
        planet = data[p1]
        
        for p2 in names[i+1:]:
            if p2 not in data or p2 in to_delete:
                continue
            other = data[p2]
    
            dx = other['pos'][0] - planet['pos'][0]
            dy = other['pos'][1] - planet['pos'][1]
            dist = m.hypot(dx, dy)
            
            if dist <= planet['rad'] + other['rad'] :
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
                    if schwarzschild_rad< 5:
                        show_warning("BH Radius too Small: Sim is Unstable")
                        to_delete.add(absorber_key)
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
        
        draw_stars()
        draw_planets()
        draw_warning()

        if not paused:
            update_planets()
            frame_count += 1
        
        draw_console()

        # CHANGE: Draw debug text to show game is running
        debug_text = font.render(f"Running | Planets: {len(data)} | Frame: {frame_count}", True, (0, 255, 0))
        display.blit(debug_text, (10, 10))
        
        # Draw instructions
        inst_text = font.render("Press E,V,M,J,S,B to spawn planets", True, (255, 255, 255))
        display.blit(inst_text, (10, 550))
        
    
        draw_pause_overlay()
        draw_pause_button()
        draw_planet_creator_overlay()

        clock.tick(fps)
        pygame.display.update()
        
        for event in pygame.event.get():
            if event.type == QUIT:
                run = False
            if event.type == MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    add_console_message("Left button clicked")
                    handle_pause_click(event.pos)
                    if creator_active:
                        handle_creator_mouse_click(event.pos)
                continue

            if event.type == MOUSEMOTION:
                if creator_active:
                    handle_creator_mouse_drag(event.pos)
            
            if event.type == MOUSEBUTTONUP:
                if creator_active:
                    handle_creator_mouse_release() 

            if event.type == KEYDOWN:
                if creator_active:
                    if handle_creator_keypress(event):
                        continue  

                if event.key == K_SPACE:
                    toggle_pause()
                if event.key == K_c:
                    open_planet_creator()
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