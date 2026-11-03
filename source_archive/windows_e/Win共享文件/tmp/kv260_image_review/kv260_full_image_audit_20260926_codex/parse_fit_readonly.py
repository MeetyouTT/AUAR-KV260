#!/usr/bin/env python3
"""Read-only FIT metadata/member digest reader for an existing image.ub."""
import hashlib
import mmap
import struct
import sys

path = sys.argv[1]
with open(path, "rb") as stream:
    mm = mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ)
    if len(mm) < 40 or mm[:4] != b"\xd0\x0d\xfe\xed":
        raise SystemExit("not an FDT/FIT image")
    fields = struct.unpack_from(">10I", mm, 0)
    _, total, off_struct, off_strings, _, version, last_comp, _, size_strings, size_struct = fields
    if total > len(mm) or off_struct + size_struct > len(mm) or off_strings + size_strings > len(mm):
        raise SystemExit("invalid FDT bounds")
    strings = (off_strings, size_strings)
    nodes = {"/": {"props": {}, "children": []}}
    stack = ["/"]
    pos = off_struct

    def align4(n):
        return (n + 3) & ~3

    def cstr_at(offset, limit):
        end = mm.find(b"\0", offset, limit)
        if end < 0:
            raise ValueError("unterminated FDT string")
        return bytes(mm[offset:end]).decode("utf-8", "replace"), end + 1

    while pos < off_struct + size_struct:
        tag = struct.unpack_from(">I", mm, pos)[0]
        pos += 4
        if tag == 1:  # FDT_BEGIN_NODE
            name, pos = cstr_at(pos, off_struct + size_struct)
            pos = off_struct + align4(pos - off_struct)
            parent = stack[-1]
            current = ("/" + name) if parent == "/" else parent + "/" + name
            nodes.setdefault(current, {"props": {}, "children": []})
            nodes[parent]["children"].append(current)
            stack.append(current)
        elif tag == 2:  # FDT_END_NODE
            if len(stack) <= 1:
                raise ValueError("unbalanced end node")
            stack.pop()
        elif tag == 3:  # FDT_PROP
            length, nameoff = struct.unpack_from(">II", mm, pos)
            pos += 8
            name, _ = cstr_at(off_strings + nameoff, off_strings + size_strings)
            start = pos
            nodes[stack[-1]]["props"][name] = (start, length)
            pos += align4(length)
        elif tag == 4:  # FDT_NOP
            continue
        elif tag == 9:  # FDT_END
            break
        else:
            raise ValueError("unknown FDT structure tag %d at 0x%x" % (tag, pos - 4))

    def val(node, name):
        item = nodes[node]["props"].get(name)
        return None if item is None else bytes(mm[item[0]:item[0] + item[1]])

    def text_prop(node, name):
        raw = val(node, name)
        if raw is None:
            return "-"
        return "|".join(s.decode("utf-8", "replace") for s in raw.rstrip(b"\0").split(b"\0"))

    def uint_prop(node, name):
        raw = val(node, name)
        if raw is None:
            return None
        if len(raw) not in (4, 8):
            return None
        return int.from_bytes(raw, "big")

    def digest_range(start, length):
        h = hashlib.sha256()
        end = start + length
        if start < 0 or end > len(mm):
            raise ValueError("FIT member bounds exceed input file")
        while start < end:
            next_pos = min(start + 1024 * 1024, end)
            h.update(mm[start:next_pos])
            start = next_pos
        return h.hexdigest()

    print("FILE=%s" % path)
    print("FILE_SIZE=%d FDT_TOTALSIZE=%d FDT_VERSION=%d LAST_COMP_VERSION=%d" % (len(mm), total, version, last_comp))
    print("FIT_DESCRIPTION=%s DEFAULT_CONFIGURATION=%s" % (text_prop("/", "description"), text_prop("/configurations", "default")))
    for node in nodes.get("/images", {}).get("children", []):
        props = nodes[node]["props"]
        if "data" in props:
            data_off, data_len = props["data"]
            method = "inline"
        elif "data-position" in props:
            data_off = uint_prop(node, "data-position")
            data_len = uint_prop(node, "data-size")
            method = "data-position"
        elif "data-offset" in props:
            data_off = total + (uint_prop(node, "data-offset") or 0)
            data_len = uint_prop(node, "data-size")
            method = "data-offset-from-fdt-totalsize"
        else:
            data_off, data_len, method = None, None, "no-data-property"
        print("IMAGE=%s DESCRIPTION=%s TYPE=%s ARCH=%s OS=%s COMPRESSION=%s METHOD=%s OFFSET=%s SIZE=%s" % (
            node.rsplit("/", 1)[-1], text_prop(node, "description"), text_prop(node, "type"),
            text_prop(node, "arch"), text_prop(node, "os"), text_prop(node, "compression"),
            method, data_off, data_len))
        if data_off is not None and data_len is not None:
            computed = digest_range(data_off, data_len)
            print("  COMPUTED_SHA256=%s" % computed)
            for child in nodes[node]["children"]:
                if "/hash" in child:
                    alg = text_prop(child, "algo")
                    value = val(child, "value")
                    print("  FIT_HASH=%s:%s" % (alg, "-" if value is None else value.hex()))
    mm.close()
