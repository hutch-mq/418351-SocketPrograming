import time
import struct
import pygame
import threading
import sys
import socket
import subprocess
import os

from config import GameConfig, PacketType, TargetType, StatusCode
from entity import ClientState, NetworkState, PlayerInfo, update_local_player, draw_all_players
from ui import (
    draw_menu, draw_room_list_menu, draw_name_input, 
    draw_char_select, draw_pause_menu, draw_status_overlay, draw_debug_log, draw_toast_message
)
from protocol import UDPClient, ProtocolConfig

class GameState:
    MENU, ROOM_LIST, ROOM_INPUT, NAME_INPUT = 0, 1, 2, 3
    CHAR_SELECT, PLAY, PAUSE = 4, 5, 6

class GameApplication:
    def __init__(self):
        pygame.init()
        self.cfg = GameConfig()
        
        self.screen = pygame.display.set_mode((self.cfg.SCREEN_WIDTH, self.cfg.SCREEN_HEIGHT))
        pygame.display.set_caption(self.cfg.TITLE)
        self.clock = pygame.time.Clock()
        
        if self.cfg.FONT_PATH:
            self.font = pygame.font.Font(self.cfg.FONT_PATH, 36)
            self.font_small = pygame.font.Font(self.cfg.FONT_PATH, 20)
        else:
            self.font = pygame.font.SysFont(None, 48)
            self.font_small = pygame.font.SysFont(None, 24)

        self._init_states()
        self._init_network()

    def _init_states(self):
        self.running = True
        self.current_state = GameState.MENU
        self.show_debug_log = False
        
        self.room_code = ""
        self.player_pos = pygame.Vector2(self.screen.get_width() / 2, self.screen.get_height() / 2)
        self.player_name = ""
        self.player_color = self.cfg.DEFAULT_COLOR
        self.local_player_id = -1
        self.is_host = False
        self.is_p2p = False
        self.online_rooms = []
        self.current_taken_colors = []

        self.ui_rects = {}
        self.color_options = []

        self.toast_msg = ""
        self.toast_timer = 0.0
        self.error_msg = ""
        self.error_timer = 0.0
        self.server_debug_logs = []
        self.default_server_ip = self.cfg.SERVER_IP
        self.local_server_process = None

    def start_local_server(self):
        if hasattr(self, 'local_server_process') and self.local_server_process:
            return
        server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'server', 'main.py'))
        self.local_server_process = subprocess.Popen([sys.executable, server_path])
        time.sleep(0.5)

    def _init_network(self):
        self.net_timer = 0.0
        self.net_tick_dt = 1.0 / self.cfg.NET_TICK_RATE
        self.last_sent_pos = pygame.Vector2(-1, -1)
        
        self.is_waiting_server = False
        self.request_time = 0.0
        self.punch_timer = 0.0

        self.net_state = NetworkState()
        self.net_config = ProtocolConfig(timeout=0.0)
        
        self.server_ip = sys.argv[1] if len(sys.argv) > 1 else self.cfg.SERVER_IP 
        self.default_server_ip = self.server_ip
        self.net_config.server_ip = self.server_ip
        
        self.udp_client = UDPClient(self.net_config)
        self.client_state = ClientState()

    def _push_server_log(self, msg: str):
        print(f"[LOG] {msg}")
        self.server_debug_logs.append(msg)
        if len(self.server_debug_logs) > 6:
            self.server_debug_logs.pop(0)

    def _show_toast(self, msg: str):
        self.toast_msg = msg
        self.toast_timer = time.time()

    def _show_error(self, msg: str, back_to_menu=True):
        self.error_msg = msg
        self.error_timer = time.time()
        self.is_waiting_server = False
        if back_to_menu:
            self.current_state = GameState.MENU
            self.room_code = ""
            self.net_state.reset()
            self.client_state.network_players.clear()

    def _parse_state_update(self, raw_data: bytes):
        if len(raw_data) < 1: return
        count = raw_data[0]
        offset = 1
        active_ids = set()
        
        for _ in range(count):
            if offset + 6 > len(raw_data): break
            pid, r, g, b, name_len = struct.unpack('!HBBBB', raw_data[offset:offset+6])
            offset += 6
            
            if offset + name_len > len(raw_data): break
            name = raw_data[offset:offset+name_len].decode('utf-8', errors='ignore')
            offset += name_len
            
            if pid != self.local_player_id:
                active_ids.add(pid)
                if pid not in self.client_state.network_players:
                    self.client_state.network_players[pid] = PlayerInfo(player_id=pid, username=name, color=(r,g,b))
                else:
                    self.client_state.network_players[pid].username = name
                    self.client_state.network_players[pid].color = (r, g, b)

        keys_to_remove = [k for k in self.client_state.network_players if k not in active_ids]
        for k in keys_to_remove:
            del self.client_state.network_players[k]
            if k in self.udp_client.peers:
                del self.udp_client.peers[k]

    def _handle_network_response(self, packet: dict, addr):
        p_type = packet['type']
        raw_data = packet['data']
        pid = packet['player_id']

        if p_type == PacketType.MOVE and len(raw_data) >= 8:
            px, py = struct.unpack('!ff', raw_data[:8])
            self.client_state.updatePosition(pid, px, py)
            return
            
        elif p_type == PacketType.STATE_UPDATE:
            self._parse_state_update(raw_data)
            return
            
        elif p_type == PacketType.LIST_ROOMS:
            if len(raw_data) >= 1:
                count = raw_data[0]
                offset = 1
                for _ in range(count):
                    if offset + 6 > len(raw_data): break
                    code = raw_data[offset:offset+5].decode('utf-8', errors='ignore')
                    players = raw_data[offset+5]
                    offset += 6
                    taken_colors = []
                    for _ in range(players):
                        if offset + 3 > len(raw_data): break
                        r, g, b = struct.unpack('!BBB', raw_data[offset:offset+3])
                        taken_colors.append((r, g, b))
                        offset += 3
                    self.online_rooms.append({"code": code, "players": players, "taken_colors": taken_colors, "ip": addr[0]})
                self.is_waiting_server = False
            return
            
        elif p_type == PacketType.ERROR and len(raw_data) >= 1:
            err_code = raw_data[0]
            if err_code == StatusCode.ROOM_NOT_FOUND: self.error_msg = "ไม่พบห้องนี้"
            elif err_code == StatusCode.ROOM_FULL: self.error_msg = "ห้องเต็มแล้ว"
            elif err_code == StatusCode.NAME_TAKEN: self.error_msg = "ชื่อนี้มีคนใช้แล้ว"
            elif err_code == StatusCode.COLOR_TAKEN: self.error_msg = "สีนี้มีคนใช้แล้ว"
            elif err_code == StatusCode.MAX_ROOMS_REACHED: self.error_msg = "ห้องเต็มเซิร์ฟเวอร์แล้ว (สร้างได้สูงสุด 3 ห้อง)"
            else: self.error_msg = "เกิดข้อผิดพลาด"
            
            self.error_timer = time.time()
            self.is_waiting_server = False
            self.current_state = GameState.MENU
            return
            
        try:
            p_data = raw_data.decode('utf-8')
            if p_data: self._push_server_log(f"MSG: {p_data}")
        except:
            p_data = ""

        if self.is_waiting_server:
            if p_type in (PacketType.CREATE_ROOM, PacketType.JOIN_ROOM) and p_data:
                self.room_code = p_data if p_type == PacketType.CREATE_ROOM else self.room_code
                self.net_state.room = self.room_code
                self.local_player_id = packet['player_id']
                self.udp_client.player_id = self.local_player_id
                self.is_waiting_server = False
                self.current_state = GameState.PLAY
                
                action = "สร้างห้อง" if p_type == PacketType.CREATE_ROOM else "เข้าร่วมห้อง"
                self.toast_msg = f"{action}สำเร็จ: {self.room_code}"
                self.toast_timer = time.time()

    def _process_network_events(self):
        while True:
            res = self.udp_client.receivePacket()
            if not res: break
            packet, addr = res
            self._handle_network_response(packet, addr)

    def _handle_mouse_click(self, mouse_pos: tuple):
        for key, rect in self.ui_rects.items():
            if not rect.collidepoint(mouse_pos) or self.is_waiting_server: continue

            if self.current_state == GameState.MENU:
                if key == "host_online":
                    self.is_host, self.is_p2p = True, False
                    self.net_state.mode = "Online"
                    self.udp_client.config.server_ip = self.default_server_ip
                    self.current_taken_colors = []
                    self.room_code, self.current_state = "", GameState.NAME_INPUT
                elif key == "list_online":
                    self.is_host, self.is_p2p = False, False
                    self.net_state.mode = "Online"
                    self.udp_client.config.server_ip = self.default_server_ip
                    self.online_rooms.clear()
                    self.udp_client.sendPacket(PacketType.LIST_ROOMS, TargetType.SERVER)
                    self.is_waiting_server = True
                    self.request_time = time.time()
                    self.current_state = GameState.ROOM_LIST
                elif key == "host_lan":
                    self.start_local_server()
                    self.is_host, self.is_p2p = True, False
                    self.net_state.mode = "Local"
                    self.udp_client.config.server_ip = "127.0.0.1"
                    self.current_taken_colors = []
                    self.room_code, self.current_state = "", GameState.NAME_INPUT
                elif key == "list_lan":
                    self.is_host, self.is_p2p = False, False
                    self.net_state.mode = "Local"
                    self.online_rooms.clear()
                    
                    # Send to both Broadcast and Localhost (for testing on same machine)
                    port = self.udp_client.config.server_port
                    self.udp_client.sendPacket(PacketType.LIST_ROOMS, TargetType.SERVER, addr=('255.255.255.255', port))
                    self.udp_client.sendPacket(PacketType.LIST_ROOMS, TargetType.SERVER, addr=('127.0.0.1', port))
                    self.is_waiting_server = True
                    self.request_time = time.time()
                    self.current_state = GameState.ROOM_LIST
                    
            elif self.current_state == GameState.ROOM_LIST:
                if key.startswith("room_"):
                    self.room_code = key.split("_")[1]
                    # หาห้องที่เลือกเพื่อดึงสีที่ถูกใช้ไปแล้ว
                    for r in self.online_rooms:
                        if r['code'] == self.room_code:
                            self.current_taken_colors = r.get('taken_colors', [])
                            if self.net_state.mode == "Local" and 'ip' in r:
                                self.udp_client.config.server_ip = r['ip']
                            break
                    self.current_state = GameState.NAME_INPUT
                elif key == "refresh":
                    self.online_rooms.clear()
                    if self.net_state.mode == "Local":
                        port = self.udp_client.config.server_port
                        self.udp_client.sendPacket(PacketType.LIST_ROOMS, TargetType.SERVER, addr=('255.255.255.255', port))
                        self.udp_client.sendPacket(PacketType.LIST_ROOMS, TargetType.SERVER, addr=('127.0.0.1', port))
                    else:
                        self.udp_client.config.server_ip = self.default_server_ip
                        self.udp_client.sendPacket(PacketType.LIST_ROOMS, TargetType.SERVER)
                    self.is_waiting_server = True
                    self.request_time = time.time()
                elif key == "back":
                    self.current_state = GameState.MENU
                    
            elif self.current_state == GameState.ROOM_INPUT:
                if key == "next" and self.room_code: self.current_state = GameState.NAME_INPUT
                elif key == "back": self.current_state = GameState.MENU
                    
            elif self.current_state == GameState.NAME_INPUT:
                if key == "next" and self.player_name: self.current_state = GameState.CHAR_SELECT
                elif key == "back": 
                    if self.is_host: self.current_state = GameState.MENU
                    elif self.is_p2p: self.current_state = GameState.ROOM_INPUT
                    else: self.current_state = GameState.ROOM_LIST
                    
            elif self.current_state == GameState.CHAR_SELECT:
                if key.startswith("color_"):
                    self.player_color = self.color_options[int(key.split("_")[1])]
                elif key == "play":
                    color_str = f"{self.player_color[0]},{self.player_color[1]},{self.player_color[2]}"
                    if self.is_host:
                        payload = f"{self.player_name}:{color_str}".encode('utf-8')
                        self.udp_client.sendPacket(PacketType.CREATE_ROOM, TargetType.SERVER, payload)
                    else:
                        payload = f"{self.room_code}:{self.player_name}:{color_str}".encode('utf-8')
                        self.udp_client.sendPacket(PacketType.JOIN_ROOM, TargetType.SERVER, payload)
                    
                    self.is_waiting_server = True
                    self.request_time = time.time()
                elif key == "back": self.current_state = GameState.NAME_INPUT
                    
            elif self.current_state == GameState.PAUSE:
                if key == "resume": self.current_state = GameState.PLAY
                elif key == "leave":
                    self.udp_client.sendPacket(PacketType.LEAVE_ROOM, TargetType.SERVER)
                    self.net_state.reset()
                    self.client_state.network_players.clear()
                    self.udp_client.peers.clear()
                    self.current_state = GameState.MENU

    def _process_input_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F3:
                    self.show_debug_log = not self.show_debug_log
                elif self.current_state == GameState.PLAY and event.key == pygame.K_ESCAPE:
                    self.current_state = GameState.PAUSE
                elif self.current_state == GameState.PAUSE and event.key == pygame.K_ESCAPE:
                    self.current_state = GameState.PLAY
                    
                if self.is_waiting_server: continue

                if self.current_state == GameState.ROOM_INPUT:
                    if event.key == pygame.K_BACKSPACE: self.room_code = self.room_code[:-1]
                    elif event.key == pygame.K_RETURN and self.room_code: self.current_state = GameState.NAME_INPUT
                    elif len(self.room_code) < 15 and event.unicode.isprintable(): self.room_code += event.unicode
                        
                elif self.current_state == GameState.NAME_INPUT:
                    if event.key == pygame.K_BACKSPACE: self.player_name = self.player_name[:-1]
                    elif event.key == pygame.K_RETURN and self.player_name: self.current_state = GameState.CHAR_SELECT
                    elif len(self.player_name) < 10 and event.unicode.isprintable(): self.player_name += event.unicode
                            
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_mouse_click(event.pos)

    def _update_and_render(self, dt: float):
        self.ui_rects.clear()
        
        if self.current_state == GameState.MENU:
            self.ui_rects = draw_menu(self.screen, self.font)
        elif self.current_state == GameState.ROOM_LIST:
            self.ui_rects = draw_room_list_menu(self.screen, self.font, self.online_rooms)
        elif self.current_state == GameState.NAME_INPUT:
            self.ui_rects = draw_name_input(self.screen, self.font, self.player_name)
        elif self.current_state == GameState.CHAR_SELECT:
            self.ui_rects, self.color_options = draw_char_select(self.screen, self.font, self.player_color, self.current_taken_colors)
            
        elif self.current_state in (GameState.PLAY, GameState.PAUSE):
            self.screen.fill((0, 0, 0))
            
            if self.current_state == GameState.PLAY:
                update_local_player(self.screen, self.player_pos, dt)
                
            #กัน Server เตะเพราะ AFK
            self.client_state.update_network_players(dt) 
            
            is_moving = self.player_pos.distance_to(self.last_sent_pos) > 1.0
            force_heartbeat = (time.time() - getattr(self, 'last_move_time', 0)) > 1.0
            
            if self.net_timer >= self.net_tick_dt:
                if is_moving or force_heartbeat:
                    payload = struct.pack('!ff', self.player_pos.x, self.player_pos.y)
                    self.udp_client.sendPacket(PacketType.MOVE, TargetType.SERVER, payload)
                    self.last_sent_pos = self.player_pos.copy()
                    self.last_move_time = time.time()
                self.net_timer = 0.0
                
            draw_all_players(self.screen, self.player_pos, self.player_name, self.player_color, self.client_state, self.font_small)
                
            if self.current_state == GameState.PAUSE:
                players_list = [PlayerInfo(player_id=self.local_player_id, username=self.player_name, color=self.player_color)]
                for pid, net_player in self.client_state.network_players.items():
                    players_list.append(net_player)
                self.ui_rects = draw_pause_menu(self.screen, self.font, players_list, self.local_player_id)

        self._render_overlays()
        pygame.display.flip()

    def _render_overlays(self):
        if self.current_state not in (GameState.MENU, GameState.ROOM_LIST):
            draw_status_overlay(self.screen, self.font_small, self.net_state.toDict())

        if self.error_msg:
            if time.time() - self.error_timer < 3.0:
                err_txt = self.font.render(self.error_msg, True, (255, 255, 255))
                err_rect = err_txt.get_rect(midtop=(self.screen.get_width() / 2, 20))
                bg_rect = err_rect.inflate(40, 20)
                pygame.draw.rect(self.screen, (180, 40, 40), bg_rect)
                pygame.draw.rect(self.screen, (255, 255, 255), bg_rect, 2)
                self.screen.blit(err_txt, err_rect)
            else: self.error_msg = ""

        if self.toast_msg:
            if time.time() - self.toast_timer < 2.0:
                draw_toast_message(self.screen, self.font_small, self.toast_msg)
            else: self.toast_msg = ""

        draw_debug_log(self.screen, self.font_small, self.room_code, self.player_pos, self.show_debug_log, self.server_debug_logs)

        # Draw waiting overlay last so it covers everything
        if self.is_waiting_server:
            overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))
            
            wait_txt = self.font.render("กำลังติดต่อเซิร์ฟเวอร์...", True, (255, 255, 0))
            txt_rect = wait_txt.get_rect(center=(self.screen.get_width() / 2, self.screen.get_height() / 2))
            self.screen.blit(wait_txt, txt_rect)

    def run(self):
        try:
            while self.running:
                dt = self.clock.tick(self.cfg.FPS) / 1000.0
                self.net_timer += dt

                self._process_network_events()

                if self.is_waiting_server and (time.time() - self.request_time > self.cfg.SERVER_TIMEOUT):
                    self._show_error("เซิร์ฟเวอร์ไม่ตอบกลับ (Timeout)", back_to_menu=True)

                self._process_input_events()
                self._update_and_render(dt)
        finally:
            if hasattr(self, 'local_server_process') and self.local_server_process:
                self.local_server_process.terminate()
                self.local_server_process.wait()
            self.udp_client.sendPacket(PacketType.LEAVE_ROOM, TargetType.SERVER)
            self.udp_client.close()
            pygame.quit()

if __name__ == "__main__":
    app = GameApplication()
    app.run()
