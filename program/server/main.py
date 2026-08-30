import socket
import struct
import string
import random
import time
from typing import Dict, List, Tuple
from config import MAGIC_NUMBER, DEFAULT_PORT, PacketType, StatusCode

class Player:
    def __init__(self, pid: int, addr: Tuple[str, int], name: str, color: Tuple[int, int, int]):
        self.pid = pid
        self.addr = addr
        self.name = name
        self.color = color
        self.last_seen = time.time()
        self.x = 0.0
        self.y = 0.0

class Room:
    def __init__(self, code: str, is_p2p: bool):
        self.code = code
        self.is_p2p = is_p2p
        self.players: Dict[int, Player] = {}
        self.next_pid = 1

def generate_room_code() -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

def print_packet_debug(action: str, p_type: int, payload: bytes, addr: tuple):
    if p_type == PacketType.MOVE:
        return
        
    hex_str = ' '.join(f'{b:02X}' for b in payload)
        
    type_name = [k for k, v in PacketType.__dict__.items() if v == p_type]
    t_name = type_name[0] if type_name else f"UNKNOWN({p_type})"
    
    print(f"[{action}] Type: {t_name} | IP: {addr[0]}:{addr[1]}")
    if hex_str:
        print(f"   HEX: {hex_str}")

def encode_payload(data: bytes) -> bytes:
    timestamp = int(time.time())
    return struct.pack('!I', timestamp) + data

def decode_payload(payload: bytes) -> bytes:
    if len(payload) < 4: return b''
    return payload[4:]

def create_packet(pid: int, p_type: int, data: bytes) -> bytes:
    payload = encode_payload(data)
    length = len(payload)
    header = struct.pack('!HIHBBIB', MAGIC_NUMBER, 0, pid, p_type, 0, 0, length)
    return header + payload

def build_state_update(room: Room) -> bytes:
    count = len(room.players)
    data = struct.pack('!B', count)
    for p in room.players.values():
        name_bytes = p.name.encode('utf-8')
        name_len = len(name_bytes)
        data += struct.pack('!HBBBB', p.pid, p.color[0], p.color[1], p.color[2], name_len) + name_bytes
    return data

