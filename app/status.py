from __future__ import annotations

import json
import socket
import struct
from dataclasses import dataclass

import psutil


@dataclass(frozen=True)
class PingResult:
    online_players: int
    max_players: int
    version_name: str


def encode_varint(value: int) -> bytes:
    value &= 0xFFFFFFFF
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def parse_varint(data: bytes, offset: int = 0) -> tuple[int, int]:
    result = 0
    shift = 0
    size = 0
    while True:
        if offset + size >= len(data):
            raise ValueError("VarInt is incomplete")
        byte = data[offset + size]
        result |= (byte & 0x7F) << shift
        size += 1
        if not byte & 0x80:
            return result, size
        shift += 7
        if size > 5:
            raise ValueError("VarInt too long")


def build_status_request(host: str, port: int) -> bytes:
    host_bytes = host.encode("utf-8")
    handshake = (
        encode_varint(0)
        + encode_varint(-1)
        + encode_varint(len(host_bytes))
        + host_bytes
        + struct.pack(">H", port)
        + encode_varint(1)
    )
    status_request = encode_varint(0)
    return (
        encode_varint(len(handshake))
        + handshake
        + encode_varint(len(status_request))
        + status_request
    )


def parse_status_payload(packet: bytes) -> PingResult:
    packet_length, packet_length_size = parse_varint(packet, 0)
    available_length = len(packet) - packet_length_size
    if available_length < packet_length:
        raise ValueError("Status packet is incomplete")

    offset = packet_length_size
    packet_id, packet_id_size = parse_varint(packet, offset)
    offset += packet_id_size
    if packet_id != 0:
        raise ValueError(f"Unexpected status packet id: {packet_id}")

    json_length, json_length_size = parse_varint(packet, offset)
    offset += json_length_size
    json_bytes = packet[offset:offset + json_length]
    if len(json_bytes) < json_length:
        raise ValueError("Status JSON is incomplete")

    payload = json.loads(json_bytes.decode("utf-8"))
    players = payload["players"]
    version = payload.get("version", {})
    return PingResult(
        online_players=int(players["online"]),
        max_players=int(players["max"]),
        version_name=str(version.get("name", "unknown")),
    )


def query_server_list_ping(host: str, port: int, timeout: float = 2.0) -> PingResult | None:
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(build_status_request(host, port))
            data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    return None
                data += chunk
                try:
                    return parse_status_payload(data)
                except ValueError:
                    continue
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return None


def port_is_listening(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    if port <= 0:
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def process_resource_usage(pid: int) -> tuple[float, float] | None:
    try:
        process = psutil.Process(pid)
        memory_mb = process.memory_info().rss / 1024 / 1024
        return process.cpu_percent(interval=None), memory_mb
    except psutil.Error:
        return None
