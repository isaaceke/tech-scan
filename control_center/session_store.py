"""Owner sessions encrypted for the current Windows user using DPAPI."""
import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path

class DataBlob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

def crypt(data, encrypt):
    if os.name != "nt":
        raise OSError("Windows protected session storage is unavailable")
    buffer = ctypes.create_string_buffer(data)
    source = DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = DataBlob()
    library = ctypes.WinDLL("crypt32", use_last_error=True)
    function = library.CryptProtectData if encrypt else library.CryptUnprotectData
    function.argtypes = [ctypes.POINTER(DataBlob), ctypes.c_void_p, ctypes.POINTER(DataBlob),
        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DataBlob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        free = ctypes.WinDLL("kernel32", use_last_error=True).LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        free(ctypes.cast(output.data, ctypes.c_void_p))

class SessionStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(__file__).resolve().parent / "owner_session.dat"
    def load(self):
        try:
            return json.loads(crypt(self.path.read_bytes(), False))
        except (OSError, ValueError):
            return None
    def save(self, session):
        encrypted = crypt(json.dumps(session).encode(), True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(encrypted)
        os.replace(temporary, self.path)
    def clear(self):
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass
