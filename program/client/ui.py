import pygame

def draw_button(screen, font, text, x, y, w, h, color):
    txt_surf = font.render(text, True, (255, 255, 255))
    final_w = max(w, txt_surf.get_width() + 40)
    final_h = max(h, txt_surf.get_height() + 20)
    
    if final_w > w:
        x -= (final_w - w) / 2
        
    rect = pygame.Rect(x, y, final_w, final_h)
    pygame.draw.rect(screen, color, rect)
    pygame.draw.rect(screen, (255, 255, 255), rect, 2)
    
    text_x = x + (final_w - txt_surf.get_width()) / 2
    text_y = y + (final_h - txt_surf.get_height()) / 2
    screen.blit(txt_surf, (text_x, text_y))
    return rect

def draw_menu(screen, font):
    screen.fill((20, 20, 20))
    rects = {}
    title = font.render("Menu", True, (0, 255, 0))
    screen.blit(title, (screen.get_width() / 2 - title.get_width() / 2, 150))
    
    btn_w, btn_h = 400, 60
    cx = screen.get_width() / 2 - btn_w / 2
    
    rects["host_online"] = draw_button(screen, font, "สร้างห้อง (Online)", cx, 250, btn_w, btn_h, (0, 100, 200))
    rects["list_online"] = draw_button(screen, font, "ค้นหาห้อง (Online)", cx, 330, btn_w, btn_h, (0, 150, 0))
    rects["host_lan"] = draw_button(screen, font, "สร้างห้อง (Local)", cx, 410, btn_w, btn_h, (200, 100, 0))
    rects["list_lan"] = draw_button(screen, font, "ค้นหาห้อง (Local)", cx, 490, btn_w, btn_h, (150, 0, 150))
    
    return rects

def draw_room_list_menu(screen, font, rooms):
    screen.fill((20, 20, 20))
    rects = {}
    title = font.render("รายชื่อห้อง", True, (255, 255, 255))
    screen.blit(title, (screen.get_width() / 2 - title.get_width() / 2, 50))
    
    btn_w, btn_h = 500, 60
    cx = screen.get_width() / 2 - btn_w / 2
    
    start_y = 130
    for i, room in enumerate(rooms):
        y = start_y + (i * 70)
        
        ip_str = f" [{room['ip']}]" if 'ip' in room else ""
        text = font.render(f"ห้อง: {room['code']} ({room['players']}/4){ip_str}", True, (255, 255, 255))
        
        # Expand box width if text is too wide
        box_w = max(btn_w, text.get_width() + 40)
        box_x = screen.get_width() / 2 - box_w / 2
        
        rects[f"room_{room['code']}"] = pygame.Rect(box_x, y, box_w, btn_h)
        pygame.draw.rect(screen, (50, 50, 50), rects[f"room_{room['code']}"])
        pygame.draw.rect(screen, (255, 255, 255), rects[f"room_{room['code']}"], 2)
        
        text_y = y + (btn_h - text.get_height()) / 2
        screen.blit(text, (box_x + 20, text_y))
                
    rects["refresh"] = draw_button(screen, font, "รีเฟรช", screen.get_width() / 2 - 210, 480, 200, 60, (100, 100, 100))
    rects["back"] = draw_button(screen, font, "กลับ", screen.get_width() / 2 + 10, 480, 200, 60, (150, 0, 0))
    return rects

