"""
Twofish-CBC helper: turns arbitrary UTF-8 text into a base64 string and
back, using a random IV per message and PKCS7 padding.

Wire format (before base64): IV (16 bytes) || ciphertext (N*16 bytes)
"""
import os
import base64

from twofish_cipher import Twofish

BLOCK = 16


def _pkcs7_pad(data: bytes) -> bytes:
    pad_len = BLOCK - (len(data) % BLOCK)
    return data + bytes([pad_len]) * pad_len


def _pkcs7_unpad(data: bytes) -> bytes:
    if not data:
        raise ValueError("Leere Daten - Entschluesselung fehlgeschlagen")
    pad_len = data[-1]
    if pad_len < 1 or pad_len > BLOCK or len(data) < pad_len:
        raise ValueError("Ungueltiges Padding - falscher Schluessel oder beschaedigter Text")
    if data[-pad_len:] != bytes([pad_len]) * pad_len:
        raise ValueError("Ungueltiges Padding - falscher Schluessel oder beschaedigter Text")
    return data[:-pad_len]


def _xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def encrypt_text(key: bytes, plaintext: str) -> str:
    """Encrypt a UTF-8 string with Twofish-CBC. Returns a base64 string."""
    cipher = Twofish(key)
    data = _pkcs7_pad(plaintext.encode("utf-8"))
    iv = os.urandom(BLOCK)
    prev = iv
    out = bytearray()
    for i in range(0, len(data), BLOCK):
        block = data[i:i + BLOCK]
        enc = cipher.encrypt(_xor_bytes(block, prev))
        out += enc
        prev = enc
    return base64.b64encode(iv + bytes(out)).decode("ascii")


def decrypt_text(key: bytes, b64_ciphertext: str) -> str:
    """Decrypt a base64 Twofish-CBC string back to the original UTF-8 text."""
    try:
        raw = base64.b64decode(b64_ciphertext.strip(), validate=True)
    except Exception as exc:
        raise ValueError("Kein gueltiger Base64-Text") from exc
    if len(raw) < BLOCK * 2 or (len(raw) - BLOCK) % BLOCK != 0:
        raise ValueError("Verschluesselter Text hat eine ungueltige Laenge")
    cipher = Twofish(key)
    iv, ciphertext = raw[:BLOCK], raw[BLOCK:]
    prev = iv
    out = bytearray()
    for i in range(0, len(ciphertext), BLOCK):
        block = ciphertext[i:i + BLOCK]
        dec = cipher.decrypt(block)
        out += _xor_bytes(dec, prev)
        prev = block
    plain = _pkcs7_unpad(bytes(out))
    try:
        return plain.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Entschluesselung ergab keinen gueltigen Text - falscher Schluessel?") from exc


if __name__ == "__main__":
    key = os.urandom(32)
    msg = "Hallo Welt! Dies ist ein Test mit Umlauten: äöüß 😀"
    enc = encrypt_text(key, msg)
    print("encrypted:", enc)
    dec = decrypt_text(key, enc)
    print("match:", dec == msg)
    # wrong key must fail loudly, not silently return garbage
    try:
        decrypt_text(os.urandom(32), enc)
        print("WARNING: wrong key did not raise!")
    except ValueError as e:
        print("wrong key correctly rejected:", e)
