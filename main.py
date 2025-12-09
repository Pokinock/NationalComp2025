import pygame
import sys
import traceback
import math
import random
# --- Constants & Configuration ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
# Layout
GAME_VIEW_WIDTH = int(SCREEN_WIDTH * 0.6)
EDITOR_WIDTH = SCREEN_WIDTH - GAME_VIEW_WIDTH
HUD_HEIGHT = 40
GRID_SIZE = 10
# Calculate TILE_SIZE to fit within the remaining height and width
TILE_SIZE = min(GAME_VIEW_WIDTH // GRID_SIZE, (SCREEN_HEIGHT - HUD_HEIGHT) // GRID_SIZE)
GRID_OFFSET_X = (GAME_VIEW_WIDTH - (GRID_SIZE * TILE_SIZE)) // 2
GRID_OFFSET_Y = HUD_HEIGHT + ((SCREEN_HEIGHT - HUD_HEIGHT) - (GRID_SIZE * TILE_SIZE)) // 2
# Colors
COLOR_BG = (30, 30, 30)          # #1E1E1E
COLOR_GRID = (51, 51, 51)        # #333333
COLOR_WALL = (64, 64, 64)        # #404040
COLOR_PLAYER = (0, 255, 255)     # #00FFFF (Cyan Neon)
COLOR_GOAL = (0, 255, 0)         # #00FF00
COLOR_TEXT = (220, 220, 220)
COLOR_COMMENT = (100, 160, 100)
COLOR_KEYWORD = (86, 156, 214)   # VS Code Blue
COLOR_ERROR = (255, 100, 100)
COLOR_SUCCESS = (100, 255, 100)
COLOR_EDITOR_BG = (30, 30, 30)
COLOR_EDITOR_LINE_NUM = (100, 100, 100)
COLOR_CURSOR = (200, 200, 200)
COLOR_SELECTION = (38, 79, 120)  # VS Code Selection
COLOR_CONSOLE_BG = (20, 20, 20)
COLOR_HUD_BG = (25, 25, 25)
COLOR_HUD_TEXT = (255, 255, 255)
COLOR_BUTTON = (50, 50, 50)
COLOR_BUTTON_HOVER = (70, 70, 70)
COLOR_BUTTON_TEXT = (200, 200, 200)
COLOR_PLAY_BUTTON = (40, 100, 40)
COLOR_PLAY_BUTTON_HOVER = (60, 150, 60)
COLOR_KEY = (255, 215, 0)       # Gold
COLOR_DOOR = (139, 69, 19)      # SaddleBrown
COLOR_SCROLLBAR = (80, 80, 80)
COLOR_SCROLLBAR_HOVER = (100, 100, 100)
COLOR_SCROLLBAR_ACTIVE = (120, 120, 120)
COLOR_PATH_TRACK = (50, 200, 50, 150)  # Green with transparency for path tracking
COLOR_PATH_TRACK_VISITED = (100, 255, 100, 100)  # Lighter green for visited cells
# Game Rules
MAX_LINES = 50 
STARTING_COINS = 200
LINE_COST = 10
ANIMATION_DURATION_MS = 400 
LEVEL_REWARD_BASE = 200
# --- Helper Functions ---
def cubic_bezier(t):
    # Ease in-out cubic
    return t * t * (3.0 - 2.0 * t)
def lerp(a, b, t):
    return a + (b - a) * t
# --- Classes ---
class Button:
    def __init__(self, x, y, width, height, text, callback, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.font = font
        self.hovered = False
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.hovered:
                self.callback()
                return True
        return False
    def draw(self, surface):
        color = COLOR_BUTTON_HOVER if self.hovered else COLOR_BUTTON
        if self.text == "RUN":
             color = COLOR_PLAY_BUTTON_HOVER if self.hovered else COLOR_PLAY_BUTTON
        elif self.text == "DELETE":
             color = COLOR_ERROR if self.hovered else (150, 50, 50)
             
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, COLOR_GRID, self.rect, 1) # Border
        
        text_surf = self.font.render(self.text, True, COLOR_BUTTON_TEXT)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
class Console:
    def __init__(self, x, y, width, height, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.logs = [] # List of (text, color)
        self.max_logs = 10
    def log(self, message, color=COLOR_TEXT):
        self.logs.append((message, color))
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)
    
    def clear(self):
        self.logs = []
    def draw(self, surface):
        pygame.draw.rect(surface, COLOR_CONSOLE_BG, self.rect)
        pygame.draw.line(surface, COLOR_GRID, (self.rect.left, self.rect.top), (self.rect.right, self.rect.top))
        
        y = self.rect.top + 5
        for text, color in self.logs:
            surf = self.font.render(text, True, color)
            surface.blit(surf, (self.rect.left + 5, y))
            y += 20
class PathTracker:
    def __init__(self, game_map):
        self.map = game_map
        self.current_path = []
        self.visited_cells = set()
        self.predicted_path = []
        self.last_code_hash = None
        
    def simulate_code(self, code_str):
        """Simulate the code to predict the path"""
        try:
            # Create a simulation state
            sim_x, sim_y = self.map.start_pos
            sim_dir = 1  # Start facing East
            
            # Keep track of visited positions
            visited = [(sim_x, sim_y)]
            
            # Define the environment for exec
            def move():
                nonlocal sim_x, sim_y
                dx, dy = 0, 0
                if sim_dir == 0: dy = -1
                elif sim_dir == 1: dx = 1
                elif sim_dir == 2: dy = 1
                elif sim_dir == 3: dx = -1
                
                target_x, target_y = sim_x + dx, sim_y + dy
                if not self.map.is_wall(target_x, target_y):
                    sim_x, sim_y = target_x, target_y
                    visited.append((sim_x, sim_y))
                return True
            
            def turn_left():
                nonlocal sim_dir
                sim_dir = (sim_dir - 1) % 4
                return True
            
            def turn_right():
                nonlocal sim_dir
                sim_dir = (sim_dir + 1) % 4
                return True
            
            def wall_ahead():
                dx, dy = 0, 0
                if sim_dir == 0: dy = -1
                elif sim_dir == 1: dx = 1
                elif sim_dir == 2: dy = 1
                elif sim_dir == 3: dx = -1
                return self.map.is_wall(sim_x + dx, sim_y + dy)
            
            def path_left():
                left_dir = (sim_dir - 1) % 4
                dx, dy = 0, 0
                if left_dir == 0: dy = -1
                elif left_dir == 1: dx = 1
                elif left_dir == 2: dy = 1
                elif left_dir == 3: dx = -1
                return not self.map.is_wall(sim_x + dx, sim_y + dy)
            
            def path_right():
                right_dir = (sim_dir + 1) % 4
                dx, dy = 0, 0
                if right_dir == 0: dy = -1
                elif right_dir == 1: dx = 1
                elif right_dir == 2: dy = 1
                elif right_dir == 3: dx = -1
                return not self.map.is_wall(sim_x + dx, sim_y + dy)
            
            # Create execution environment
            env = {
                'move': move,
                'turn_left': turn_left,
                'turn_right': turn_right,
                'wall_ahead': wall_ahead,
                'path_left': path_left,
                'path_right': path_right,
                'range': range,
                'print': lambda x: None
            }
            
            # Execute the code
            exec(code_str, {"__builtins__": {}}, env)
            
            # Update predicted path
            self.predicted_path = visited
            return True
            
        except Exception as e:
            # If code has errors, clear predicted path
            self.predicted_path = []
            return False
    
    def update_from_player(self, player_pos):
        """Update tracking based on actual player position"""
        self.current_path.append(player_pos)
        self.visited_cells.add(player_pos)
    
    def reset(self):
        """Reset tracking"""
        self.current_path = []
        self.visited_cells = set()
        self.predicted_path = []
        self.last_code_hash = None
    
    def draw(self, surface, tile_size, offset_x, offset_y):
        """Draw the path tracking visualization"""
        # Draw predicted path (green)
        for i, (x, y) in enumerate(self.predicted_path):
            # Calculate position on screen
            screen_x = offset_x + x * tile_size + tile_size // 2
            screen_y = offset_y + y * tile_size + tile_size // 2
            
            # Draw a circle for each predicted position
            radius = tile_size // 6
            color = COLOR_PATH_TRACK
            
            # Make the path gradient (darker at start, lighter at end)
            if len(self.predicted_path) > 1:
                intensity = i / len(self.predicted_path)
                r = int(50 + 150 * intensity)
                g = int(200 + 55 * intensity)
                b = 50
                color = (r, g, b, 150)
            
            # Create a temporary surface for alpha blending
            circle_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(circle_surf, color, (radius, radius), radius)
            surface.blit(circle_surf, (screen_x - radius, screen_y - radius))
            
            # Draw connecting lines between consecutive points
            if i > 0:
                prev_x, prev_y = self.predicted_path[i-1]
                prev_screen_x = offset_x + prev_x * tile_size + tile_size // 2
                prev_screen_y = offset_y + prev_y * tile_size + tile_size // 2
                
                # Draw line with gradient
                line_surf = pygame.Surface((tile_size * 2, tile_size * 2), pygame.SRCALPHA)
                pygame.draw.line(line_surf, color, 
                               (tile_size, tile_size),
                               (tile_size + (screen_x - prev_screen_x), tile_size + (screen_y - prev_screen_y)), 
                               max(2, tile_size // 8))
                surface.blit(line_surf, (prev_screen_x - tile_size, prev_screen_y - tile_size))
        
        # Draw visited cells (lighter green)
        for (x, y) in self.visited_cells:
            screen_x = offset_x + x * tile_size
            screen_y = offset_y + y * tile_size
            
            # Create a semi-transparent overlay for visited cells
            visited_surf = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
            visited_surf.fill((*COLOR_PATH_TRACK_VISITED[:3], 50))  # Very light overlay
            surface.blit(visited_surf, (screen_x, screen_y))
            
            # Draw a small marker in visited cells
            center_x = screen_x + tile_size // 2
            center_y = screen_y + tile_size // 2
            marker_size = tile_size // 8
            pygame.draw.circle(surface, COLOR_PATH_TRACK_VISITED[:3], 
                             (center_x, center_y), marker_size)
        
        # Draw current path (if player is moving)
        for i in range(1, len(self.current_path)):
            x1, y1 = self.current_path[i-1]
            x2, y2 = self.current_path[i]
            
            screen_x1 = offset_x + x1 * tile_size + tile_size // 2
            screen_y1 = offset_y + y1 * tile_size + tile_size // 2
            screen_x2 = offset_x + x2 * tile_size + tile_size // 2
            screen_y2 = offset_y + y2 * tile_size + tile_size // 2
            
            # Draw line for actual path taken
            pygame.draw.line(surface, (255, 255, 100, 200), 
                           (screen_x1, screen_y1), (screen_x2, screen_y2), 
                           max(3, tile_size // 6))
class TextEditor:
    def __init__(self, x, y, width, height, font):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.lines = ["move()"]
        self.cursor_row = 0
        self.cursor_col = 6
        self.scroll_y = 0
        self.selection_start = None # (row, col) or None
        self.line_height = 24
        
        # Scrolling variables
        self.scrollbar_width = 10
        self.scrollbar_rect = pygame.Rect(
            self.rect.right - self.scrollbar_width,
            self.rect.top,
            self.scrollbar_width,
            self.rect.height
        )
        self.scrollbar_handle_height = 100
        self.scrollbar_handle_rect = pygame.Rect(
            self.scrollbar_rect.left,
            self.scrollbar_rect.top,
            self.scrollbar_rect.width,
            self.scrollbar_handle_height
        )
        self.scrollbar_dragging = False
        self.scrollbar_hovered = False
        self.max_visible_lines = self.rect.height // self.line_height
        
        # Initialize clipboard support
        try:
            import tkinter
            self.tk_root = tkinter.Tk()
            self.tk_root.withdraw()
        except:
            self.tk_root = None
        # Autocomplete
        self.suggestions = []
        self.suggestion_index = 0
        self.autocomplete_keywords = ['move()', 'turn_left()', 'turn_right()', 'range()', 'for i in range():']
    
    def update_scrollbar(self):
        total_lines = len(self.lines)
        if total_lines <= self.max_visible_lines:
            self.scroll_y = 0
            self.scrollbar_handle_rect.top = self.scrollbar_rect.top
            self.scrollbar_handle_rect.height = self.scrollbar_rect.height
            return
        
        # Calculate scrollbar handle position and size
        visible_ratio = self.max_visible_lines / total_lines
        self.scrollbar_handle_height = max(20, int(self.scrollbar_rect.height * visible_ratio))
        
        # Calculate handle position based on scroll_y
        scroll_range = total_lines - self.max_visible_lines
        if scroll_range > 0:
            scroll_ratio = self.scroll_y / scroll_range
            max_top = self.scrollbar_rect.bottom - self.scrollbar_handle_height
            self.scrollbar_handle_rect.top = self.scrollbar_rect.top + int(scroll_ratio * (max_top - self.scrollbar_rect.top))
        else:
            self.scrollbar_handle_rect.top = self.scrollbar_rect.top
        
        self.scrollbar_handle_rect.height = self.scrollbar_handle_height
    
    def scroll_to_cursor(self):
        # Ensure cursor is visible
        if self.cursor_row < self.scroll_y:
            self.scroll_y = self.cursor_row
        elif self.cursor_row >= self.scroll_y + self.max_visible_lines:
            self.scroll_y = self.cursor_row - self.max_visible_lines + 1
        self.update_scrollbar()
    
    def handle_scrollbar_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            # Check if mouse is over scrollbar
            self.scrollbar_hovered = self.scrollbar_rect.collidepoint(event.pos)
            
            if self.scrollbar_dragging:
                # Calculate new scroll position based on mouse position
                mouse_y = event.pos[1]
                total_lines = len(self.lines)
                
                if total_lines > self.max_visible_lines:
                    # Calculate available movement range
                    handle_min_y = self.scrollbar_rect.top
                    handle_max_y = self.scrollbar_rect.bottom - self.scrollbar_handle_height
                    
                    # Clamp mouse position
                    new_handle_y = max(handle_min_y, min(mouse_y - self.scrollbar_drag_offset, handle_max_y))
                    
                    # Calculate scroll position
                    scroll_range = total_lines - self.max_visible_lines
                    scroll_ratio = (new_handle_y - handle_min_y) / (handle_max_y - handle_min_y)
                    self.scroll_y = int(scroll_ratio * scroll_range)
                    self.update_scrollbar()
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.scrollbar_rect.collidepoint(event.pos):
                if self.scrollbar_handle_rect.collidepoint(event.pos):
                    # Start dragging the handle
                    self.scrollbar_dragging = True
                    self.scrollbar_drag_offset = event.pos[1] - self.scrollbar_handle_rect.top
                else:
                    # Click on scrollbar track - jump to that position
                    total_lines = len(self.lines)
                    if total_lines > self.max_visible_lines:
                        # Calculate click position relative to scrollbar
                        click_ratio = (event.pos[1] - self.scrollbar_rect.top) / self.scrollbar_rect.height
                        scroll_range = total_lines - self.max_visible_lines
                        self.scroll_y = int(click_ratio * scroll_range)
                        self.scroll_y = max(0, min(self.scroll_y, scroll_range))
                        self.update_scrollbar()
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.scrollbar_dragging = False
        
        elif event.type == pygame.MOUSEWHEEL:
            # Scroll with mouse wheel
            self.scroll_y -= event.y * 3  # Scroll 3 lines per wheel tick
            total_lines = len(self.lines)
            self.scroll_y = max(0, min(self.scroll_y, total_lines - self.max_visible_lines))
            self.update_scrollbar()
            return True
        
        return False
    
    def clear(self):
        """Clear all text from editor"""
        self.lines = [""]
        self.cursor_row = 0
        self.cursor_col = 0
        self.scroll_y = 0
        self.selection_start = None
        self.update_scrollbar()
    
    def get_text(self):
        return "\n".join(self.lines)
    
    def set_text(self, text):
        self.lines = text.split('\n')
        self.cursor_row = min(len(self.lines)-1, self.cursor_row)
        self.cursor_col = min(len(self.lines[self.cursor_row]), self.cursor_col)
        self.scroll_to_cursor()
    
    def copy_to_clipboard(self, text):
        if self.tk_root:
            self.tk_root.clipboard_clear()
            self.tk_root.clipboard_append(text)
            self.tk_root.update()
    
    def get_from_clipboard(self):
        if self.tk_root:
            try:
                return self.tk_root.clipboard_get()
            except:
                return ""
        return ""
    
    def handle_input(self, event):
        # Handle scrollbar events first
        if self.handle_scrollbar_event(event):
            return
        
        if event.type == pygame.KEYDOWN:
            # Autocomplete Priority Handling
            if self.suggestions:
                if event.key == pygame.K_UP:
                    self.suggestion_index = (self.suggestion_index - 1) % len(self.suggestions)
                    return
                elif event.key == pygame.K_DOWN:
                    self.suggestion_index = (self.suggestion_index + 1) % len(self.suggestions)
                    return
                elif event.key == pygame.K_TAB or event.key == pygame.K_RETURN:
                    self.complete_suggestion()
                    self.scroll_to_cursor()
                    return
                elif event.key == pygame.K_ESCAPE:
                    self.suggestions = []
                    return
            
            # Modifiers
            ctrl = event.mod & pygame.KMOD_CTRL
            shift = event.mod & pygame.KMOD_SHIFT
            
            # Page Up/Down for scrolling
            if event.key == pygame.K_PAGEUP:
                self.scroll_y = max(0, self.scroll_y - self.max_visible_lines)
                self.update_scrollbar()
                return
            elif event.key == pygame.K_PAGEDOWN:
                total_lines = len(self.lines)
                self.scroll_y = min(total_lines - self.max_visible_lines, self.scroll_y + self.max_visible_lines)
                self.update_scrollbar()
                return
            
            # Navigation
            if event.key == pygame.K_UP:
                self.move_cursor(-1, 0, shift)
            elif event.key == pygame.K_DOWN:
                self.move_cursor(1, 0, shift)
            elif event.key == pygame.K_LEFT:
                if ctrl: self.move_word_left(shift)
                else: self.move_cursor(0, -1, shift)
            elif event.key == pygame.K_RIGHT:
                if ctrl: self.move_word_right(shift)
                else: self.move_cursor(0, 1, shift)
            elif event.key == pygame.K_HOME:
                self.move_to_line_start(shift)
            elif event.key == pygame.K_END:
                self.move_to_line_end(shift)
            
            # Editing
            elif event.key == pygame.K_BACKSPACE:
                self.backspace()
            elif event.key == pygame.K_DELETE:
                self.delete()
            elif event.key == pygame.K_RETURN:
                self.insert_newline()
            elif event.key == pygame.K_TAB:
                self.insert_text("    ")
            
            # Clipboard / Shortcuts
            elif ctrl and event.key == pygame.K_c:
                self.copy()
            elif ctrl and event.key == pygame.K_x:
                self.cut()
            elif ctrl and event.key == pygame.K_v:
                self.paste()
            elif ctrl and event.key == pygame.K_a:
                self.select_all()
            
            # Typing
            elif event.unicode and event.unicode.isprintable() and not ctrl:
                self.insert_text(event.unicode)
                self.update_suggestions()
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                # Calculate row
                rel_y = event.pos[1] - self.rect.top - 5
                row = rel_y // self.line_height + self.scroll_y
                self.cursor_row = max(0, min(len(self.lines) - 1, row))
                
                # Calculate col (Assuming fixed width font approx)
                char_w = self.font.size(' ')[0]
                rel_x = event.pos[0] - self.rect.left - 40 # 40 is margin
                col = round(rel_x / char_w)
                self.cursor_col = max(0, min(len(self.lines[self.cursor_row]), col))
                
                # Reset selection on click
                self.selection_start = None
                self.scroll_to_cursor()
    
    def move_cursor(self, d_row, d_col, select):
        self.suggestions = [] # Clear suggestions on move
        if select and self.selection_start is None:
            self.selection_start = (self.cursor_row, self.cursor_col)
        elif not select:
            self.selection_start = None
        
        # Vertical
        if d_row != 0:
            self.cursor_row = max(0, min(len(self.lines) - 1, self.cursor_row + d_row))
            self.cursor_col = min(len(self.lines[self.cursor_row]), self.cursor_col)
            self.scroll_to_cursor()
        
        # Horizontal
        if d_col != 0:
            self.cursor_col += d_col
            if self.cursor_col < 0:
                if self.cursor_row > 0:
                    self.cursor_row -= 1
                    self.cursor_col = len(self.lines[self.cursor_row])
                    self.scroll_to_cursor()
                else:
                    self.cursor_col = 0
            elif self.cursor_col > len(self.lines[self.cursor_row]):
                if self.cursor_row < len(self.lines) - 1:
                    self.cursor_row += 1
                    self.cursor_col = 0
                    self.scroll_to_cursor()
                else:
                    self.cursor_col = len(self.lines[self.cursor_row])
    
    def move_word_left(self, select):
        # Simple word jump implementation
        line = self.lines[self.cursor_row]
        if self.cursor_col == 0:
            self.move_cursor(0, -1, select)
            return
            
        i = self.cursor_col - 1
        while i > 0 and line[i] == ' ': i -= 1 # Skip spaces
        while i > 0 and line[i] != ' ': i -= 1 # Skip word
        self.cursor_col = i if i == 0 else i + 1
        if select and self.selection_start is None: self.selection_start = (self.cursor_row, self.cursor_col) # Fix selection logic later if needed
    
    def move_word_right(self, select):
        line = self.lines[self.cursor_row]
        if self.cursor_col >= len(line):
            self.move_cursor(0, 1, select)
            return
            
        i = self.cursor_col
        while i < len(line) and line[i] != ' ': i += 1
        while i < len(line) and line[i] == ' ': i += 1
        self.cursor_col = i
    
    def move_to_line_start(self, select):
        if select and self.selection_start is None: self.selection_start = (self.cursor_row, self.cursor_col)
        elif not select: self.selection_start = None
        self.cursor_col = 0
    
    def move_to_line_end(self, select):
        if select and self.selection_start is None: self.selection_start = (self.cursor_row, self.cursor_col)
        elif not select: self.selection_start = None
        self.cursor_col = len(self.lines[self.cursor_row])
    
    def get_selection_range(self):
        if self.selection_start is None: return None
        
        r1, c1 = self.selection_start
        r2, c2 = self.cursor_row, self.cursor_col
        
        if (r1, c1) > (r2, c2):
            return (r2, c2), (r1, c1)
        return (r1, c1), (r2, c2)
    
    def delete_selection(self):
        sel = self.get_selection_range()
        if not sel: return False
        
        (r1, c1), (r2, c2) = sel
        
        if r1 == r2:
            self.lines[r1] = self.lines[r1][:c1] + self.lines[r1][c2:]
        else:
            self.lines[r1] = self.lines[r1][:c1] + self.lines[r2][c2:]
            del self.lines[r1+1:r2+1]
        
        self.cursor_row, self.cursor_col = r1, c1
        self.selection_start = None
        self.scroll_to_cursor()
        return True
    
    def backspace(self):
        if self.delete_selection(): 
            self.scroll_to_cursor()
            return
        
        if self.cursor_col > 0:
            line = self.lines[self.cursor_row]
            self.lines[self.cursor_row] = line[:self.cursor_col-1] + line[self.cursor_col:]
            self.cursor_col -= 1
            self.update_suggestions()
        elif self.cursor_row > 0:
            line = self.lines[self.cursor_row]
            prev_line = self.lines[self.cursor_row-1]
            self.cursor_col = len(prev_line)
            self.lines[self.cursor_row-1] = prev_line + line
            del self.lines[self.cursor_row]
            self.cursor_row -= 1
            self.update_suggestions()
        self.scroll_to_cursor()
    
    def delete(self):
        if self.delete_selection(): 
            self.scroll_to_cursor()
            return
        
        if self.cursor_col < len(self.lines[self.cursor_row]):
            line = self.lines[self.cursor_row]
            self.lines[self.cursor_row] = line[:self.cursor_col] + line[self.cursor_col+1:]
            self.update_suggestions()
        elif self.cursor_row < len(self.lines) - 1:
            line = self.lines[self.cursor_row]
            next_line = self.lines[self.cursor_row+1]
            self.lines[self.cursor_row] = line + next_line
            del self.lines[self.cursor_row+1]
            self.update_suggestions()
        self.scroll_to_cursor()
    
    def insert_text(self, text):
        self.delete_selection()
        
        lines_to_insert = text.split('\n')
        line = self.lines[self.cursor_row]
        
        prefix = line[:self.cursor_col]
        suffix = line[self.cursor_col:]
        
        if len(lines_to_insert) == 1:
            self.lines[self.cursor_row] = prefix + lines_to_insert[0] + suffix
            self.cursor_col += len(lines_to_insert[0])
        else:
            self.lines[self.cursor_row] = prefix + lines_to_insert[0]
            for i in range(1, len(lines_to_insert) - 1):
                self.lines.insert(self.cursor_row + i, lines_to_insert[i])
            self.lines.insert(self.cursor_row + len(lines_to_insert) - 1, lines_to_insert[-1] + suffix)
            self.cursor_row += len(lines_to_insert) - 1
            self.cursor_col = len(lines_to_insert[-1])
        
        self.scroll_to_cursor()
    
    def insert_newline(self):
        self.delete_selection()
        line = self.lines[self.cursor_row]
        indent = ""
        for char in line:
            if char == ' ': indent += ' '
            else: break
            
        # Auto-indent if line ends with :
        if line[:self.cursor_col].strip().endswith(':'):
            indent += "    "
            
        self.lines.insert(self.cursor_row + 1, indent + line[self.cursor_col:])
        self.lines[self.cursor_row] = line[:self.cursor_col]
        self.cursor_row += 1
        self.cursor_col = len(indent)
        self.scroll_to_cursor()
    
    def select_all(self):
        self.selection_start = (0, 0)
        self.cursor_row = len(self.lines) - 1
        self.cursor_col = len(self.lines[-1])
        self.scroll_to_cursor()
    
    def copy(self):
        sel = self.get_selection_range()
        if not sel: return
        (r1, c1), (r2, c2) = sel
        
        if r1 == r2:
            text = self.lines[r1][c1:c2]
        else:
            text = self.lines[r1][c1:] + "\n"
            for i in range(r1+1, r2):
                text += self.lines[i] + "\n"
            text += self.lines[r2][:c2]
        
        self.copy_to_clipboard(text)
    
    def cut(self):
        self.copy()
        self.delete_selection()
    
    def paste(self):
        text = self.get_from_clipboard()
        if text:
            self.insert_text(text)
    
    def update_suggestions(self):
        self.suggestions = []
        line = self.lines[self.cursor_row]
        if not line.strip(): return
        
        # Find word before cursor
        # Walk back from cursor until space or start
        start_col = self.cursor_col
        while start_col > 0 and line[start_col-1] not in ' \t():':
            start_col -= 1
            
        word = line[start_col:self.cursor_col]
        if not word: return
        
        for kw in self.autocomplete_keywords:
            if kw.startswith(word) and kw != word:
                self.suggestions.append(kw)
        
        self.suggestion_index = 0
    
    def complete_suggestion(self):
        if not self.suggestions: return
        
        suggestion = self.suggestions[self.suggestion_index]
        line = self.lines[self.cursor_row]
        
        # Find start of word
        start_col = self.cursor_col
        while start_col > 0 and line[start_col-1] not in ' \t():':
            start_col -= 1
            
        # Replace word with suggestion
        self.lines[self.cursor_row] = line[:start_col] + suggestion + line[self.cursor_col:]
        self.cursor_col = start_col + len(suggestion)
        self.suggestions = []
        self.scroll_to_cursor()
    
    def draw_suggestions(self, surface):
        if not self.suggestions: return
        
        # Position box near cursor
        # Calculate pixel position of cursor
        line = self.lines[self.cursor_row]
        cx = self.rect.left + 40 + self.font.size(line[:self.cursor_col])[0]
        cy = self.rect.top + 5 + (self.cursor_row - self.scroll_y + 1) * self.line_height
        
        box_w = 200
        box_h = len(self.suggestions) * 20 + 4
        
        # Ensure inside screen
        if cy + box_h > SCREEN_HEIGHT:
            cy -= (box_h + self.line_height)
            
        pygame.draw.rect(surface, (30, 30, 30), (cx, cy, box_w, box_h))
        pygame.draw.rect(surface, COLOR_GRID, (cx, cy, box_w, box_h), 1)
        
        for i, sugg in enumerate(self.suggestions):
            color = COLOR_SUCCESS if i == self.suggestion_index else COLOR_TEXT
            if i == self.suggestion_index:
                pygame.draw.rect(surface, (50, 50, 50), (cx + 1, cy + 2 + i*20, box_w - 2, 20))
            
            surf = self.font.render(sugg, True, color)
            surface.blit(surf, (cx + 5, cy + 2 + i*20))
    
    def draw(self, surface):
        pygame.draw.rect(surface, COLOR_EDITOR_BG, self.rect)
        
        # Draw visible lines only
        start_line = self.scroll_y
        end_line = min(start_line + self.max_visible_lines, len(self.lines))
        
        # Draw Selection
        sel = self.get_selection_range()
        if sel:
            (r1, c1), (r2, c2) = sel
            for r in range(r1, r2 + 1):
                if r < start_line or r >= end_line:
                    continue
                    
                y = self.rect.top + 5 + (r - start_line) * self.line_height
                line = self.lines[r]
                x_start = self.rect.left + 40 # Margin for line nums
                
                s_col = c1 if r == r1 else 0
                e_col = c2 if r == r2 else len(line) + 1 # +1 for newline highlight
                
                # Calculate pixel width
                p_start = self.font.size(line[:s_col])[0]
                p_width = self.font.size(line[s_col:e_col])[0]
                if e_col > len(line): p_width += 10 # Highlight newline
                
                pygame.draw.rect(surface, COLOR_SELECTION, (x_start + p_start, y, p_width, self.line_height))
        
        # Draw Text
        for i in range(start_line, end_line):
            line = self.lines[i]
            y = self.rect.top + 5 + (i - start_line) * self.line_height
            
            # Line Number
            num_surf = self.font.render(str(i+1), True, COLOR_EDITOR_LINE_NUM)
            surface.blit(num_surf, (self.rect.left + 5, y))
            
            # Syntax Highlighting (Simple)
            x = self.rect.left + 40
            
            # Comments
            if '#' in line:
                code_part, comment_part = line.split('#', 1)
                self.draw_syntax_line(surface, code_part, x, y)
                x += self.font.size(code_part)[0]
                
                comm_surf = self.font.render('#' + comment_part, True, COLOR_COMMENT)
                surface.blit(comm_surf, (x, y))
            else:
                self.draw_syntax_line(surface, line, x, y)
            
            # Cursor
            if i == self.cursor_row and pygame.time.get_ticks() % 1000 < 500:
                cx = self.rect.left + 40 + self.font.size(line[:self.cursor_col])[0]
                pygame.draw.rect(surface, COLOR_CURSOR, (cx, y, 2, self.line_height))
        
        # Draw scrollbar if needed
        if len(self.lines) > self.max_visible_lines:
            # Scrollbar background
            pygame.draw.rect(surface, COLOR_SCROLLBAR, self.scrollbar_rect)
            
            # Scrollbar handle
            handle_color = COLOR_SCROLLBAR_ACTIVE if self.scrollbar_dragging else (
                COLOR_SCROLLBAR_HOVER if self.scrollbar_hovered else COLOR_SCROLLBAR
            )
            pygame.draw.rect(surface, handle_color, self.scrollbar_handle_rect)
            pygame.draw.rect(surface, COLOR_GRID, self.scrollbar_handle_rect, 1)
        
        self.draw_suggestions(surface)
    
    def draw_syntax_line(self, surface, text, x, y):
        keywords = ['move', 'turn_left', 'turn_right', 'range', 'for', 'in', 'def', 'if', 'else']
        
        # Very basic tokenizer
        words = text.split(' ')
        curr_x = x
        for i, word in enumerate(words):
            clean_word = word.strip('():')
            color = COLOR_TEXT
            if clean_word in keywords:
                color = COLOR_KEYWORD
            
            surf = self.font.render(word, True, color)
            surface.blit(surf, (curr_x, y))
            curr_x += surf.get_width()
            if i < len(words) - 1:
                space = self.font.render(' ', True, COLOR_TEXT)
                surface.blit(space, (curr_x, y))
                curr_x += space.get_width()
class GameMap:
    def __init__(self, size=10):
        self.size = size
        # 0 = Floor, 1 = Wall
        self.grid = []
        self.start_pos = (1, 1)
        self.goal_pos = (size - 2, size - 2)
        self.keys = [] # List of positions
        self.doors = [] # List of positions
        self.generate_maze()
    
    def generate_maze(self, num_doors=0):
        # Initialize with walls
        self.grid = [[1 for _ in range(self.size)] for _ in range(self.size)]
        
        # Recursive Backtracker
        cells = []
        for y in range(1, self.size - 1, 2):
            for x in range(1, self.size - 1, 2):
                cells.append((x, y))
        
        stack = []
        start = (1, 1)
        self.grid[start[1]][start[0]] = 0
        stack.append(start)
        
        visited = {start}
        
        while stack:
            cx, cy = stack[-1]
            neighbors = []
            
            for dx, dy in [(0, -2), (2, 0), (0, 2), (-2, 0)]:
                nx, ny = cx + dx, cy + dy
                if 1 <= nx < self.size - 1 and 1 <= ny < self.size - 1:
                    if (nx, ny) not in visited:
                        neighbors.append((nx, ny))
            
            if neighbors:
                nx, ny = random.choice(neighbors)
                wx, wy = cx + (nx - cx) // 2, cy + (ny - cy) // 2
                self.grid[wy][wx] = 0
                self.grid[ny][nx] = 0
                visited.add((nx, ny))
                stack.append((nx, ny))
            else:
                stack.pop()
        
        # Ensure Goal is reachable
        gx, gy = self.size - 2, self.size - 2
        self.goal_pos = (gx, gy)
        self.grid[gy][gx] = 0
        
        if self.grid[gy][gx-1] == 1 and self.grid[gy-1][gx] == 1:
             self.grid[gy][gx-1] = 0
        
        # Add random loops ONLY if no doors (Strict Requirement)
        if num_doors == 0:
            for _ in range(self.size // 2):
                rx = random.randint(1, self.size - 2)
                ry = random.randint(1, self.size - 2)
                if self.grid[ry][rx] == 1:
                    floors = 0
                    for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                        if self.grid[ry+dy][rx+dx] == 0:
                            floors += 1
                    if floors >= 2:
                        self.grid[ry][rx] = 0
        
        # Place Keys and Doors
        self.keys = []
        self.doors = []
        
        if num_doors > 0:
            path = self.find_path(self.start_pos, self.goal_pos)
            if path and len(path) > (num_doors * 5):
                indices = []
                for i in range(num_doors):
                    segment_len = len(path) // (num_doors + 1)
                    base_idx = segment_len * (i + 1)
                    idx = base_idx + random.randint(-2, 2)
                    idx = max(5, min(len(path) - 5, idx))
                    indices.append(idx)
                
                indices.sort()
                
                current_start = self.start_pos
                
                for i, idx in enumerate(indices):
                    door_pos = path[idx]
                    self.doors.append(door_pos)
                    
                    block_list = self.doors[:] 
                    reachable_dists = self.get_reachable_distances(current_start, block_list=block_list)
                    
                    candidates = []
                    path_segment_set = set(path[:idx])
                    
                    for pos, dist in reachable_dists.items():
                        if pos not in path_segment_set and pos not in self.keys and pos not in self.doors and pos != self.start_pos:
                            candidates.append((pos, dist))
                    
                    candidates.sort(key=lambda x: x[1], reverse=True)
                    
                    if candidates:
                        top_n = max(1, len(candidates) // 4)
                        key_pos = random.choice(candidates[:top_n])[0]
                        self.keys.append(key_pos)
                    else:
                        if reachable_dists:
                            self.keys.append(random.choice(list(reachable_dists.keys())))
                        else:
                            self.keys.append(path[idx-1])
                    
                    if idx + 1 < len(path):
                        current_start = path[idx+1]
    
    def find_path(self, start, end):
        queue = [(start, [])]
        visited = {start}
        while queue:
            (cx, cy), path = queue.pop(0)
            if (cx, cy) == end:
                return path + [(cx, cy)]
            
            for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if not self.is_wall(nx, ny) and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append(((nx, ny), path + [(cx, cy)]))
        return None
    
    def get_reachable_distances(self, start, block_list):
        queue = [(start, 0)]
        visited = {start: 0}
        block_set = set(block_list)
        while queue:
            (cx, cy), dist = queue.pop(0)
            for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if not self.is_wall(nx, ny) and (nx, ny) not in block_set and (nx, ny) not in visited:
                    visited[(nx, ny)] = dist + 1
                    queue.append(((nx, ny), dist + 1))
        return visited
    
    def is_wall(self, x, y):
        if 0 <= x < self.size and 0 <= y < self.size:
            return self.grid[y][x] == 1
        return True
    
    def draw(self, surface, tile_size, offset_x, offset_y):
        # Draw Grid Lines
        for x in range(self.size + 1):
            pygame.draw.line(surface, COLOR_GRID, 
                             (offset_x + x * tile_size, offset_y),
                             (offset_x + x * tile_size, offset_y + self.size * tile_size))
        for y in range(self.size + 1):
            pygame.draw.line(surface, COLOR_GRID,
                             (offset_x, offset_y + y * tile_size),
                             (offset_x + self.size * tile_size, offset_y + y * tile_size))
        
        # Draw Walls, Goal, Key, Door
        for y in range(self.size):
            for x in range(self.size):
                rect = (offset_x + x * tile_size + 2, offset_y + y * tile_size + 2, 
                        tile_size - 4, tile_size - 4)
                cx = rect[0] + tile_size // 2
                cy = rect[1] + tile_size // 2
                
                if self.grid[y][x] == 1:
                    pygame.draw.rect(surface, COLOR_WALL, rect)
                elif (x, y) == self.goal_pos:
                    pygame.draw.rect(surface, COLOR_GOAL, rect, 3)
                    pygame.draw.rect(surface, COLOR_GOAL, (cx - 4, cy - 4, 8, 8))
                elif (x, y) in self.keys:
                    # Draw Key Art
                    pygame.draw.circle(surface, COLOR_KEY, (cx, cy - 4), 6) 
                    pygame.draw.line(surface, COLOR_KEY, (cx, cy), (cx, cy + 10), 3) 
                    pygame.draw.line(surface, COLOR_KEY, (cx, cy + 10), (cx + 4, cy + 10), 3) 
                elif (x, y) in self.doors:
                    # Draw Door Art
                    pygame.draw.rect(surface, COLOR_DOOR, rect)
                    pygame.draw.rect(surface, (100, 50, 10), rect, 2) 
                    pygame.draw.circle(surface, (255, 215, 0), (rect[0] + tile_size - 8, cy), 3)
class Player:
    def __init__(self, start_pos):
        self.reset(start_pos)
    
    def reset(self, start_pos):
        self.grid_x, self.grid_y = start_pos
        self.direction = 1 # Start facing East
        
        self.x = float(self.grid_x)
        self.y = float(self.grid_y)
        
        self.angle = 90.0 
        self.target_angle = 90.0
        self.start_angle = 90.0
        
        self.target_x, self.target_y = self.x, self.y
        
        self.animating = False
        self.anim_t = 0.0
        self.anim_duration = ANIMATION_DURATION_MS
        
        self.crashed = False
        self.won = False
        self.keys_collected = 0
    
    def get_angle_for_dir(self, d):
        # 0=N (0), 1=E (90), 2=S (180), 3=W (270)
        return d * 90.0
    
    def start_move(self, dx, dy, duration=ANIMATION_DURATION_MS):
        self.start_x = self.x
        self.start_y = self.y
        self.start_angle = self.target_angle # Lock angle
        
        self.grid_x += dx
        self.grid_y += dy
        self.target_x = float(self.grid_x)
        self.target_y = float(self.grid_y)
        
        self.animating = True
        self.anim_t = 0.0
        self.anim_duration = duration
    
    def start_turn(self, new_dir):
        self.start_x = self.target_x
        self.start_y = self.target_y
        self.start_angle = self.angle
        
        target = self.get_angle_for_dir(new_dir)
        # Shortest path rotation
        diff = (target - self.start_angle + 180) % 360 - 180
        self.target_angle = self.start_angle + diff
        
        self.direction = new_dir
        self.animating = True
        self.anim_t = 0.0
        self.anim_duration = ANIMATION_DURATION_MS
    
    def update(self, dt_ms):
        if self.animating:
            self.anim_t += dt_ms / self.anim_duration
            if self.anim_t >= 1.0:
                self.anim_t = 1.0
                self.animating = False
                self.x = self.target_x
                self.y = self.target_y
                self.angle = self.target_angle
            else:
                t = cubic_bezier(self.anim_t)
                self.x = lerp(self.start_x, self.target_x, t)
                self.y = lerp(self.start_y, self.target_y, t)
                self.angle = lerp(self.start_angle, self.target_angle, t)
    
    def draw(self, surface, tile_size, offset_x, offset_y):
        center_x = offset_x + self.x * tile_size + tile_size // 2
        center_y = offset_y + self.y * tile_size + tile_size // 2
        size = tile_size // 3
        
        # Base triangle pointing UP (0 degrees)
        # Points relative to center
        p1 = (0, -size)
        p2 = (-size, size)
        p3 = (size, size)
        
        # Rotate points
        rad = math.radians(self.angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        
        def rotate(p):
            px, py = p
            nx = px * cos_a - py * sin_a
            ny = px * sin_a + py * cos_a
            return (center_x + nx, center_y + ny)
        
        points = [rotate(p1), rotate(p2), rotate(p3)]
        
        color = COLOR_ERROR if self.crashed else COLOR_PLAYER
        if self.keys_collected > 0:
             color = COLOR_KEY # Show player holding key
             
        pygame.draw.polygon(surface, color, points)
class CodeInterpreter:
    def __init__(self, console, game):
        self.action_queue = []
        self.console = console
        self.game = game

    def run_code(self, code_str):
        self.action_queue = []
        self.console.clear()
        
        # Simulation State
        sim_x, sim_y = self.game.player.grid_x, self.game.player.grid_y
        sim_dir = self.game.player.direction # 0=N, 1=E, 2=S, 3=W
        
        lines = [l for l in code_str.split('\n') if l.strip() and not l.strip().startswith('#')]

        def move(): 
            nonlocal sim_x, sim_y
            # Calculate next pos
            dx, dy = 0, 0
            if sim_dir == 0: dy = -1
            elif sim_dir == 1: dx = 1
            elif sim_dir == 2: dy = 1
            elif sim_dir == 3: dx = -1
            
            target_x, target_y = sim_x + dx, sim_y + dy
            # Check collision with wall using game map
            if not self.game.map.is_wall(target_x, target_y):
                sim_x, sim_y = target_x, target_y
            
            self.action_queue.append(('MOVE',))

        def turn_left(): 
            nonlocal sim_dir
            sim_dir = (sim_dir - 1) % 4
            self.action_queue.append(('TURN', 'LEFT'))

        def turn_right(): 
            nonlocal sim_dir
            sim_dir = (sim_dir + 1) % 4
            self.action_queue.append(('TURN', 'RIGHT'))

        # Sensors
        def wall_ahead():
            dx, dy = 0, 0
            if sim_dir == 0: dy = -1
            elif sim_dir == 1: dx = 1
            elif sim_dir == 2: dy = 1
            elif sim_dir == 3: dx = -1
            return self.game.map.is_wall(sim_x + dx, sim_y + dy)

        def path_left():
            # Check left relative to current direction
            left_dir = (sim_dir - 1) % 4
            dx, dy = 0, 0
            if left_dir == 0: dy = -1
            elif left_dir == 1: dx = 1
            elif left_dir == 2: dy = 1
            elif left_dir == 3: dx = -1
            return not self.game.map.is_wall(sim_x + dx, sim_y + dy)

        def path_right():
            # Check right relative to current direction
            right_dir = (sim_dir + 1) % 4
            dx, dy = 0, 0
            if right_dir == 0: dy = -1
            if right_dir == 1: dx = 1
            elif right_dir == 2: dy = 1
            elif right_dir == 3: dx = -1
            return not self.game.map.is_wall(sim_x + dx, sim_y + dy)

        env = {
            'move': move,
            'turn_left': turn_left,
            'turn_right': turn_right,
            'wall_ahead': wall_ahead,
            'path_left': path_left,
            'path_right': path_right,
            'range': range,
            'print': lambda x: self.console.log(str(x))
        }
        try:
            exec(code_str, {"__builtins__": {}}, env)
            self.console.log("Execution successful.", COLOR_SUCCESS)
            return True
        except Exception as e:
            self.console.log(f"Runtime Error: {str(e)}", COLOR_ERROR)
            return False
class Game:
    def __init__(self):
        pygame.init()
        
        # Initialize fullscreen mode
        self.fullscreen = False
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("MazeBot")
        
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 18)
        self.large_font = pygame.font.SysFont("Consolas", 32)
        
        # Enable Key Repeat
        pygame.key.set_repeat(400, 50)
        
        self.difficulty = "NORMAL"
        self.grid_size = 10
        self.line_cost = 10
        self.calculate_layout()
        self.map = GameMap(self.grid_size)
        self.player = Player(self.map.start_pos)
        
        # Initialize path tracker
        self.path_tracker = PathTracker(self.map)
        self.last_code_hash = None
        
        # UI Components
        BUTTON_AREA_HEIGHT = 80 # Increased for 2 rows
        self.editor = TextEditor(GAME_VIEW_WIDTH, 0, EDITOR_WIDTH, SCREEN_HEIGHT - 200 - BUTTON_AREA_HEIGHT, self.font)
        self.console = Console(GAME_VIEW_WIDTH, SCREEN_HEIGHT - 200, EDITOR_WIDTH, 200, self.font)
        self.interpreter = CodeInterpreter(self.console, self)
        
        # Buttons
        self.buttons = []
        btn_y = SCREEN_HEIGHT - 200 - BUTTON_AREA_HEIGHT
        btn_w = (EDITOR_WIDTH - 20) // 4
        btn_h = 30
        margin = 4
        
        def add_text(t):
            if self.state != "EDITING":
                self.reset_run()
            self.editor.insert_text(t)
            
        # Row 1: Actions
        self.buttons.append(Button(GAME_VIEW_WIDTH + 4, btn_y + 5, btn_w, btn_h, "move()", lambda: add_text("move()\n"), self.font))
        self.buttons.append(Button(GAME_VIEW_WIDTH + 4 + btn_w + margin, btn_y + 5, btn_w, btn_h, "left()", lambda: add_text("turn_left()\n"), self.font))
        self.buttons.append(Button(GAME_VIEW_WIDTH + 4 + 2*(btn_w + margin), btn_y + 5, btn_w, btn_h, "right()", lambda: add_text("turn_right()\n"), self.font))
        self.buttons.append(Button(GAME_VIEW_WIDTH + 4 + 3*(btn_w + margin), btn_y + 5, btn_w, btn_h, "loop", lambda: add_text("for i in range(1):\n    "), self.font))

        # Row 2: Logic/Sensors
        y2 = btn_y + 5 + btn_h + 5
        self.buttons.append(Button(GAME_VIEW_WIDTH + 4, y2, btn_w, btn_h, "if wall", lambda: add_text("if wall_ahead():\n    "), self.font))
        self.buttons.append(Button(GAME_VIEW_WIDTH + 4 + btn_w + margin, y2, btn_w, btn_h, "if left", lambda: add_text("if path_left():\n    "), self.font))
        self.buttons.append(Button(GAME_VIEW_WIDTH + 4 + 2*(btn_w + margin), y2, btn_w, btn_h, "if right", lambda: add_text("if path_right():\n    "), self.font))
        self.buttons.append(Button(GAME_VIEW_WIDTH + 4 + 3*(btn_w + margin), y2, btn_w, btn_h, "else", lambda: add_text("else:\n    "), self.font))
        
        # Control buttons row (above helper buttons)
        play_btn_w = 80
        play_btn_x = SCREEN_WIDTH - play_btn_w - 20
        play_btn_y = SCREEN_HEIGHT - 200 - BUTTON_AREA_HEIGHT - 40
        
        # DELETE Button (leftmost)
        delete_btn_x = play_btn_x - play_btn_w - 10
        self.buttons.append(Button(delete_btn_x, play_btn_y, play_btn_w, 30, "DELETE", self.delete_code, self.font))
        
        # RESET Button
        reset_btn_x = delete_btn_x - play_btn_w - 10
        self.buttons.append(Button(reset_btn_x, play_btn_y, play_btn_w, 30, "RESET", self.reset_run, self.font))
        
        # RUN Button
        self.buttons.append(Button(play_btn_x, play_btn_y, play_btn_w, 30, "RUN", self.start_run, self.font))
        
        # FULL Button
        full_btn_x = reset_btn_x - play_btn_w - 10
        self.buttons.append(Button(full_btn_x, play_btn_y, play_btn_w, 30, "FULL", self.toggle_fullscreen, self.font))
        
        # Menu Buttons
        self.menu_buttons = []
        btn_w = 400
        btn_h = 40
        cx = SCREEN_WIDTH // 2 - btn_w // 2
        self.menu_buttons.append(Button(cx, 350, btn_w, btn_h, "1. NORMAL (10x10, Cost 10, Win 32x32)", lambda: self.set_difficulty("NORMAL"), self.font))
        self.menu_buttons.append(Button(cx, 400, btn_w, btn_h, "2. HARD (16x16, Cost 15, Win 50x50)", lambda: self.set_difficulty("HARD"), self.font))
        self.menu_buttons.append(Button(cx, 450, btn_w, btn_h, "3. EXTREME (24x24, Cost 20, Win 72x72)", lambda: self.set_difficulty("EXTREME"), self.font))
        
        self.state = "MENU" # Start in Menu
        self.level = 1
        self.coins = STARTING_COINS
        self.current_run_cost = 0
        
        self.optimal_lines = self.calculate_optimal_lines()
        
        # Timer for live code analysis
        self.last_live_update = 0
        self.live_update_interval = 500  # Update path every 500ms
    
    def delete_code(self):
        """Delete all code in the editor"""
        self.editor.clear()
        self.console.log("All code deleted.", COLOR_TEXT)
        self.path_tracker.reset()
    
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            # Get actual screen size
            global SCREEN_WIDTH, SCREEN_HEIGHT, GAME_VIEW_WIDTH, EDITOR_WIDTH
            SCREEN_WIDTH, SCREEN_HEIGHT = self.screen.get_size()
            GAME_VIEW_WIDTH = int(SCREEN_WIDTH * 0.6)
            EDITOR_WIDTH = SCREEN_WIDTH - GAME_VIEW_WIDTH
        else:
            self.screen = pygame.display.set_mode((1280, 720))
            SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720
            GAME_VIEW_WIDTH = int(SCREEN_WIDTH * 0.6)
            EDITOR_WIDTH = SCREEN_WIDTH - GAME_VIEW_WIDTH
        
        # Recalculate layout and reposition UI elements
        self.calculate_layout()
        self.reposition_ui()
        self.console.log(f"{'Entered' if self.fullscreen else 'Exited'} Fullscreen Mode", COLOR_SUCCESS)
    
    def reposition_ui(self):
        # Reposition the editor and console
        BUTTON_AREA_HEIGHT = 80
        self.editor.rect = pygame.Rect(GAME_VIEW_WIDTH, 0, EDITOR_WIDTH, SCREEN_HEIGHT - 200 - BUTTON_AREA_HEIGHT)
        self.console.rect = pygame.Rect(GAME_VIEW_WIDTH, SCREEN_HEIGHT - 200, EDITOR_WIDTH, 200)
        
        # Update editor's scrollbar
        self.editor.scrollbar_rect = pygame.Rect(
            self.editor.rect.right - self.editor.scrollbar_width,
            self.editor.rect.top,
            self.editor.scrollbar_width,
            self.editor.rect.height
        )
        self.editor.max_visible_lines = self.editor.rect.height // self.editor.line_height
        self.editor.update_scrollbar()
        
        # Reposition buttons
        btn_y = SCREEN_HEIGHT - 200 - BUTTON_AREA_HEIGHT
        btn_w = (EDITOR_WIDTH - 20) // 4
        btn_h = 30
        margin = 4
        
        # Row 1: Actions
        self.buttons[0].rect = pygame.Rect(GAME_VIEW_WIDTH + 4, btn_y + 5, btn_w, btn_h)
        self.buttons[1].rect = pygame.Rect(GAME_VIEW_WIDTH + 4 + btn_w + margin, btn_y + 5, btn_w, btn_h)
        self.buttons[2].rect = pygame.Rect(GAME_VIEW_WIDTH + 4 + 2*(btn_w + margin), btn_y + 5, btn_w, btn_h)
        self.buttons[3].rect = pygame.Rect(GAME_VIEW_WIDTH + 4 + 3*(btn_w + margin), btn_y + 5, btn_w, btn_h)

        # Row 2: Logic/Sensors
        y2 = btn_y + 5 + btn_h + 5
        self.buttons[4].rect = pygame.Rect(GAME_VIEW_WIDTH + 4, y2, btn_w, btn_h)
        self.buttons[5].rect = pygame.Rect(GAME_VIEW_WIDTH + 4 + btn_w + margin, y2, btn_w, btn_h)
        self.buttons[6].rect = pygame.Rect(GAME_VIEW_WIDTH + 4 + 2*(btn_w + margin), y2, btn_w, btn_h)
        self.buttons[7].rect = pygame.Rect(GAME_VIEW_WIDTH + 4 + 3*(btn_w + margin), y2, btn_w, btn_h)
        
        # Control buttons
        play_btn_w = 80
        play_btn_x = SCREEN_WIDTH - play_btn_w - 20
        play_btn_y = SCREEN_HEIGHT - 200 - BUTTON_AREA_HEIGHT - 40
        
        # Adjust indices based on the new button order
        # DELETE button (index 8)
        delete_btn_x = play_btn_x - play_btn_w - 10
        self.buttons[8].rect = pygame.Rect(delete_btn_x, play_btn_y, play_btn_w, 30)
        
        # RESET button (index 9)
        reset_btn_x = delete_btn_x - play_btn_w - 10
        self.buttons[9].rect = pygame.Rect(reset_btn_x, play_btn_y, play_btn_w, 30)
        
        # RUN button (index 10)
        self.buttons[10].rect = pygame.Rect(play_btn_x, play_btn_y, play_btn_w, 30)
        
        # FULL button (index 11)
        full_btn_x = reset_btn_x - play_btn_w - 10
        self.buttons[11].rect = pygame.Rect(full_btn_x, play_btn_y, play_btn_w, 30)
        
        # Reposition menu buttons
        btn_w = 400
        btn_h = 40
        cx = SCREEN_WIDTH // 2 - btn_w // 2
        self.menu_buttons[0].rect = pygame.Rect(cx, 350, btn_w, btn_h)
        self.menu_buttons[1].rect = pygame.Rect(cx, 400, btn_w, btn_h)
        self.menu_buttons[2].rect = pygame.Rect(cx, 450, btn_w, btn_h)
    
    def calculate_layout(self):
        self.tile_size = min(GAME_VIEW_WIDTH // self.grid_size, (SCREEN_HEIGHT - HUD_HEIGHT) // self.grid_size)
        self.grid_offset_x = (GAME_VIEW_WIDTH - (self.grid_size * self.tile_size)) // 2
        self.grid_offset_y = HUD_HEIGHT + ((SCREEN_HEIGHT - HUD_HEIGHT) - (self.grid_size * self.tile_size)) // 2
    
    def set_difficulty(self, diff):
        self.difficulty = diff
        if diff == "NORMAL":
            self.grid_size = 10
            self.line_cost = 10
        elif diff == "HARD":
            self.grid_size = 16
            self.line_cost = 15
        elif diff == "EXTREME":
            self.grid_size = 24
            self.line_cost = 20
        
        self.calculate_layout()
        self.level = 1
        self.coins = STARTING_COINS
        self.level_start_coins = STARTING_COINS
        
        # Determine num_doors
        num_doors = 0
        if diff == "EXTREME":
            if self.grid_size >= 72: num_doors = 5
            elif self.grid_size >= 64: num_doors = 4
            elif self.grid_size >= 32: num_doors = 3
            else: num_doors = 2
        elif self.grid_size >= 16: # Normal/Hard threshold
             num_doors = 1
            
        self.map = GameMap(self.grid_size)
        self.map.generate_maze(num_doors)
        
        self.player = Player(self.map.start_pos)
        self.path_tracker = PathTracker(self.map)
        self.optimal_lines = self.calculate_optimal_lines()
        
        # Dynamic Starting Coins
        # Ensure coins exactly match goal lines cost
        goal_mult = 1.5 if diff == "HARD" else 2.0
        goal_lines = int(self.optimal_lines * goal_mult)
        self.coins = goal_lines * self.line_cost
        self.level_start_coins = self.coins
        
        self.state = "EDITING"
        self.editor.lines = ["move()"]
        self.editor.cursor_row = 0
        self.editor.cursor_col = 6
        self.editor.scroll_y = 0
        self.editor.update_scrollbar()
        self.console.log(f"Difficulty: {diff}. Cost: {self.line_cost}/line. Coins: {self.coins}", COLOR_SUCCESS)
    
    def next_level(self):
        self.level += 1
        
        # Reward
        reward = (self.grid_size * 10) + LEVEL_REWARD_BASE
        if self.difficulty == "EXTREME":
             reward = (self.grid_size * 5) + (LEVEL_REWARD_BASE // 2) # Smaller reward
             
        self.coins += reward
        self.console.log(f"Level Complete! Reward: {reward} Coins.", COLOR_SUCCESS)
        
        # Scale Difficulty (Size)
        if self.difficulty == "EXTREME":
            # 24 -> 32 -> 48 -> 64 -> 72
            if self.grid_size == 24: self.grid_size = 32
            elif self.grid_size == 32: self.grid_size = 48
            elif self.grid_size == 48: self.grid_size = 64
            elif self.grid_size == 64: self.grid_size = 72
            elif self.grid_size == 72:
                self.state = "YOU_WON" # Win Condition
                return
        else:
            # Normal / Hard Scaling
            if self.difficulty == "NORMAL" and self.grid_size >= 32:
                self.state = "YOU_WON"
                return
            elif self.difficulty == "HARD" and self.grid_size >= 50:
                self.state = "YOU_WON"
                return
                
            if self.grid_size < 72:
                self.grid_size += 2
            
        self.calculate_layout()
        self.console.log(f"Map Size Increased to {self.grid_size}x{self.grid_size}!", COLOR_KEYWORD)
        
        # Determine num_doors for Extreme
        num_doors = 0
        if self.difficulty == "EXTREME":
            if self.grid_size >= 72: num_doors = 5
            elif self.grid_size >= 64: num_doors = 4
            elif self.grid_size >= 32: num_doors = 3
            else: num_doors = 2
        elif self.grid_size >= 16: # Normal/Hard threshold
             num_doors = 1
        
        self.map = GameMap(self.grid_size) # Regenerate with current size
        self.map.generate_maze(num_doors)
        self.player.reset(self.map.start_pos)
        self.path_tracker = PathTracker(self.map)
        self.state = "EDITING"
        self.optimal_lines = self.calculate_optimal_lines()
        self.current_run_cost = 0
        
        # Ensure sufficient coins for next level
        goal_mult = 1.5 if self.difficulty == "HARD" else 2.0
        goal_lines = int(self.optimal_lines * goal_mult)
        needed = goal_lines * self.line_cost
        
        if self.coins < needed:
            self.coins = needed
            self.console.log(f"Coins topped up to {self.coins} for next level.", COLOR_KEYWORD)
            
        self.level_start_coins = self.coins # Checkpoint
        
        self.editor.lines = ["move()"] 
        self.editor.cursor_row = 0
        self.editor.cursor_col = 6
        self.editor.scroll_y = 0
        self.editor.update_scrollbar()
        self.console.log(f"Level {self.level} Started!", COLOR_SUCCESS)
    
    def calculate_optimal_lines(self):
        # BFS to find shortest path
        queue = [(self.map.start_pos, [])]
        visited = {self.map.start_pos}
        path = []
        
        while queue:
            (curr_x, curr_y), curr_path = queue.pop(0)
            if (curr_x, curr_y) == self.map.goal_pos:
                path = curr_path + [(curr_x, curr_y)]
                break
            
            for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                next_x, next_y = curr_x + dx, curr_y + dy
                if not self.map.is_wall(next_x, next_y) and (next_x, next_y) not in visited:
                    visited.add((next_x, next_y))
                    queue.append(((next_x, next_y), curr_path + [(curr_x, curr_y)]))
        
        if not path: return 999
        curr_dir = 1 
        lines = 0
        i = 0
        while i < len(path) - 1:
            curr_node = path[i]
            next_node = path[i+1]
            dx = next_node[0] - curr_node[0]
            dy = next_node[1] - curr_node[1]
            
            target_dir = -1
            if dy == -1: target_dir = 0
            elif dx == 1: target_dir = 1
            elif dy == 1: target_dir = 2
            elif dx == -1: target_dir = 3
            
            diff = (target_dir - curr_dir) % 4
            if diff == 1: lines += 1
            elif diff == 2: lines += 2
            elif diff == 3: lines += 1
            
            curr_dir = target_dir
            moves = 0
            while i < len(path) - 1:
                n1 = path[i]
                n2 = path[i+1]
                dx2 = n2[0] - n1[0]
                dy2 = n2[1] - n1[1]
                move_dir = -1
                if dy2 == -1: move_dir = 0
                elif dx2 == 1: move_dir = 1
                elif dy2 == 1: move_dir = 2
                elif dx2 == -1: move_dir = 3
                
                if move_dir == curr_dir:
                    moves += 1
                    i += 1
                else:
                    break
            
            if moves == 1: lines += 1
            elif moves > 1: lines += 2
                
        return lines
    
    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            # Fullscreen toggle with F11
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.toggle_fullscreen()
            
            if self.state == "MENU":
                for btn in self.menu_buttons:
                    btn.handle_event(event)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        self.set_difficulty("NORMAL")
                    elif event.key == pygame.K_2:
                        self.set_difficulty("HARD")
                    elif event.key == pygame.K_3:
                        self.set_difficulty("EXTREME")
            
            elif self.state == "GAME_OVER" or self.state == "YOU_WON":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = "MENU"
            elif self.state == "EDITING" or self.state == "RUNNING" or self.state == "FINISHED":
                if self.state == "EDITING":
                    self.editor.handle_input(event)
                
                for btn in self.buttons:
                    btn.handle_event(event)
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F5:
                        self.start_run()
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == "MENU":
                        pygame.quit()
                        sys.exit()
                    elif self.state != "GAME_OVER":
                        self.reset_run()
                
                # Auto-Reset on Typing if Running/Finished
                elif (self.state == "RUNNING" or self.state == "FINISHED") and not self.player.won:
                     # If user tries to type (printable char or backspace/delete/enter), reset
                     if (event.unicode and event.unicode.isprintable()) or event.key in [pygame.K_BACKSPACE, pygame.K_DELETE, pygame.K_RETURN]:
                         self.reset_run()
                         # Pass event to editor so the keystroke isn't lost
                         self.editor.handle_input(event)
                # Next Level Debug / Cheat or Interaction
                if self.state == "FINISHED" and self.player.won:
                    if event.key == pygame.K_RETURN:
                        self.next_level()
    
    def reset_run(self):
        self.state = "EDITING"
        self.player.reset(self.map.start_pos)
        self.path_tracker.reset()
        self.coins = self.level_start_coins # Restore coins
        self.console.log("Reset. Coins Restored.", COLOR_TEXT)
    
    def start_run(self):
        code = self.editor.get_text()
        if self.interpreter.run_code(code):
            self.state = "RUNNING"
            self.player.reset(self.map.start_pos)
            self.path_tracker.reset()
            
            lines_used = len([l for l in self.editor.lines if l.strip() and not l.strip().startswith('#')])
            
            # Cost
            cost = lines_used * self.line_cost
            if self.coins >= cost:
                self.coins -= cost
                self.console.log(f"Running... Cost: {cost} Coins. (Lines: {lines_used})", COLOR_TEXT)
            else:
                self.console.log(f"Not enough coins! Need {cost}.", COLOR_ERROR)
    
    def update(self):
        dt = self.clock.get_time()
        current_time = pygame.time.get_ticks()
        
        # Update live path tracking when editing
        if self.state == "EDITING" and current_time - self.last_live_update > self.live_update_interval:
            code = self.editor.get_text()
            if code.strip():  # Only simulate if there's code
                self.path_tracker.simulate_code(code)
            self.last_live_update = current_time
        
        # Update player animation
        self.player.update(dt)
        
        # Update path tracker with player position
        if self.state == "RUNNING" or self.state == "FINISHED":
            self.path_tracker.update_from_player((self.player.grid_x, self.player.grid_y))
        
        if self.state == "RUNNING" and not self.player.animating:
            if self.interpreter.action_queue:
                action = self.interpreter.action_queue.pop(0)
                
                # Check for consecutive moves
                if action[0] == 'MOVE':
                    moves = 1
                    # Peek ahead
                    while self.interpreter.action_queue and self.interpreter.action_queue[0][0] == 'MOVE':
                        self.interpreter.action_queue.pop(0)
                        moves += 1
                    
                    self.execute_move_sequence(moves)
                else:
                    self.execute_action(action)
            else:
                if (self.player.grid_x, self.player.grid_y) == self.map.goal_pos:
                    self.state = "FINISHED"
                    self.player.won = True
                    self.console.log(f"GOAL! Level Complete. Press ENTER.", COLOR_SUCCESS)
                else:
                    self.state = "FINISHED"
                    self.console.log("Stopped.", COLOR_TEXT)
    
    def execute_move_sequence(self, moves):
        dx, dy = 0, 0
        if self.player.direction == 0: dy = -1
        elif self.player.direction == 1: dx = 1
        elif self.player.direction == 2: dy = 1
        elif self.player.direction == 3: dx = -1
        
        # Check how far we can actually go
        valid_moves = 0
        crashed = False
        for i in range(1, moves + 1):
            tx = self.player.grid_x + dx * i
            ty = self.player.grid_y + dy * i
            # Check Key Pickup
            if (tx, ty) in self.map.keys:
                # Remove key
                self.map.keys.remove((tx, ty))
                self.player.keys_collected += 1
                self.console.log("Key Collected!", COLOR_SUCCESS)
            # Check Door Collision
            if (tx, ty) in self.map.doors:
                if self.player.keys_collected > 0:
                    # Unlock Door
                    self.map.doors.remove((tx, ty))
                    self.player.keys_collected -= 1
                    self.console.log("Door Unlocked!", COLOR_SUCCESS)
                else:
                    crashed = True
                    self.console.log("CRASH: Door Locked!", COLOR_ERROR)
                    break
            if self.map.is_wall(tx, ty):
                crashed = True
                break
            valid_moves += 1
        
        # Animate valid moves
        if valid_moves > 0:
            # Faster animation for longer sequences
            # Base duration + small increment per extra tile
            duration = ANIMATION_DURATION_MS + (valid_moves - 1) * 100
            self.player.start_move(dx * valid_moves, dy * valid_moves, duration)
        
        if crashed:
            self.console.log(f"Path blocked! Moved {valid_moves}/{moves} steps.", COLOR_ERROR)
            self.interpreter.action_queue = []
    
    def execute_action(self, action):
        if action[0] == 'MOVE':
            # Should be handled by execute_move_sequence usually, but single moves might fall here if logic changes
            self.execute_move_sequence(1)
            
        elif action[0] == 'TURN':
            new_dir = self.player.direction
            if action[1] == 'LEFT':
                new_dir = (self.player.direction - 1) % 4
            elif action[1] == 'RIGHT':
                new_dir = (self.player.direction + 1) % 4
            self.player.start_turn(new_dir)
    
    def draw(self):
        self.screen.fill(COLOR_BG)
        if self.state == "MENU":
            self.draw_menu()
            pygame.display.flip()
            return
        
        if self.state == "GAME_OVER":
            self.draw_game_over()
            pygame.display.flip()
            return
        
        if self.state == "YOU_WON":
            self.draw_win()
            pygame.display.flip()
            return
        
        # Draw Game View
        self.map.draw(self.screen, self.tile_size, self.grid_offset_x, self.grid_offset_y)
        
        # Draw path tracking (behind player)
        self.path_tracker.draw(self.screen, self.tile_size, self.grid_offset_x, self.grid_offset_y)
        
        # Draw player (on top of path)
        self.player.draw(self.screen, self.tile_size, self.grid_offset_x, self.grid_offset_y)
        
        # Level Counter on Map (Bottom Left)
        lvl_text = self.font.render(f"Level {self.level}", True, COLOR_TEXT)
        self.screen.blit(lvl_text, (10, SCREEN_HEIGHT - 30))
        
        # Draw HUD
        pygame.draw.rect(self.screen, COLOR_HUD_BG, (0, 0, GAME_VIEW_WIDTH, HUD_HEIGHT))
        pygame.draw.line(self.screen, COLOR_GRID, (0, HUD_HEIGHT), (GAME_VIEW_WIDTH, HUD_HEIGHT), 2)
        
        # HUD Text
        lines_used = len([l for l in self.editor.lines if l.strip() and not l.strip().startswith('#')])
        goal_mult = 1.5 if self.difficulty == "HARD" else 2.0
        goal_lines = int(self.optimal_lines * goal_mult)
        
        # Compact HUD
        hud_font = self.font # Use smaller font
        hud_text = f"LVL: {self.level} | COINS: {self.coins} | LINES: {lines_used} (Cost: {lines_used*self.line_cost}) | GOAL: {goal_lines}"
        hud_surf = hud_font.render(hud_text, True, COLOR_HUD_TEXT)
        self.screen.blit(hud_surf, (20, 10))
        
        # Draw UI
        self.editor.draw(self.screen)
        self.console.draw(self.screen)
        for btn in self.buttons:
            btn.draw(self.screen)
        
        # Draw Overlay Info
        if self.state == "FINISHED" and self.player.won:
            msg = f"LEVEL COMPLETE! Press ENTER"
            surf = self.large_font.render(msg, True, COLOR_SUCCESS)
            # Center in Game View
            self.screen.blit(surf, (GAME_VIEW_WIDTH//2 - surf.get_width()//2, SCREEN_HEIGHT//2))
        
        # Draw live tracking info
        if self.state == "EDITING" and self.path_tracker.predicted_path:
            predicted_length = len(self.path_tracker.predicted_path)
            info_text = f"Predicted Path: {predicted_length} steps"
            info_surf = self.font.render(info_text, True, COLOR_PATH_TRACK[:3])
            self.screen.blit(info_surf, (GAME_VIEW_WIDTH + 10, 10))
        
        pygame.display.flip()
    
    def draw_menu(self):
        title = self.large_font.render("MazeBot", True, COLOR_PLAYER)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 200))
        
        info = self.font.render("Select Difficulty:", True, COLOR_TEXT)
        self.screen.blit(info, (SCREEN_WIDTH//2 - info.get_width()//2, 300))
        
        for btn in self.menu_buttons:
            btn.draw(self.screen)
        
        esc = self.font.render("Press ESC to Quit | F11: Fullscreen", True, (100, 100, 100))
        self.screen.blit(esc, (SCREEN_WIDTH//2 - esc.get_width()//2, 550))
    
    def draw_game_over(self):
        title = self.large_font.render("GAME OVER", True, COLOR_ERROR)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 200))
        
        reason = self.font.render("BANKRUPT! Not enough coins to code.", True, COLOR_TEXT)
        self.screen.blit(reason, (SCREEN_WIDTH//2 - reason.get_width()//2, 300))
        
        esc = self.font.render("Press ESC to Return to Menu", True, (100, 100, 100))
        self.screen.blit(esc, (SCREEN_WIDTH//2 - esc.get_width()//2, 400))
    
    def draw_win(self):
        title = self.large_font.render("YOU WON!", True, COLOR_SUCCESS)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 200))
        
        msg_text = f"You beat {self.difficulty} Mode!"
        msg = self.font.render(msg_text, True, COLOR_TEXT)
        self.screen.blit(msg, (SCREEN_WIDTH//2 - msg.get_width()//2, 300))
        
        esc = self.font.render("Press ESC to Return to Menu", True, (100, 100, 100))
        self.screen.blit(esc, (SCREEN_WIDTH//2 - esc.get_width()//2, 400))
    
    def run(self):
        while True:
            self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = Game()
    game.run()
