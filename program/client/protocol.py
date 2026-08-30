import socket
import struct
import time
from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from config import MAGIC_NUMBER, PacketType

@dataclass
class ProtocolConfig:
    server_ip: str = "127.0.0.1" 
    server_port: int = 42512
    timeout: float = 0.0
    buffer_size: int = 1024

def encodePayload(data: bytes) -> bytes:
    timestamp = int(time.time())
    return struct.pack('!I', timestamp) + data

def decodePayload(payload: bytes) -> Tuple[int, bytes]:
    if len(payload) < 4:
        raise ValueError("Payload size too small to contain Timestamp.")
    timestamp = struct.unpack('!I', payload[:4])[0]
    data = payload[4:]
    return timestamp, data

def createPacket(session_id: int, player_id: int, p_type: int, target: int, seq_num: int, data: bytes) -> bytes:
    payload = encodePayload(data)
    length = len(payload)
    
    if length > 251:
        raise ValueError(f"Payload length ({length} bytes) exceeds maximum capacity of 251 bytes.")

    header = struct.pack('!HIHBBIB', MAGIC_NUMBER, session_id, player_id, p_type, target, seq_num, length)
    return header + payload

def parsePacket(raw_packet: bytes) -> Dict:
    if len(raw_packet) < 15:
        raise ValueError("Packet is smaller than minimum Header size (15 Bytes).")

    header = raw_packet[:15]
    magic, session_id, player_id, p_type, target, seq_num, length = struct.unpack('!HIHBBIB', header)
    
    if magic != MAGIC_NUMBER:
        raise ValueError(f"Invalid Magic Number detected: {hex(magic)}")

    payload_bytes = raw_packet[15:15+length]
    timestamp, data = decodePayload(payload_bytes)

    return {
        "session_id": session_id,
        "player_id": player_id,
        "type": p_type,
        "target": target,
        "sequence": seq_num,
        "length": length,
        "timestamp": timestamp,
        "data": data,
        "raw_payload": payload_bytes
    }

def print_packet_debug(action: str, p_type: int, payload: bytes):
    hex_str = ' '.join(f'{b:02X}' for b in payload)
        
    type_name = [k for k, v in PacketType.__dict__.items() if v == p_type]
    t_name = type_name[0] if type_name else f"UNKNOWN({p_type})"
    print(f"[{action}] Type: {t_name}")
    if hex_str:
        print(f"   HEX: {hex_str}")

class UDPClient:
    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.settimeout(self.config.timeout)
        self.sock.bind(('', 0)) # Bind to dynamic port
        
        self.sequence = 0
        self.session_id = 0
        self.player_id = 0
        self.peers = {} # For P2P mode: player_id -> (ip, port)

    def sendPacket(self, p_type: int, target: int, data: bytes = b'', addr: Tuple[str, int] = None) -> None:
        self.sequence += 1
        packet_bytes = createPacket(
            session_id=self.session_id,
            player_id=self.player_id,
            p_type=p_type,
            target=target,
            seq_num=self.sequence,
            data=data
        )
        
        # Determine destination
        dst_addr = addr if addr else (self.config.server_ip, self.config.server_port)
        
        # Send
        try:
            self.sock.sendto(packet_bytes, dst_addr)
            print_packet_debug("SEND", p_type, packet_bytes[15:])
        except Exception as e:
            print(f"Send error: {e}")

    def sendP2P(self, p_type: int, data: bytes = b'') -> None:
        """Send packet to all known peers in P2P mode."""
        for peer_id, addr in self.peers.items():
            self.sendPacket(p_type, 1, data, addr=addr)

    def receivePacket(self) -> Optional[Tuple[Dict, Tuple[str, int]]]:
        try:
            raw_data, addr = self.sock.recvfrom(self.config.buffer_size)
            parsed = parsePacket(raw_data)
            print_packet_debug("RECV", parsed['type'], parsed['raw_payload'])
            return parsed, addr
        except socket.timeout:
            return None
        except BlockingIOError:
            return None
        except Exception as e:
            # print(f"Recv error: {e}")
            return None

    def close(self) -> None:
        self.sock.close()
