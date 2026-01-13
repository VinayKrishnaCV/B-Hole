import pygame
pygame.init()
from pygame.locals import *
from random import randint
import math as m
import copy
import asyncio
import mysql.connector
from mysql.connector import Error

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
    'type': 0,
    'color': [100, 100, 255],
    'active_field': None,
    'dropdown_open': False,
    'dragging_slider': None
}

# Planet Selector Menu State
selector_active = False
selector_selected_planet = None
selector_scroll_y = 0
selector_max_scroll = 0
selector_dragging_scrollbar = False
selector_drag_offset = 0

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Vinay@050209',
    'database': 'gravity_simulator'
}

pygame.display.set_caption("Gravity Simulator")
fps = 27
clock = pygame.time.Clock()

font = pygame.font.Font(None, 36)

stars = [((randint(150, 200), randint(150, 200), randint(150, 200)),
          (randint(1, winSize[0]), randint(1, winSize[1])),
          randint(1, 2)) for _ in range(275)]

data = {}
_next_planet_id = 0

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

# ==================== DATABASE FUNCTIONS ====================

def get_db_connection():
    """Get connection to the gravity_simulator database"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        add_console_message(f"DB Error: {e}", 3000, (255, 100, 100))
        return None

def initialize_database():
    """Create database and tables if they don't exist"""
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = connection.cursor()
        
        cursor.execute("CREATE DATABASE IF NOT EXISTS gravity_simulator")
        cursor.close()
        connection.close()
        
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            
            create_table_query = """
            CREATE TABLE IF NOT EXISTS custom_planets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                color_r INT NOT NULL CHECK (color_r >= 0 AND color_r <= 255),
                color_g INT NOT NULL CHECK (color_g >= 0 AND color_g <= 255),
                color_b INT NOT NULL CHECK (color_b >= 0 AND color_b <= 255),
                radius FLOAT NOT NULL,
                mass FLOAT NOT NULL,
                type INT NOT NULL CHECK (type >= 0 AND type <= 3),
                density FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_name (name),
                INDEX idx_type (type)
            )
            """
            cursor.execute(create_table_query)
            connection.commit()
            cursor.close()
            connection.close()
            add_console_message("Database initialized!", 3000, (0, 255, 0))
            return True
    except Error as e:
        add_console_message(f"DB Init Error: {e}", 3000, (255, 100, 100))
        return False

