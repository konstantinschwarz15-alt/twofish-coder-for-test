"""
Pure-Python Twofish block cipher.

Twofish is a public 128-bit block cipher designed by Bruce Schneier, John
Kelsey, Doug Whiting, David Wagner, Chris Hall and Niels Ferguson (AES
finalist). The fixed tables/constants below are dictated entirely by the
published Twofish specification. No external dependency, no C compiler
needed - runs identically on Windows, Linux, macOS and Android.
"""

MASK32 = 0xFFFFFFFF


def _rotl32(x, n):
    x &= MASK32
    return ((x << n) | (x >> (32 - n))) & MASK32


def _rotr32(x, n):
    x &= MASK32
    return ((x >> n) | (x << (32 - n))) & MASK32


def _byte(word, n):
    return (word >> (8 * n)) & 0xFF


# ---------------------------------------------------------------------------
# Fixed permutation tables (from the Twofish specification)
# ---------------------------------------------------------------------------

_QT0 = [8, 1, 7, 13, 6, 15, 3, 2, 0, 11, 5, 9, 14, 12, 10, 4]
_QT1 = [2, 8, 11, 13, 15, 7, 6, 14, 3, 1, 9, 4, 0, 10, 12, 5]
_QT2 = [14, 12, 11, 8, 1, 2, 3, 5, 15, 4, 10, 6, 7, 0, 9, 13]
_QT3 = [1, 14, 2, 11, 4, 12, 3, 7, 6, 13, 10, 5, 15, 9, 0, 8]
_QT4 = [11, 10, 5, 14, 6, 13, 9, 0, 12, 8, 15, 3, 2, 4, 7, 1]
_QT5 = [4, 12, 7, 5, 1, 6, 9, 10, 0, 14, 13, 8, 2, 11, 3, 15]
_QT6 = [13, 7, 15, 4, 1, 2, 6, 14, 9, 11, 3, 0, 8, 5, 12, 10]
_QT7 = [11, 9, 5, 1, 12, 3, 13, 14, 6, 4, 7, 15, 2, 0, 8, 10]

_ROR4 = [0, 8, 1, 9, 2, 10, 3, 11, 4, 12, 5, 13, 6, 14, 7, 15]
_ASHX = [0, 9, 2, 11, 4, 13, 6, 15, 8, 1, 10, 3, 12, 5, 14, 7]

_TAB_5B = [0, 90, 180, 238]
_TAB_EF = [0, 238, 180, 90]


def _qp(which, x):
    """Fixed byte permutation q0 (which=0) or q1 (which=1)."""
    a0 = x >> 4
    b0 = x & 15
    a1 = a0 ^ b0
    b1 = _ROR4[b0] ^ _ASHX[a0]
    a2 = (_QT0 if which == 0 else _QT1)[a1]
    b2 = (_QT2 if which == 0 else _QT3)[b1]
    a3 = a2 ^ b2
    b3 = _ROR4[b2] ^ _ASHX[a2]
    a4 = (_QT4 if which == 0 else _QT5)[a3]
    b4 = (_QT6 if which == 0 else _QT7)[b3]
    return (b4 << 4) | a4


_Q_TAB = [[_qp(w, x) for x in range(256)] for w in (0, 1)]


def _mds_rem(p0, p1):
    """Polynomial remainder step used to derive the key-dependent S-box keys."""
    for _ in range(8):
        t = p1 >> 24
        p1 = ((p1 << 8) & MASK32) | (p0 >> 24)
        p0 = (p0 << 8) & MASK32
        u = (t << 1) & MASK32
        if t & 0x80:
            u ^= 0x14D
        p1 ^= t ^ ((u << 16) & MASK32)
        u ^= (t >> 1)
        if t & 1:
            u ^= 0x14D >> 1
        p1 ^= ((u << 24) & MASK32) | ((u << 8) & MASK32)
    return p1