def draw_name_input(screen, font, player_name):
    screen.fill((20, 20, 20))
    rects = {}
    title = font.render("ใส่ชื่อตัวละคร:", True, (255, 255, 255))
    screen.blit(title, (screen.get_width() / 2 - title.get_width() / 2, 200))
    
    box_w, box_h = 400, 60
    cx = screen.get_width() / 2 - box_w / 2
    pygame.draw.rect(screen, (50, 50, 50), (cx, 300, box_w, box_h))
    pygame.draw.rect(screen, (255, 255, 255), (cx, 300, box_w, box_h), 2)
    
    txt_surf = font.render(player_name, True, (255, 255, 0))
    txt_rect = txt_surf.get_rect(midleft=(cx + 20, 300 + box_h // 2))
    screen.blit(txt_surf, txt_rect)
    
    rects["next"] = draw_button(screen, font, "ถัดไป", cx, 400, box_w, box_h, (0, 150, 0))
    rects["back"] = draw_button(screen, font, "กลับ", cx, 500, box_w, box_h, (150, 0, 0))
    return rects

def draw_char_select(screen, font, current_color, taken_colors=[]):
    screen.fill((20, 20, 20))
    rects = {}
    colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), (255,0,255), (0,255,255), (255,165,0), (255,255,255)]
    
    title = font.render("เลือกสีตัวละคร (ห้ามซ้ำ)", True, (255, 255, 255))
    screen.blit(title, (screen.get_width() / 2 - title.get_width() / 2, 60))
    
    pygame.draw.circle(screen, current_color, (screen.get_width()//2, 170), 40)
    pygame.draw.circle(screen, (255,255,255), (screen.get_width()//2, 170), 40, 3)
    
    start_x = screen.get_width() / 2 - (len(colors) * 60) / 2
    for i, c in enumerate(colors):
        rect = pygame.Rect(start_x + i * 60, 250, 50, 50)
        pygame.draw.rect(screen, c, rect)
        if c == current_color:
            pygame.draw.rect(screen, (255, 255, 255), rect, 3)
            
        if c in taken_colors:
            pygame.draw.line(screen, (255, 0, 0), rect.topleft, rect.bottomright, 4)
            pygame.draw.line(screen, (255, 0, 0), rect.topright, rect.bottomleft, 4)
        else:
            rects[f"color_{i}"] = rect
        
    btn_w, btn_h = 400, 60
    cx = screen.get_width() / 2 - btn_w / 2
    rects["play"] = draw_button(screen, font, "เริ่มเกม", cx, 350, btn_w, btn_h, (0, 150, 0))
    rects["back"] = draw_button(screen, font, "กลับ", cx, 430, btn_w, btn_h, (150, 0, 0))
    return rects, colors

def draw_pause_menu(screen, font, players_list, local_id):
    overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))
    
    rects = {}
    title = font.render("หยุดเกมชั่วคราว", True, (255, 255, 255))
    screen.blit(title, (screen.get_width() / 2 - title.get_width() / 2, 100))

    start_y, row_spacing = 200, 60
    panel_w = 600
    panel_h = max(100, (len(players_list) * row_spacing) + 20)
    
    panel_rect = pygame.Rect(screen.get_width() / 2 - panel_w / 2, start_y, panel_w, panel_h)
    pygame.draw.rect(screen, (40, 40, 50), panel_rect)
    pygame.draw.rect(screen, (255, 255, 255), panel_rect, 2)
    
    for i, p in enumerate(players_list):
        y = start_y + 10 + (i * row_spacing)
        pygame.draw.rect(screen, p.color, (screen.get_width()/2 - 250, y, 40, 40))
        pygame.draw.rect(screen, (255,255,255), (screen.get_width()/2 - 250, y, 40, 40), 1)
        
        is_self = "(คุณ)" if p.player_id == local_id else ""
        txt = font.render(f"{p.username} {is_self}", True, (255, 255, 255))
        screen.blit(txt, (screen.get_width()/2 - 190, y + 5))

    btn_w, btn_h = 300, 50
    cx = screen.get_width() / 2 - btn_w / 2
    rects["resume"] = draw_button(screen, font, "เล่นต่อ", cx, start_y + panel_h + 30, btn_w, btn_h, (0, 150, 0))
    rects["leave"] = draw_button(screen, font, "ออกจากห้อง", cx, start_y + panel_h + 100, btn_w, btn_h, (150, 0, 0))
    return rects

def draw_status_overlay(screen, font_small, net_dict):
    mode = net_dict.get("Mode", "Unknown")
    room = net_dict.get("Room", "None")
    txt = font_small.render(f"Mode: {mode} | Room: {room} | (F3) Debug", True, (200, 200, 200))
    screen.blit(txt, (10, 10))

def draw_toast_message(screen, font, msg):
    txt = font.render(msg, True, (255, 255, 255))
    rect = txt.get_rect(midbottom=(screen.get_width() / 2, screen.get_height() - 20))
    bg_rect = rect.inflate(40, 20)
    pygame.draw.rect(screen, (50, 50, 50), bg_rect)
    pygame.draw.rect(screen, (200, 200, 200), bg_rect, 2)
    screen.blit(txt, rect)

def draw_debug_log(screen, font_small, room_code, player_pos, is_visible, server_logs):
    if not is_visible: return
    
    logs = [
        f"Room: {room_code}",
        f"Pos: X={player_pos.x:.1f}, Y={player_pos.y:.1f}",
        "-" * 20,
        "Network Logs:"
    ] + server_logs
    
    y = screen.get_height() - (len(logs) * 25) - 20
    for text in logs:
        txt = font_small.render(text, True, (255, 255, 0))
        screen.blit(txt, (10, y))
        y += 25
