import struct
from typing import Union


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


class BinaryArrayBuilder:
    def __init__(self):
        self.__data = bytearray()

    @property
    def data(self):
        return bytes(self.__data)

    def add_bin_array(self, arr: Union[bytes, bytearray]):
        start_index = len(self.__data)
        self.__data += arr
        end_index = len(self.__data)
        return start_index, end_index - start_index
