import json
import os
import socket
import struct
import threading

from app.status import (
    build_status_request,
    encode_varint,
    parse_status_payload,
    parse_varint,
    port_is_listening,
    process_resource_usage,
    query_server_list_ping,
)


def make_status_packet(payload: dict) -> bytes:
    body = json.dumps(payload).encode("utf-8")
    response = encode_varint(0) + encode_varint(len(body)) + body
    return encode_varint(len(response)) + response


def test_varint_roundtrip_positive_values():
    for value in (0, 1, 127, 128, 25565, 2097151):
        encoded = encode_varint(value)
        decoded, size = parse_varint(encoded, 0)
        assert decoded == value
        assert size == len(encoded)


def test_encode_negative_protocol_version_as_unsigned_32_bit():
    encoded = encode_varint(-1)
    decoded, size = parse_varint(encoded, 0)

    assert encoded == b"\xff\xff\xff\xff\x0f"
    assert decoded == 0xFFFFFFFF
    assert size == 5


def test_status_request_contains_host_port_and_request_packet():
    packet = build_status_request("127.0.0.1", 25565)

    assert b"127.0.0.1" in packet
    assert struct.pack(">H", 25565) in packet
    assert packet.endswith(encode_varint(1) + encode_varint(0))


def test_parse_status_payload():
    packet = make_status_packet(
        {
            "players": {"online": 3, "max": 20},
            "version": {"name": "1.20.1"},
        }
    )

    result = parse_status_payload(packet)

    assert result.online_players == 3
    assert result.max_players == 20
    assert result.version_name == "1.20.1"


def test_port_is_listening_with_real_socket():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    try:
        assert port_is_listening(port) is True
        assert port_is_listening(port + 1 if port < 65535 else port - 1, timeout=0.1) is False
    finally:
        listener.close()


def test_query_server_list_ping_with_fake_server():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    packet = make_status_packet({"players": {"online": 1, "max": 5}, "version": {"name": "1.20.1"}})

    def serve():
        connection, _ = listener.accept()
        with connection:
            connection.recv(4096)
            connection.sendall(packet)

    server_thread = threading.Thread(target=serve, daemon=True)
    server_thread.start()
    try:
        result = query_server_list_ping("127.0.0.1", port, timeout=2.0)
    finally:
        listener.close()
        server_thread.join(timeout=2)

    assert result is not None
    assert result.online_players == 1
    assert result.max_players == 5
    assert result.version_name == "1.20.1"


def test_process_resource_usage_for_current_process():
    usage = process_resource_usage(os.getpid())

    assert usage is not None
    cpu_percent, memory_mb = usage
    assert cpu_percent >= 0
    assert memory_mb > 0


def test_process_resource_usage_missing_pid_returns_none():
    assert process_resource_usage(999_999_999) is None
