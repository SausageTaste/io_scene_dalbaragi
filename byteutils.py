import struct


def to_bool1(v: bool) -> bytes:
    return b"\x01" if v else b"\x00"

def to_int16(v: int) -> bytes:
    res = struct.pack("<i", int(v))

    if v >= 0:
        if res[2] != 0 or res[3] != 0:
            raise OverflowError(v)
    else:
        if res[2] != 255 or res[3] != 255:
            raise OverflowError(v)

    return res[0:2]

def to_int32(v: int) -> bytes:
    return struct.pack("<i", int(v))

def to_float32(v: float) -> bytes:
    return struct.pack("<f", float(v))

def to_nullTerminated(v: str) -> bytes:
    return v.encode(encoding="utf8") + b'\0'
