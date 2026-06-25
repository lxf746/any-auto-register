"""AWS event stream wire format decoder for Kiro Q Developer streaming responses."""

import struct
import zlib
from typing import Iterator


class AWSEventStreamError(Exception):
    pass


def crc32_checksum(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def iter_aws_event_stream(data: bytes) -> Iterator[tuple[dict[str, str], bytes]]:
    """Yield (headers_dict, payload_bytes) for each message in an AWS event stream.

    Wire format:
      [4B total_len][4B headers_len][4B prelude_crc]
      [headers_len bytes of headers]
      [payload bytes: total_len - 16 - headers_len]
      [4B message_crc]
    """
    offset = 0
    while offset + 12 <= len(data):
        total_len = struct.unpack_from('>I', data, offset)[0]
        headers_len = struct.unpack_from('>I', data, offset + 4)[0]

        if total_len < 12 or headers_len > total_len - 12:
            break

        prelude_crc = struct.unpack_from('>I', data, offset + 8)[0]
        if crc32_checksum(data[offset:offset + 8]) != prelude_crc:
            raise AWSEventStreamError(f"Prelude CRC mismatch at offset {offset}")

        headers_start = offset + 12
        headers_end = headers_start + headers_len
        payload_start = headers_end
        payload_end = offset + total_len - 4

        msg_crc = struct.unpack_from('>I', data, offset + total_len - 4)[0]
        if crc32_checksum(data[offset:offset + total_len - 4]) != msg_crc:
            raise AWSEventStreamError(f"Message CRC mismatch at offset {offset}")

        headers = _decode_headers(data, headers_start, headers_end)
        payload = data[payload_start:payload_end]

        yield (headers, payload)
        offset += total_len


def _decode_headers(data: bytes, start: int, end: int) -> dict[str, str]:
    headers: dict[str, str] = {}
    pos = start
    while pos < end:
        name_len = data[pos]; pos += 1
        if pos + name_len > end:
            break
        name = data[pos:pos + name_len].decode('utf-8', errors='replace'); pos += name_len
        if pos >= end:
            break
        hdr_type = data[pos]; pos += 1
        if hdr_type == 7:  # UTF-8 string
            if pos + 2 > end:
                break
            val_len = struct.unpack_from('>H', data, pos)[0]; pos += 2
            if pos + val_len > end:
                break
            val = data[pos:pos + val_len].decode('utf-8', errors='replace'); pos += val_len
        elif hdr_type == 8:  # uint8
            if pos + 1 > end:
                break
            val = str(data[pos]); pos += 1
        elif hdr_type == 2:  # int16
            if pos + 2 > end:
                break
            val = str(struct.unpack_from('>h', data, pos)[0]); pos += 2
        elif hdr_type == 3:  # int32
            if pos + 4 > end:
                break
            val = str(struct.unpack_from('>i', data, pos)[0]); pos += 4
        elif hdr_type == 4:  # int64 / int
            if pos + 8 > end:
                break
            val = str(struct.unpack_from('>q', data, pos)[0]); pos += 8
        elif hdr_type == 5:  # binary (bytes)
            if pos + 2 > end:
                break
            val_len = struct.unpack_from('>H', data, pos)[0]; pos += 2
            if pos + val_len > end:
                break
            val = data[pos:pos + val_len].hex(); pos += val_len
        elif hdr_type == 6:  # boolean (single byte: 0 or 1)
            if pos >= end:
                break
            val = "true" if data[pos] else "false"; pos += 1
        elif hdr_type == 9:  # timestamp (int64 millis since epoch)
            if pos + 8 > end:
                break
            val = str(struct.unpack_from('>q', data, pos)[0]); pos += 8
        elif hdr_type == 0:  # UUID
            if pos + 16 > end:
                break
            b = data[pos:pos + 16]; pos += 16
            val = f"{b[0:4].hex()}-{b[4:6].hex()}-{b[6:8].hex()}-{b[8:10].hex()}-{b[10:16].hex()}"
        else:
            break
        headers[name] = val
    return headers
