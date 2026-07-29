"""
Core encryption/decryption logic for the file encryption tool.
AES-256-GCM, random-key-based (no password derivation), streaming/chunked
so large files never need to be fully loaded into memory.

File format for .enc output:
    [4 bytes magic "FE01"][12 bytes base_nonce]
    then repeated chunks until EOF:
        [4 bytes big-endian chunk length][chunk ciphertext + 16-byte tag]

Each chunk gets its own nonce derived from base_nonce XOR chunk_index,
so nonces never repeat within a file even though the key is reused
across chunks (required for GCM security).

The 256-bit key is generated randomly at encryption time and is never
written into the .enc file — it must be saved/shared separately.
"""

import os
import base64
import struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

MAGIC = b"FE01"
NONCE_SIZE = 12          # 96-bit nonce, standard for GCM
KEY_SIZE = 32             # 256 bits
CHUNK_SIZE = 4 * 1024 * 1024   # 4 MB plaintext per chunk
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB sanity cap, adjust as needed


class CryptoError(Exception):
    """Base class for all errors raised by this module — callers (e.g. the
    Flask layer) should catch this and show a safe, generic message rather
    than leaking internals to the user."""


class InvalidKeyError(CryptoError):
    """Wrong key or corrupted/tampered file."""


class InvalidFileError(CryptoError):
    """Input file missing, empty, unreadable, or not a valid .enc file."""


def generate_key() -> bytes:
    """Generate a random 256-bit AES key."""
    return AESGCM.generate_key(bit_length=256)


def key_to_string(key: bytes) -> str:
    """Encode a raw key as a base64 string for display/saving."""
    return base64.urlsafe_b64encode(key).decode("utf-8")


def key_from_string(key_str: str) -> bytes:
    """Decode a base64 key string back to raw bytes. Raises InvalidKeyError
    if the string isn't validly formed base64 or isn't 32 bytes."""
    try:
        key = base64.urlsafe_b64decode(key_str.strip().encode("utf-8"))
    except Exception:
        raise InvalidKeyError("Key is not valid — check it was copied correctly.")
    if len(key) != KEY_SIZE:
        raise InvalidKeyError("Key is the wrong length — check it was copied correctly.")
    return key


def _derive_chunk_nonce(base_nonce: bytes, index: int) -> bytes:
    """Derive a unique per-chunk nonce by XOR-ing a big-endian counter into
    the low bytes of the base nonce. Safe for up to 2**32 chunks per file
    (with 4MB chunks that's ~16 petabytes — far beyond MAX_FILE_SIZE)."""
    counter = struct.pack(">I", index)  # 4 bytes
    prefix = base_nonce[:8]
    suffix = bytes(a ^ b for a, b in zip(base_nonce[8:], counter))
    return prefix + suffix


def _validate_input_file(path: str) -> int:
    if not os.path.isfile(path):
        raise InvalidFileError("Input file does not exist.")
    size = os.path.getsize(path)
    if size == 0:
        raise InvalidFileError("Input file is empty.")
    if size > MAX_FILE_SIZE:
        raise InvalidFileError("Input file exceeds the maximum supported size.")
    return size


def encrypt_file(input_path: str, output_path: str, key: bytes = None,
                  progress_callback=None) -> bytes:
    """
    Encrypt a file with AES-256-GCM, streamed in chunks.
    If `key` is not provided, a new random key is generated.
    Returns the key used (caller is responsible for saving/displaying it —
    this function never writes the key to disk).
    """
    total_size = _validate_input_file(input_path)

    if key is None:
        key = generate_key()
    elif len(key) != KEY_SIZE:
        raise InvalidKeyError("Provided key is the wrong length.")

    aesgcm = AESGCM(key)
    base_nonce = os.urandom(NONCE_SIZE)

    written = 0
    tmp_output = output_path + ".tmp"
    try:
        with open(input_path, "rb") as fin, open(tmp_output, "wb") as fout:
            fout.write(MAGIC)
            fout.write(base_nonce)

            index = 0
            while True:
                chunk = fin.read(CHUNK_SIZE)
                if not chunk:
                    break
                nonce = _derive_chunk_nonce(base_nonce, index)
                ciphertext = aesgcm.encrypt(nonce, chunk, associated_data=None)
                fout.write(struct.pack(">I", len(ciphertext)))
                fout.write(ciphertext)

                written += len(chunk)
                index += 1
                if progress_callback:
                    progress_callback(written, total_size)

        os.replace(tmp_output, output_path)  # atomic on same filesystem
    except Exception:
        if os.path.exists(tmp_output):
            os.remove(tmp_output)
        raise

    if progress_callback:
        progress_callback(total_size, total_size)

    return key


def decrypt_file(input_path: str, output_path: str, key: bytes,
                  progress_callback=None) -> None:
    """
    Decrypt a file previously encrypted with encrypt_file().
    Raises InvalidKeyError if the key is wrong or the file was tampered
    with/corrupted. Raises InvalidFileError if the file isn't a valid
    output of this tool.
    """
    total_size = _validate_input_file(input_path)
    if len(key) != KEY_SIZE:
        raise InvalidKeyError("Provided key is the wrong length.")

    tmp_output = output_path + ".tmp"
    try:
        with open(input_path, "rb") as fin:
            magic = fin.read(4)
            if magic != MAGIC:
                raise InvalidFileError("File is not a valid encrypted file from this tool.")
            base_nonce = fin.read(NONCE_SIZE)
            if len(base_nonce) != NONCE_SIZE:
                raise InvalidFileError("File is corrupted or truncated.")

            aesgcm = AESGCM(key)
            processed = 0
            index = 0
            with open(tmp_output, "wb") as fout:
                while True:
                    len_bytes = fin.read(4)
                    if not len_bytes:
                        break
                    if len(len_bytes) != 4:
                        raise InvalidFileError("File is corrupted or truncated.")
                    chunk_len = struct.unpack(">I", len_bytes)[0]
                    ciphertext = fin.read(chunk_len)
                    if len(ciphertext) != chunk_len:
                        raise InvalidFileError("File is corrupted or truncated.")

                    nonce = _derive_chunk_nonce(base_nonce, index)
                    try:
                        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
                    except InvalidTag:
                        raise InvalidKeyError(
                            "Decryption failed — wrong key, or the file was corrupted/tampered with."
                        )
                    fout.write(plaintext)

                    processed += chunk_len
                    index += 1
                    if progress_callback:
                        progress_callback(processed, total_size)

        os.replace(tmp_output, output_path)
    except Exception:
        if os.path.exists(tmp_output):
            os.remove(tmp_output)
        raise

    if progress_callback:
        progress_callback(total_size, total_size)


def save_key_file(key: bytes, key_path: str) -> None:
    """Save a key to a .key file as a base64 string."""
    if len(key) != KEY_SIZE:
        raise InvalidKeyError("Key is the wrong length.")
    with open(key_path, "w") as f:
        f.write(key_to_string(key))


def load_key_file(key_path: str) -> bytes:
    """Load a key from a .key file."""
    if not os.path.isfile(key_path):
        raise InvalidFileError("Key file does not exist.")
    with open(key_path, "r") as f:
        return key_from_string(f.read())