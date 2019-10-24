import struct


def to_int16(v: int) -> bytes:
    res = struct.pack("<i", int(v))
    if res[2] or res[3]:
        raise OverflowError(v)
    return res[0:2]

def to_int32(v: int) -> bytes:
    return struct.pack("<i", int(v))

def to_float32(v: float) -> bytes:
    return struct.pack("<f", float(v))

def to_nullTerminated(v: str) -> bytes:
    return v.encode(encoding="utf8") + b'\0'