def save_custom_planet_to_db(name, color, radius, mass, planet_type, density):
    """Save a custom planet to database"""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            
            insert_query = """
            INSERT INTO custom_planets (name, color_r, color_g, color_b, radius, mass, type, density)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (name, color[0], color[1], color[2], radius, mass, planet_type, density)
            cursor.execute(insert_query, values)
            connection.commit()
            
            cursor.close()
            connection.close()
            add_console_message(f"Saved {name} to DB!", 3000, (0, 255, 0))
            return True
            
        except Error as e:
            add_console_message(f"Save Error: {e}", 3000, (255, 100, 100))
            return False
    return False

def load_custom_planets_from_db():
    """Load all custom planets from database into planet_templates"""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            select_query = "SELECT * FROM custom_planets ORDER BY created_at DESC"
            cursor.execute(select_query)
            
            planets = cursor.fetchall()
            
            for planet in planets:
                name = planet['name']
                planet_templates[name] = {
                    'col': (planet['color_r'], planet['color_g'], planet['color_b']),
                    'rad': planet['radius'],
                    'mass': planet['mass'],
                    'vel': [0, 0],
                    'type': planet['type'],
                    'density': planet['density']
                }
            
            cursor.close()
            connection.close()
            
            if planets:
                add_console_message(f"Loaded {len(planets)} custom planets", 3000, (100, 200, 255))
            return len(planets)
            
        except Error as e:
            add_console_message(f"Load Error: {e}", 3000, (255, 100, 100))
            return 0
    return 0

def delete_custom_planet_from_db(name):
    """Delete a custom planet from database"""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            
            delete_query = "DELETE FROM custom_planets WHERE name = %s"
            cursor.execute(delete_query, (name,))
            connection.commit()
            
            if cursor.rowcount > 0:
                cursor.close()
                connection.close()
                add_console_message(f"Deleted {name} from DB", 3000, (255, 200, 0))
                return True
            
            cursor.close()
            connection.close()
            return False
            
        except Error as e:
            add_console_message(f"Delete Error: {e}", 3000, (255, 100, 100))
            return False
    return False

def calculate_density(mass, radius):
    """Calculate density from mass and radius using sphere volume formula"""
    volume = (4/3) * m.pi * (radius ** 3)
    density = mass / volume
    return density

# ==================== GAME FUNCTIONS ====================

def spawn_planet(name, pos):
    global _next_planet_id
    if name not in planet_templates:
        add_console_message(f"Planet {name} not found!", 2000, (255, 100, 100))
        return
    base = copy.deepcopy(planet_templates[name])
    base["pos"] = [float(pos[0]), float(pos[1])]
    base["vel"] = [0.0, 0.0]
    key = f"{name}_{_next_planet_id}"
    data[key] = base
    _next_planet_id += 1
    add_console_message(f"{name} spawned")

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
    global warning_message, warning_start_time
    warning_message = message
    warning_start_time = pygame.time.get_ticks()
    add_console_message(f"Warning: {message}", color=(110, 9, 10))

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
    global paused
    paused = not paused

def draw_pause_button():
    button_font = pygame.font.Font(None, 67)
    text = ">>" if paused else "▋▋"
    text_surface = button_font.render(text, True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=pause_button_rect.center)
    display.blit(text_surface, text_rect)

def handle_pause_click(mouse_pos):
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
    
    if len(console_messages) > console_max_messages:
        console_messages.pop(0)

def draw_console():
    global console_messages
    
    current_time = pygame.time.get_ticks()
    console_messages = [msg for msg in console_messages if current_time - msg['timestamp'] < msg['duration']]
    
    console_font = pygame.font.Font(None, 28)
    y_offset = winSize[1] - 20
    
    for msg in reversed(console_messages):
        elapsed = current_time - msg['timestamp']
        
        alpha = 255
        if elapsed > msg['duration'] - 500:
            fade_progress = (msg['duration'] - elapsed) / 500
            alpha = int(255 * fade_progress)
        
        text_surface = console_font.render(msg['text'], True, msg['color'])
        text_surface.set_alpha(alpha)
        
        text_rect = text_surface.get_rect()
        text_rect.right = winSize[0] - 10
        text_rect.bottom = y_offset
        
        bg_rect = text_rect.inflate(10, 4)
        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
        bg_surface.set_alpha(int(alpha * 0.5))
        bg_surface.fill((0, 0, 0))
        display.blit(bg_surface, bg_rect.topleft)
        
        display.blit(text_surface, text_rect)
        y_offset -= text_rect.height + 5

# ==================== PLANET CREATOR ====================

def reset_creator_state():
    global creator_state
    creator_state = {
        'name': '',
        'mass': '1',
        'radius': '1',
        'type': 0,
        'color': [100, 100, 255],
        'active_field': None,
        'dropdown_open': False,
        'dragging_slider': None
    }

def open_planet_creator():
    global creator_active, paused
    creator_active = True
    if not paused:
        toggle_pause()
    reset_creator_state()

def close_planet_creator():
    global creator_active
    creator_active = False

def create_planet_from_creator():
    try:
        name = creator_state['name'] or 'custom'
        radius = float(creator_state['radius']) * ER
        mass = float(creator_state['mass']) * EM
        
        density = calculate_density(mass, radius)
        
        custom_planet = {
            'col': tuple(creator_state['color']),
            'rad': radius,
            'mass': mass,
            'vel': [0, 0],
            'type': creator_state['type'],
            'density': density
        }
        
        planet_templates[name] = custom_planet
        
        save_custom_planet_to_db(
            name,
            creator_state['color'],
            float(creator_state['radius']),
            float(creator_state['mass']),
            creator_state['type'],
            density
        )
        
        add_console_message(f"Created {name}! (Density: {density:.2f})", 3000, (0, 255, 0))
        close_planet_creator()
        return True
    except ValueError:
        add_console_message("Invalid values!", 2000, (255, 100, 100))
        return False

def draw_planet_creator_overlay():
    if not creator_active:
        return
    
    overlay = pygame.Surface((winSize[0], winSize[1]))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    display.blit(overlay, (0, 0))
    
    panel_width = 600
    panel_height = 500
    panel_x = (winSize[0] - panel_width) // 2
    panel_y = (winSize[1] - panel_height) // 2
    panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
    
    pygame.draw.rect(display, (40, 40, 50), panel_rect)
    pygame.draw.rect(display, (100, 150, 255), panel_rect, 3)
    
    creator_font = pygame.font.Font(None, 32)
    label_font = pygame.font.Font(None, 28)
    small_font = pygame.font.Font(None, 24)
    
    title = creator_font.render("Create Custom Planet", True, (255, 255, 255))
    title_rect = title.get_rect(centerx=panel_rect.centerx, y=panel_y + 15)
    display.blit(title, title_rect)
    
    field_start_y = panel_y + 70
    field_height = 35
    field_spacing = 60
    label_x = panel_x + 30
    input_x = panel_x + 200
    input_width = 350
    
    input_fields = {
        'name': {'y': field_start_y, 'label': 'Name:', 'key': 'name'},
        'mass': {'y': field_start_y + field_spacing, 'label': 'Mass (EM):', 'key': 'mass'},
        'radius': {'y': field_start_y + field_spacing * 2, 'label': 'Radius (ER):', 'key': 'radius'}
    }
    
    for field_name, field_info in input_fields.items():
        label = label_font.render(field_info['label'], True, (200, 200, 200))
        display.blit(label, (label_x, field_info['y'] + 5))
        
        field_rect = pygame.Rect(input_x, field_info['y'], input_width, field_height)
        is_active = (creator_state['active_field'] == field_name)
        color = (70, 120, 200) if is_active else (60, 60, 70)
        
        pygame.draw.rect(display, color, field_rect)
        pygame.draw.rect(display, (150, 150, 150), field_rect, 2)
        
        text = creator_state[field_info['key']]
        if is_active:
            text += "|"
        text_surface = label_font.render(text, True, (255, 255, 255))
        display.blit(text_surface, (field_rect.x + 10, field_rect.y + 5))
        
        field_info['rect'] = field_rect
    
    try:
        mass = float(creator_state['mass']) if creator_state['mass'] else 1
        radius = float(creator_state['radius']) if creator_state['radius'] else 1
        calc_density = calculate_density(mass, radius)
        density_text = small_font.render(f"Calculated Density: {calc_density:.3f}", True, (100, 255, 100))
        display.blit(density_text, (label_x, field_start_y + field_spacing * 3 - 20))
    except:
        pass
    
    type_y = field_start_y + field_spacing * 3 + 10
    type_label = label_font.render("Type:", True, (200, 200, 200))
    display.blit(type_label, (label_x, type_y + 5))
    
    type_rect = pygame.Rect(input_x, type_y, input_width, field_height)
    pygame.draw.rect(display, (60, 60, 70), type_rect)
    pygame.draw.rect(display, (150, 150, 150), type_rect, 2)
    
    planet_types = {0: 'Solid Planet', 1: 'Gas Giant', 2: 'Star', 3: 'Black Hole'}
    type_text = label_font.render(planet_types[creator_state['type']], True, (255, 255, 255))
    display.blit(type_text, (type_rect.x + 10, type_rect.y + 5))
    
    arrow_points = [
        (type_rect.right - 30, type_rect.centery - 5),
        (type_rect.right - 20, type_rect.centery + 5),
        (type_rect.right - 10, type_rect.centery - 5)
    ]
    pygame.draw.polygon(display, (150, 150, 150), arrow_points)
    
    creator_state['type_rect'] = type_rect
    
    color_y = type_y + 70
    color_label = label_font.render("Color:", True, (200, 200, 200))
    display.blit(color_label, (label_x, color_y))
    
    color_box_rect = pygame.Rect(input_x, color_y, 80, 80)
    pygame.draw.rect(display, creator_state['color'], color_box_rect)
    pygame.draw.rect(display, (150, 150, 150), color_box_rect, 2)
    
    slider_x = input_x + 100
    slider_width = 200
    slider_height = 15
    
    rgb_labels = ['R', 'G', 'B']
    for i, (label, value) in enumerate(zip(rgb_labels, creator_state['color'])):
        slider_y = color_y + i * 25
        
        slider_label = small_font.render(f"{label}: {value}", True, (200, 200, 200))
        display.blit(slider_label, (slider_x, slider_y))
        
        slider_rect = pygame.Rect(slider_x + 70, slider_y, slider_width, slider_height)
        pygame.draw.rect(display, (60, 60, 70), slider_rect)
        pygame.draw.rect(display, (150, 150, 150), slider_rect, 1)
        
        handle_x = slider_rect.x + int((value / 255) * slider_width)
        handle_rect = pygame.Rect(handle_x - 5, slider_rect.y - 3, 10, slider_height + 6)
        pygame.draw.rect(display, (200, 200, 200), handle_rect)
        
        if 'sliders' not in creator_state:
            creator_state['sliders'] = {}
        creator_state['sliders'][i] = slider_rect
    
    button_y = panel_y + panel_height - 70
    create_button = pygame.Rect(panel_x + 100, button_y, 150, 45)
    cancel_button = pygame.Rect(panel_x + 350, button_y, 150, 45)
    
    pygame.draw.rect(display, (50, 150, 50), create_button)
    pygame.draw.rect(display, (150, 150, 150), create_button, 2)
    create_text = creator_font.render("Create", True, (255, 255, 255))
    create_text_rect = create_text.get_rect(center=create_button.center)
    display.blit(create_text, create_text_rect)
    
    pygame.draw.rect(display, (150, 50, 50), cancel_button)
    pygame.draw.rect(display, (150, 150, 150), cancel_button, 2)
    cancel_text = creator_font.render("Cancel", True, (255, 255, 255))
    cancel_text_rect = cancel_text.get_rect(center=cancel_button.center)
    display.blit(cancel_text, cancel_text_rect)

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
            
            if 'dropdown_items' not in creator_state:
                creator_state['dropdown_items'] = {}
            creator_state['dropdown_items'][type_id] = dropdown_item_rect
    
    creator_state['create_button'] = create_button
    creator_state['cancel_button'] = cancel_button
    creator_state['input_fields'] = input_fields

def handle_creator_mouse_click(pos):
    if not creator_active:
        return False
    
    if 'input_fields' in creator_state:
        clicked_any = False
        for field_name, field_info in creator_state['input_fields'].items():
            if 'rect' in field_info and field_info['rect'].collidepoint(pos):
                creator_state['active_field'] = field_name
                clicked_any = True
            
        if not clicked_any:
            creator_state['active_field'] = None
    
    if 'type_rect' in creator_state and creator_state['type_rect'].collidepoint(pos):
        creator_state['dropdown_open'] = not creator_state['dropdown_open']
        return True
    
    if creator_state['dropdown_open'] and 'dropdown_items' in creator_state:
        for type_id, rect in creator_state['dropdown_items'].items():
            if rect.collidepoint(pos):
                creator_state['type'] = type_id
                creator_state['dropdown_open'] = False
                return True
    else:
        creator_state['dropdown_open'] = False
    
    if 'sliders' in creator_state:
        for i, slider_rect in creator_state['sliders'].items():
            if slider_rect.collidepoint(pos):
                creator_state['dragging_slider'] = i
                rel_x = pos[0] - slider_rect.x
                new_value = max(0, min(255, int((rel_x / slider_rect.width) * 255)))
                creator_state['color'][i] = new_value
                return True
    
    if 'create_button' in creator_state and creator_state['create_button'].collidepoint(pos):
        create_planet_from_creator()
        return True
    
    if 'cancel_button' in creator_state and creator_state['cancel_button'].collidepoint(pos):
        close_planet_creator()
        return True
    
    return True

def handle_creator_mouse_drag(pos):
    if not creator_active:
        return
    
    if creator_state['dragging_slider'] is not None and 'sliders' in creator_state:
        i = creator_state['dragging_slider']
        slider_rect = creator_state['sliders'][i]
        rel_x = pos[0] - slider_rect.x
        new_value = max(0, min(255, int((rel_x / slider_rect.width) * 255)))
        creator_state['color'][i] = new_value

def handle_creator_mouse_release():
    if creator_active:
        creator_state['dragging_slider'] = None

def handle_creator_keypress(event):
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
        if active == 'name':
            creator_state[active] += event.unicode
        elif event.unicode.isdigit() or event.unicode == '.':
            creator_state[active] += event.unicode
    
    return True 

# ==================== PLANET SELECTOR MENU ====================

def open_planet_selector():
    global selector_active, paused, selector_scroll_y
    selector_active = True
    selector_scroll_y = 0
    if not paused:
        toggle_pause()

def close_planet_selector():
    global selector_active, selector_selected_planet
    selector_active = False

def draw_planet_selector():
    global selector_scroll_y, selector_max_scroll
    
    if not selector_active:
        return
    
    overlay = pygame.Surface((winSize[0], winSize[1]))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    display.blit(overlay, (0, 0))
    
    panel_width = 700
    panel_height = 500
    panel_x = (winSize[0] - panel_width) // 2
    panel_y = (winSize[1] - panel_height) // 2
    panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
    
    pygame.draw.rect(display, (40, 40, 50), panel_rect)
    pygame.draw.rect(display, (100, 150, 255), panel_rect, 3)
    
    title_font = pygame.font.Font(None, 36)
    item_font = pygame.font.Font(None, 28)
    small_font = pygame.font.Font(None, 22)
    
    # Title
    title = title_font.render("Select Planet to Spawn (Click to place)", True, (255, 255, 255))
    title_rect = title.get_rect(centerx=panel_rect.centerx, y=panel_y + 15)
    display.blit(title, title_rect)
    
    # Categories
    built_in = ["sun", "earth", "venus", "mars", "jupiter", "blackhole"]
    custom = [name for name in planet_templates.keys() if name not in built_in]
    
    # Scrollable list area
    list_area_x = panel_x + 20
    list_area_y = panel_y + 60
    list_area_width = panel_width - 60
    list_area_height = panel_height - 130
    list_area_rect = pygame.Rect(list_area_x, list_area_y, list_area_width, list_area_height)
    
    pygame.draw.rect(display, (60, 60, 70), list_area_rect)
    
    item_height = 60
    spacing = 5
    
    # Initialize storage for rects
    if not hasattr(draw_planet_selector, 'planet_rects'):
        draw_planet_selector.planet_rects = {}
    if not hasattr(draw_planet_selector, 'delete_buttons'):
        draw_planet_selector.delete_buttons = {}
    
    # Clear previous frame's rects
    draw_planet_selector.planet_rects.clear()
    draw_planet_selector.delete_buttons.clear()
    
    # Calculate total content height
    total_content_height = 0
    total_content_height += 40  # Built-in header
    total_content_height += len(built_in) * (item_height + spacing)
    if custom:
        total_content_height += 10
        total_content_height += 40
        total_content_height += len(custom) * (item_height + spacing)
    
    # Calculate max scroll
    selector_max_scroll = max(0, total_content_height - list_area_height)
    
    # Clamp scroll
    selector_scroll_y = max(0, min(selector_scroll_y, selector_max_scroll))
    
    # Create a surface for the scrollable content
    content_surface = pygame.Surface((list_area_width, max(list_area_height, total_content_height)))
    content_surface.fill((60, 60, 70))
    
    # Draw content on the surface
    y_pos = 0
    
    # Built-in planets header
    header = item_font.render("Built-in Planets:", True, (255, 200, 100))
    content_surface.blit(header, (0, y_pos))
    y_pos += 40
    
    # Built-in planets
    for planet_name in built_in:
        planet_data = planet_templates[planet_name]
        item_rect_local = pygame.Rect(0, y_pos, list_area_width - 20, item_height)
        
        # Item background
        pygame.draw.rect(content_surface, (50, 50, 60), item_rect_local)
        pygame.draw.rect(content_surface, (150, 150, 150), item_rect_local, 2)
        
        # Color preview
        color_box = pygame.Rect(10, y_pos + 10, 40, 40)
        pygame.draw.rect(content_surface, planet_data['col'], color_box)
        pygame.draw.rect(content_surface, (150, 150, 150), color_box, 1)
        
        # Planet info
        name_text = item_font.render(planet_name.capitalize(), True, (255, 255, 255))
        content_surface.blit(name_text, (65, y_pos + 5))
        
        type_names = {0: 'Solid', 1: 'Gas', 2: 'Star', 3: 'Black Hole'}
        info_text = small_font.render(
            f"Type: {type_names[planet_data['type']]} | Mass: {planet_data['mass']:.2f} EM | Radius: {planet_data['rad']:.2f} ER",
            True, (200, 200, 200)
        )
        content_surface.blit(info_text, (65, y_pos + 30))
        
        # Store rect for click detection (in screen coordinates)
        actual_y = list_area_y + y_pos - selector_scroll_y
        item_rect_screen = pygame.Rect(list_area_x, actual_y, list_area_width - 20, item_height)
        
        # Only store if visible
        if actual_y + item_height > list_area_y and actual_y < list_area_y + list_area_height:
            draw_planet_selector.planet_rects[planet_name] = item_rect_screen
        
        y_pos += item_height + spacing
    
    # Custom planets
    if custom:
        y_pos += 10
        header = item_font.render("Custom Planets:", True, (100, 255, 200))
        content_surface.blit(header, (0, y_pos))
        y_pos += 40
        
        for planet_name in custom:
            planet_data = planet_templates[planet_name]
            item_rect_local = pygame.Rect(0, y_pos, list_area_width - 60, item_height)
            
            # Item background
            pygame.draw.rect(content_surface, (50, 50, 60), item_rect_local)
            pygame.draw.rect(content_surface, (150, 150, 150), item_rect_local, 2)
            
            # Color preview
            color_box = pygame.Rect(10, y_pos + 10, 40, 40)
            pygame.draw.rect(content_surface, planet_data['col'], color_box)
            pygame.draw.rect(content_surface, (150, 150, 150), color_box, 1)
            
            # Planet info
            name_text = item_font.render(planet_name, True, (255, 255, 255))
            content_surface.blit(name_text, (65, y_pos + 5))
            
            type_names = {0: 'Solid', 1: 'Gas', 2: 'Star', 3: 'Black Hole'}
            info_text = small_font.render(
                f"Type: {type_names[planet_data['type']]} | Mass: {planet_data['mass']:.2f} EM | Radius: {planet_data['rad']:.2f} ER",
                True, (200, 200, 200)
            )
            content_surface.blit(info_text, (65, y_pos + 30))
            
            # Delete button (on content surface)
            delete_button_local = pygame.Rect(list_area_width - 55, y_pos + 10, 35, 40)
            pygame.draw.rect(content_surface, (150, 50, 50), delete_button_local)
            pygame.draw.rect(content_surface, (200, 200, 200), delete_button_local, 1)
            delete_text = item_font.render("X", True, (255, 255, 255))
            delete_text_rect = delete_text.get_rect(center=delete_button_local.center)
            content_surface.blit(delete_text, delete_text_rect)
            
            # Store rects for click detection (in screen coordinates)
            actual_y = list_area_y + y_pos - selector_scroll_y
            item_rect_screen = pygame.Rect(list_area_x, actual_y, list_area_width - 60, item_height)
            delete_button_screen = pygame.Rect(list_area_x + list_area_width - 55, actual_y + 10, 35, 40)
            
            # Only store if visible
            if actual_y + item_height > list_area_y and actual_y < list_area_y + list_area_height:
                draw_planet_selector.planet_rects[planet_name] = item_rect_screen
                draw_planet_selector.delete_buttons[planet_name] = delete_button_screen
            
            y_pos += item_height + spacing
    
    # Blit the scrolled portion of content surface to display
    display.blit(content_surface, list_area_rect.topleft, 
                 (0, selector_scroll_y, list_area_width, list_area_height))
    
    # Draw scrollbar if content is scrollable
    if selector_max_scroll > 0:
        scrollbar_x = list_area_x + list_area_width + 5
        scrollbar_y = list_area_y
        scrollbar_width = 15
        scrollbar_height = list_area_height
        
        # Scrollbar track
        scrollbar_track = pygame.Rect(scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_height)
        pygame.draw.rect(display, (60, 60, 70), scrollbar_track)
        pygame.draw.rect(display, (100, 100, 100), scrollbar_track, 1)
        
        # Scrollbar handle
        handle_height = max(30, int((list_area_height / total_content_height) * scrollbar_height))
        handle_y = scrollbar_y + int((selector_scroll_y / selector_max_scroll) * (scrollbar_height - handle_height))
        
        scrollbar_handle = pygame.Rect(scrollbar_x, handle_y, scrollbar_width, handle_height)
        
        # Highlight handle on hover
        mouse_pos = pygame.mouse.get_pos()
        if scrollbar_handle.collidepoint(mouse_pos) or selector_dragging_scrollbar:
            pygame.draw.rect(display, (120, 150, 200), scrollbar_handle)
        else:
            pygame.draw.rect(display, (100, 120, 180), scrollbar_handle)
        
        pygame.draw.rect(display, (150, 150, 150), scrollbar_handle, 1)
        
        # Store scrollbar handle for interaction
        draw_planet_selector.scrollbar_handle = scrollbar_handle
        draw_planet_selector.scrollbar_track = scrollbar_track
    else:
        draw_planet_selector.scrollbar_handle = None
        draw_planet_selector.scrollbar_track = None
    
    # Close button
    close_button = pygame.Rect(panel_x + panel_width - 120, panel_y + panel_height - 50, 100, 40)
    pygame.draw.rect(display, (150, 50, 50), close_button)
    pygame.draw.rect(display, (200, 200, 200), close_button, 2)
    close_text = item_font.render("Close", True, (255, 255, 255))
    close_text_rect = close_text.get_rect(center=close_button.center)
    display.blit(close_text, close_text_rect)
    
    draw_planet_selector.close_button = close_button

def handle_selector_mouse_click(pos):
    global selector_selected_planet, selector_dragging_scrollbar, selector_drag_offset
    
    if not selector_active:
        return False
    
    # Check scrollbar handle click
    if hasattr(draw_planet_selector, 'scrollbar_handle') and draw_planet_selector.scrollbar_handle:
        if draw_planet_selector.scrollbar_handle.collidepoint(pos):
            selector_dragging_scrollbar = True
            selector_drag_offset = pos[1] - draw_planet_selector.scrollbar_handle.y
            return True
    
    # Check close button
    if hasattr(draw_planet_selector, 'close_button'):
        if draw_planet_selector.close_button.collidepoint(pos):
            close_planet_selector()
            return True
    
    # Check delete buttons (custom planets only)
    if hasattr(draw_planet_selector, 'delete_buttons'):
        for planet_name, button_rect in draw_planet_selector.delete_buttons.items():
            if button_rect.collidepoint(pos):
                # Delete from database and templates
                if delete_custom_planet_from_db(planet_name):
                    if planet_name in planet_templates:
                        del planet_templates[planet_name]
                        add_console_message(f"Deleted {planet_name}", 2000, (255, 150, 0))
                return True
    
    # Check planet selection
    if hasattr(draw_planet_selector, 'planet_rects'):
        for planet_name, rect in draw_planet_selector.planet_rects.items():
            if rect.collidepoint(pos):
                selector_selected_planet = planet_name
                close_planet_selector()
                add_console_message(f"Click to place {planet_name}", 3000, (100, 255, 200))
                return True
    
    return True

def handle_selector_mouse_drag(pos):
    global selector_scroll_y, selector_dragging_scrollbar
    
    if not selector_active or not selector_dragging_scrollbar:
        return
    
    if hasattr(draw_planet_selector, 'scrollbar_track') and draw_planet_selector.scrollbar_track:
        track = draw_planet_selector.scrollbar_track
        handle = draw_planet_selector.scrollbar_handle
        
        if handle:
            # Calculate new handle position
            new_handle_y = pos[1] - selector_drag_offset
            
            # Clamp to track bounds
            new_handle_y = max(track.y, min(new_handle_y, track.bottom - handle.height))
            
            # Calculate scroll position from handle position
            scroll_ratio = (new_handle_y - track.y) / (track.height - handle.height)
            selector_scroll_y = int(scroll_ratio * selector_max_scroll)

def handle_selector_mouse_release():
    global selector_dragging_scrollbar
    selector_dragging_scrollbar = False

def handle_selector_scroll(event):
    global selector_scroll_y
    
    if not selector_active:
        return
    
    # Scroll with mouse wheel
    if event.type == pygame.MOUSEWHEEL:
        scroll_speed = 30
        selector_scroll_y -= event.y * scroll_speed
        selector_scroll_y = max(0, min(selector_scroll_y, selector_max_scroll))

# ==================== OTHER DRAW FUNCTIONS ====================

def draw_pause_overlay():
    if paused and not creator_active and not selector_active:
        overlay = pygame.Surface((winSize[0], winSize[1]))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        display.blit(overlay, (0, 0))
        
        pause_font = pygame.font.Font(None, 100)
        pause_text = pause_font.render("PAUSED", True, (255, 255, 255))
        pause_rect = pause_text.get_rect(center=(winSize[0]//2, winSize[1]//2))
        display.blit(pause_text, pause_rect)
        
        inst_font = pygame.font.Font(None, 36)
        inst_text = inst_font.render("Press SPACE or click >> to continue", True, (200, 200, 200))
        inst_rect = inst_text.get_rect(center=(winSize[0]//2, winSize[1]//2 + 80))
        display.blit(inst_text, inst_rect)

def draw_warning():
    global warning_message, warning_start_time
    
    if warning_message:
        current_time = pygame.time.get_ticks()
        elapsed = current_time - warning_start_time
        
        if elapsed > warning_duration:
            warning_message = ""
            warning_start_time = 0
            return
        
        flash_interval = 500
        if (elapsed // flash_interval) % 2 == 0:
            warning_font = pygame.font.Font(None, 72)
            text = warning_font.render(warning_message, True, (255, 255, 0))
            
            text_rect = text.get_rect(center=(winSize[0]//2, winSize[1]//2))
            padding = 20
            bg_rect = pygame.Rect(
                text_rect.x - padding,
                text_rect.y - padding,
                text_rect.width + padding * 2,
                text_rect.height + padding * 2
            )
            
            pygame.draw.rect(display, (200, 0, 0), bg_rect)
            pygame.draw.rect(display, (255, 255, 0), bg_rect, 3)
            
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
                    schwarzschild_rad = (2 * absorber["mass"] * G) / (C ** 2)
                    if schwarzschild_rad < 5:
                        show_warning("BH Radius too Small: Sim is Unstable")
                        to_delete.add(absorber_key)
                    absorber['rad'] = max(5, schwarzschild_rad)
                break  
    
    for p1 in names:
        if p1 not in data or p1 in to_delete:
            continue
        planet = data[p1]
        
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

            if dist > planet['rad'] + other['rad']:
                accel = G * other['mass'] / (dist ** 2)
                planet['vel'][0] += accel * dx / dist
                planet['vel'][1] += accel * dy / dist
        
        planet['pos'][0] += planet['vel'][0]
        planet['pos'][1] += planet['vel'][1]
    
    for p in to_delete:
        if p in data:
            del data[p]

# ==================== MAIN LOOP ====================

async def main():
    global selector_selected_planet, paused
    
    run = True
    frame_count = 0
    
    # Initialize database and load custom planets
    initialize_database()
    load_custom_planets_from_db()
    
    spawn_planet("sun", (500, 300))
    
    while run:
        display.fill((0, 0, 0))
        
        draw_stars()
        draw_planets()
        draw_warning()

        if not paused and not creator_active and not selector_active:
            update_planets()
            frame_count += 1
        
        draw_console()

        debug_text = font.render(f"Running | Planets: {len(data)} | Frame: {frame_count}", True, (0, 255, 0))
        display.blit(debug_text, (10, 10))
        
        inst_text = font.render("E,V,M,J,S,B=spawn | P=menu | C=create", True, (255, 255, 255))
        display.blit(inst_text, (10, 550))
        
        draw_pause_overlay()
        draw_pause_button()
        draw_planet_creator_overlay()
        draw_planet_selector()

        clock.tick(fps)
        pygame.display.update()
        
        for event in pygame.event.get():
            if event.type == QUIT:
                run = False
                
            if event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    # Handle planet placement from selector
                    if selector_selected_planet:
                        spawn_planet(selector_selected_planet, event.pos)
                        selector_selected_planet = None
                        if paused:
                            toggle_pause()
                        continue
                    
                    # Handle UI clicks
                    if selector_active:
                        if handle_selector_mouse_click(event.pos):
                            continue
                    
                    if creator_active:
                        if handle_creator_mouse_click(event.pos):
                            continue
                    
                    handle_pause_click(event.pos)

            if event.type == MOUSEMOTION:
                if selector_active:
                    handle_selector_mouse_drag(event.pos)
                if creator_active:
                    handle_creator_mouse_drag(event.pos)
            
            if event.type == MOUSEBUTTONUP:
                if selector_active:
                    handle_selector_mouse_release()
                if creator_active:
                    handle_creator_mouse_release() 

            if event.type == KEYDOWN:
                if creator_active:
                    if handle_creator_keypress(event):
                        continue
                
                if event.key == K_SPACE:
                    toggle_pause()
                elif event.key == K_c:
                    open_planet_creator()
                elif event.key == K_p:
                    open_planet_selector()
                else:
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
            
            # Mouse wheel scrolling for selector
            if event.type == pygame.MOUSEWHEEL:
                if selector_active:
                    handle_selector_scroll(event)
                        
        await asyncio.sleep(0)
    pygame.quit()

asyncio.run(main())