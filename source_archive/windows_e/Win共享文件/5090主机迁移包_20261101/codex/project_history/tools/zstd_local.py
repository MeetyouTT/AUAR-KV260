"""Read Codex .jsonl.zst through the already installed Git libzstd; no network."""
import ctypes as C
from pathlib import Path

DLL_SOURCE = Path(r'D:\share、\项目开发\tools\PortableGit\mingw64\bin\libzstd.dll')


class Buffer(C.Structure):
    _fields_ = [('data', C.c_void_p), ('size', C.c_size_t), ('pos', C.c_size_t)]


def chunks(path):
    dll = C.CDLL(str(DLL_SOURCE))
    dll.ZSTD_createDStream.restype = C.c_void_p
    dll.ZSTD_initDStream.argtypes = [C.c_void_p]
    dll.ZSTD_initDStream.restype = C.c_size_t
    dll.ZSTD_decompressStream.argtypes = [C.c_void_p, C.POINTER(Buffer), C.POINTER(Buffer)]
    dll.ZSTD_decompressStream.restype = C.c_size_t
    dll.ZSTD_freeDStream.argtypes = [C.c_void_p]
    dll.ZSTD_isError.argtypes = [C.c_size_t]
    dll.ZSTD_isError.restype = C.c_uint
    dll.ZSTD_getErrorName.argtypes = [C.c_size_t]
    dll.ZSTD_getErrorName.restype = C.c_char_p
    state = dll.ZSTD_createDStream()
    if not state:
        raise MemoryError('ZSTD_createDStream')
    try:
        code = dll.ZSTD_initDStream(state)
        if dll.ZSTD_isError(code):
            raise ValueError('ZSTD_initDStream')
        output = C.create_string_buffer(131072)
        with Path(path).open('rb') as source:
            while True:
                data = source.read(131072)
                if not data:
                    if code != 0:
                        raise ValueError('ZSTD_TRUNCATED_FRAME')
                    break
                block = C.create_string_buffer(data)
                incoming = Buffer(C.cast(block, C.c_void_p), len(data), 0)
                while incoming.pos < incoming.size:
                    outgoing = Buffer(C.cast(output, C.c_void_p), len(output), 0)
                    code = dll.ZSTD_decompressStream(state, C.byref(outgoing), C.byref(incoming))
                    if dll.ZSTD_isError(code):
                        raise ValueError('ZSTD_DECOMPRESSION_ERROR')
                    if outgoing.pos:
                        yield output.raw[:outgoing.pos]
    finally:
        dll.ZSTD_freeDStream(state)


def lines(path):
    pending = bytearray()
    for chunk in chunks(path):
        pending.extend(chunk)
        start = 0
        while True:
            end = pending.find(b'\n', start)
            if end < 0:
                if start:
                    del pending[:start]
                break
            yield bytes(pending[start:end+1])
            start = end+1
    if pending:
        yield bytes(pending)
