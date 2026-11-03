"""Software IP model for demonstration only; contains no PYNQ dependency."""


class MockIP:
    def __init__(self, contract):
        self.contract = contract
        self.offsets = {r["name"]: r["offset"] for r in contract["registers"]}
        self.values = {r["offset"]: 0 for r in contract["registers"]}
        self.trace = []

    def write(self, offset, value):
        self.trace.append(("write", offset, value))
        self.values[offset] = value
        if offset == self.offsets[self.contract["control"]["start"]["register"]]:
            self.values[self.offsets["status"]] = 0
            lhs = self.values[self.offsets["lhs"]]
            rhs = self.values[self.offsets["rhs"]]
            self.values[self.offsets["sum"]] = (lhs + rhs) % (2 ** 32)
            self.values[self.offsets["status"]] = 1

    def read(self, offset):
        self.trace.append(("read", offset))
        return self.values[offset]


def create_ip(contract):
    return MockIP(contract)