def _gen_m_tab():
    """Precomputed table combining the MDS matrix multiply with q0/q1."""
    m_tab = [[0] * 256 for _ in range(4)]
    for i in range(256):
        f01 = _Q_TAB[1][i]
        f5b = f01 ^ (f01 >> 2) ^ _TAB_5B[f01 & 3]
        fef = f01 ^ (f01 >> 1) ^ (f01 >> 2) ^ _TAB_EF[f01 & 3]
        m_tab[0][i] = f01 | (f5b << 8) | (fef << 16) | (fef << 24)
        m_tab[2][i] = f5b | (fef << 8) | (f01 << 16) | (fef << 24)

        f01 = _Q_TAB[0][i]
        f5b = f01 ^ (f01 >> 2) ^ _TAB_5B[f01 & 3]
        fef = f01 ^ (f01 >> 1) ^ (f01 >> 2) ^ _TAB_EF[f01 & 3]
        m_tab[1][i] = fef | (fef << 8) | (f5b << 16) | (f01 << 24)
        m_tab[3][i] = f5b | (f01 << 8) | (fef << 16) | (f5b << 24)
    return m_tab


_M_TAB = _gen_m_tab()


def _h_fun(x, key_words):
    """Key-dependent h() function mixing a 32-bit word with the round key material."""
    b0, b1, b2, b3 = _byte(x, 0), _byte(x, 1), _byte(x, 2), _byte(x, 3)
    k = len(key_words)
    if k >= 4:
        b0 = _Q_TAB[1][b0] ^ _byte(key_words[3], 0)
        b1 = _Q_TAB[0][b1] ^ _byte(key_words[3], 1)
        b2 = _Q_TAB[0][b2] ^ _byte(key_words[3], 2)
        b3 = _Q_TAB[1][b3] ^ _byte(key_words[3], 3)
    if k >= 3:
        b0 = _Q_TAB[1][b0] ^ _byte(key_words[2], 0)
        b1 = _Q_TAB[1][b1] ^ _byte(key_words[2], 1)
        b2 = _Q_TAB[0][b2] ^ _byte(key_words[2], 2)
        b3 = _Q_TAB[0][b3] ^ _byte(key_words[2], 3)
    b0 = _Q_TAB[0][_Q_TAB[0][b0] ^ _byte(key_words[1], 0)] ^ _byte(key_words[0], 0)
    b1 = _Q_TAB[0][_Q_TAB[1][b1] ^ _byte(key_words[1], 1)] ^ _byte(key_words[0], 1)
    b2 = _Q_TAB[1][_Q_TAB[0][b2] ^ _byte(key_words[1], 2)] ^ _byte(key_words[0], 2)
    b3 = _Q_TAB[1][_Q_TAB[1][b3] ^ _byte(key_words[1], 3)] ^ _byte(key_words[0], 3)
    return _M_TAB[0][b0] ^ _M_TAB[1][b1] ^ _M_TAB[2][b2] ^ _M_TAB[3][b3]


