"""Unsigned 32-bit addition reference."""


def expected(inputs):
    return {"sum": (inputs["lhs"] + inputs["rhs"]) & 0xffffffff}
