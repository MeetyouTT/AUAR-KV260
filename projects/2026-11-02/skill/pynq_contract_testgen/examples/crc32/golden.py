"""CRC-32 reference using Python's zlib rather than the bit-serial IP model."""
import zlib


def expected(inputs):
    return {"digest": zlib.crc32(inputs["word"].to_bytes(4, "little")) & 0xffffffff}
