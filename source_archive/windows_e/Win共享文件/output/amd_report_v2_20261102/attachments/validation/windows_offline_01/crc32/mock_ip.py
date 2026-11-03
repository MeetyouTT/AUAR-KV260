"""Bit-serial CRC model, independent of the zlib golden reference.

CRC-32/ISO-HDLC over the four little-endian bytes of the input word.
Reflected polynomial 0xedb88320, initial/final xor 0xffffffff.
"""


class MockIP:
    def __init__(self, contract):
        self.contract = contract
        self.offsets = {r["name"]: r["offset"] for r in contract["registers"]}
        self.values = {r["offset"]: 0 for r in contract["registers"]}
        self.trace = []

    def write(self, offset, value):
        self.trace.append(("write", offset, value))
        self.values[offset] = value
        if offset == self.offsets["command"]:
            self.values[self.offsets["status"]] = 0
            crc = 0xffffffff
            word = self.values[self.offsets["word"]]
            for shift in (0, 8, 16, 24):
                crc ^= (word >> shift) & 255
                for _ in range(8):
                    crc = (crc >> 1) ^ (0xedb88320 if crc & 1 else 0)
            self.values[self.offsets["digest"]] = crc ^ 0xffffffff
            self.values[self.offsets["status"]] = 128

    def read(self, offset):
        self.trace.append(("read", offset))
        value = self.values[offset]
        if offset == self.offsets["status"]:
            self.values[offset] = 0
        return value


def create_ip(contract):
    return MockIP(contract)