class Twofish:
    """Twofish block cipher. key: bytes, length 16, 24 or 32."""

    def __init__(self, key: bytes):
        if len(key) not in (16, 24, 32):
            raise ValueError("Twofish key must be 16, 24 or 32 bytes long")
        k_len = len(key) // 8  # 2, 3 or 4

        words = [int.from_bytes(key[i:i + 4], "little") for i in range(0, len(key), 4)]
        me_key = [words[2 * i] for i in range(k_len)]
        mo_key = [words[2 * i + 1] for i in range(k_len)]

        s_key = [0] * k_len
        for i in range(k_len):
            s_key[k_len - i - 1] = _mds_rem(me_key[i], mo_key[i])
        self._s_key = s_key

        l_key = [0] * 40
        for i in range(0, 40, 2):
            a = (0x01010101 * i) & MASK32
            b = (a + 0x01010101) & MASK32
            a = _h_fun(a, me_key)
            b = _rotl32(_h_fun(b, mo_key), 8)
            l_key[i] = (a + b) & MASK32
            l_key[i + 1] = _rotl32((a + 2 * b) & MASK32, 9)
        self._l_key = l_key

    def _g(self, word):
        return _h_fun(word, self._s_key)

    def encrypt(self, block: bytes) -> bytes:
        if len(block) != 16:
            raise ValueError("Twofish block must be 16 bytes")
        K = self._l_key
        blk = [int.from_bytes(block[i:i + 4], "little") for i in range(0, 16, 4)]
        blk[0] ^= K[0]
        blk[1] ^= K[1]
        blk[2] ^= K[2]
        blk[3] ^= K[3]

        for i in range(8):
            t1 = self._g(_rotl32(blk[1], 8))
            t0 = self._g(blk[0])
            blk[2] = _rotr32(blk[2] ^ ((t0 + t1 + K[4 * i + 8]) & MASK32), 1)
            blk[3] = _rotl32(blk[3], 1) ^ ((t0 + 2 * t1 + K[4 * i + 9]) & MASK32)

            t1 = self._g(_rotl32(blk[3], 8))
            t0 = self._g(blk[2])
            blk[0] = _rotr32(blk[0] ^ ((t0 + t1 + K[4 * i + 10]) & MASK32), 1)
            blk[1] = _rotl32(blk[1], 1) ^ ((t0 + 2 * t1 + K[4 * i + 11]) & MASK32)

        out = [blk[2] ^ K[4], blk[3] ^ K[5], blk[0] ^ K[6], blk[1] ^ K[7]]
        return b"".join(w.to_bytes(4, "little") for w in out)

    def decrypt(self, block: bytes) -> bytes:
        if len(block) != 16:
            raise ValueError("Twofish block must be 16 bytes")
        K = self._l_key
        blk = [int.from_bytes(block[i:i + 4], "little") for i in range(0, 16, 4)]
        blk[0] ^= K[4]
        blk[1] ^= K[5]
        blk[2] ^= K[6]
        blk[3] ^= K[7]

        for i in range(7, -1, -1):
            t1 = self._g(_rotl32(blk[1], 8))
            t0 = self._g(blk[0])
            blk[2] = _rotl32(blk[2], 1) ^ ((t0 + t1 + K[4 * i + 10]) & MASK32)
            blk[3] = _rotr32(blk[3] ^ ((t0 + 2 * t1 + K[4 * i + 11]) & MASK32), 1)

            t1 = self._g(_rotl32(blk[3], 8))
            t0 = self._g(blk[2])
            blk[0] = _rotl32(blk[0], 1) ^ ((t0 + t1 + K[4 * i + 8]) & MASK32)
            blk[1] = _rotr32(blk[1] ^ ((t0 + 2 * t1 + K[4 * i + 9]) & MASK32), 1)

        out = [blk[2] ^ K[0], blk[3] ^ K[1], blk[0] ^ K[2], blk[1] ^ K[3]]
        return b"".join(w.to_bytes(4, "little") for w in out)


if __name__ == "__main__":
    # Published test vector (Gladman reference implementation)
    test_key = (b'\xD4\x3B\xB7\x55\x6E\xA3\x2E\x46\xF2\xA2\x82\xB7\xD4\x5B\x4E\x0D'
                b'\x57\xFF\x73\x9D\x4D\xC9\x2C\x1B\xD7\xFC\x01\x70\x0C\xC8\x21\x6F')
    test_plain = b'\x90\xAF\xE9\x1B\xB2\x88\x54\x4F\x2C\x32\xDC\x23\x9B\x26\x35\xE6'
    expected_cipher = (b'\x6C\xB4\x56\x1C\x40\xBF\x0A\x97\x05\x93\x1C\xB6\xD4\x08\xE7\xFA')

    tf = Twofish(test_key)
    got_cipher = tf.encrypt(test_plain)
    print("cipher match:", got_cipher == expected_cipher, got_cipher.hex())
    got_plain = tf.decrypt(expected_cipher)
    print("plain match: ", got_plain == test_plain, got_plain.hex())