def cleanup_rooms(rooms: Dict[str, Room]):
    now = time.time()
    empty_rooms = []
    for code, room in rooms.items():
        # 15 seconds timeout
        timed_out = [pid for pid, p in room.players.items() if now - p.last_seen > 15.0]
        for pid in timed_out:
            del room.players[pid]
            print(f"Player {pid} timed out from room {code}")
            
        if not room.players:
            empty_rooms.append(code)
            
    for code in empty_rooms:
        del rooms[code]
        print(f"Room {code} deleted (empty)")

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', DEFAULT_PORT))
    print(f"Server started on port {DEFAULT_PORT}")
    
    rooms: Dict[str, Room] = {}
    last_cleanup = time.time()
    
    while True:
        try:
            # Check timeouts every 5 seconds
            if time.time() - last_cleanup > 5.0:
                cleanup_rooms(rooms)
                last_cleanup = time.time()
                
            raw_data, addr = sock.recvfrom(2048)
            if len(raw_data) < 15: continue
            
            magic, session_id, pid, p_type, target, seq_num, length = struct.unpack('!HIHBBIB', raw_data[:15])
            if magic != MAGIC_NUMBER: continue
            
            raw_payload = raw_data[15:15+length]
            data = decode_payload(raw_payload)
            
            if p_type != PacketType.MOVE:
                print(f"\n--- RECV FROM {addr[0]}:{addr[1]} ---")
            print_packet_debug("RECV", p_type, raw_payload, addr)
            
            # Update last_seen if player exists
            for room in rooms.values():
                if pid in room.players and room.players[pid].addr == addr:
                    room.players[pid].last_seen = time.time()

            if p_type == PacketType.LIST_ROOMS:
                online_rooms = [r for r in rooms.values() if not r.is_p2p]
                res_data = struct.pack('!B', len(online_rooms))
                for r in online_rooms:
                    res_data += r.code.encode('utf-8') + struct.pack('!B', len(r.players))

                    # ส่งสีของทุกคนในห้องกลับไป เพื่อใช้ล็อคสีตอนเลือก
                    for p in r.players.values():
                        res_data += struct.pack('!BBB', p.color[0], p.color[1], p.color[2])
                sock.sendto(create_packet(0, PacketType.LIST_ROOMS, res_data), addr)
            
            elif p_type == PacketType.CREATE_ROOM:
                try:
                    text = data.decode('utf-8')
                    name, color_str = text.split(':')
                    r, g, b = map(int, color_str.split(','))
                    
                    if len(rooms) >= 3:
                        err = create_packet(0, PacketType.ERROR, bytes([StatusCode.MAX_ROOMS_REACHED]))
                        sock.sendto(err, addr)
                        continue

                    room_code = generate_room_code()
                    room = Room(room_code, False)
                    rooms[room_code] = room
                    
                    new_pid = room.next_pid
                    room.next_pid += 1
                    player = Player(new_pid, addr, name, (r, g, b))
                    room.players[new_pid] = player
                    
                    res_data = room_code.encode('utf-8')
                    sock.sendto(create_packet(new_pid, p_type, res_data), addr)
                    print(f"Room {room_code} Created.")
                    
                    state_data = build_state_update(room)
                    sock.sendto(create_packet(0, PacketType.STATE_UPDATE, state_data), addr)
                except Exception as e:
                    print(f"Error creating room: {e}")
                    
            elif p_type == PacketType.JOIN_ROOM:
                try:
                    text = data.decode('utf-8')
                    parts = text.split(':')
                    if len(parts) != 3: continue
                    room_code, name, color_str = parts
                    req_color = tuple(map(int, color_str.split(',')))
                    
                    if room_code not in rooms:
                        err = create_packet(0, PacketType.ERROR, bytes([StatusCode.ROOM_NOT_FOUND]))
                        sock.sendto(err, addr)
                        continue
                        
                    room = rooms[room_code]
                    if len(room.players) >= 4:
                        err = create_packet(0, PacketType.ERROR, bytes([StatusCode.ROOM_FULL]))
                        sock.sendto(err, addr)
                        continue

                    # Check unique name and color
                    has_error = False
                    for p in room.players.values():
                        if p.name == name:
                            sock.sendto(create_packet(0, PacketType.ERROR, bytes([StatusCode.NAME_TAKEN])), addr)
                            has_error = True
                            break
                        if p.color == req_color:
                            sock.sendto(create_packet(0, PacketType.ERROR, bytes([StatusCode.COLOR_TAKEN])), addr)
                            has_error = True
                            break
                    if has_error: continue

                    new_pid = room.next_pid
                    room.next_pid += 1
                    player = Player(new_pid, addr, name, req_color)
                    room.players[new_pid] = player
                    
                    sock.sendto(create_packet(new_pid, p_type, room_code.encode('utf-8')), addr)
                    
                    # ส่ง STATE_UPDATE ให้ทุกคนในห้อง
                    state_data = build_state_update(room)
                    state_pkt = create_packet(0, PacketType.STATE_UPDATE, state_data)
                    for p in room.players.values():
                        sock.sendto(state_pkt, p.addr)
                            
                    print(f"Player {name} joined room {room_code}")
                except Exception as e:
                    print(f"Error joining room: {e}")
                    
            elif p_type == PacketType.LEAVE_ROOM:
                for code, room in list(rooms.items()):
                    if pid in room.players and room.players[pid].addr == addr:
                        print(f"Player {room.players[pid].name} left {code}")
                        del room.players[pid]
                        if not room.players:
                            del rooms[code]
                            print(f"Room {code} deleted (empty)")
                        else:
                            # อัปเดตสถานะให้คนในห้องรู้ว่ามีคนออกไปแล้ว
                            state_data = build_state_update(room)
                            state_pkt = create_packet(0, PacketType.STATE_UPDATE, state_data)
                            for p in room.players.values():
                                sock.sendto(state_pkt, p.addr)
                        break

            elif p_type == PacketType.MOVE:
                for room in rooms.values():
                    if pid in room.players and room.players[pid].addr == addr:
                        for p in room.players.values():
                            if p.pid != pid:
                                sock.sendto(raw_data, p.addr)
                        break
        except Exception as e:
            pass

if __name__ == "__main__":
    main()
