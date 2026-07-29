"""Round-trip and security tests for the hardened crypto_core.py"""

import os
from crypto_core import (
    encrypt_file, decrypt_file, save_key_file, load_key_file,
    generate_key, InvalidKeyError, InvalidFileError
)

def main():
    test_dir = "test_files"
    os.makedirs(test_dir, exist_ok=True)

    original = os.path.join(test_dir, "sample.txt")
    encrypted = os.path.join(test_dir, "sample.txt.enc")
    decrypted = os.path.join(test_dir, "sample_decrypted.txt")
    keyfile = os.path.join(test_dir, "sample.key")

    # Make a file large enough to span multiple chunks (chunk size is 4MB)
    with open(original, "wb") as f:
        f.write(os.urandom(1024) + b"secret payload " * 500000)  # ~7.5MB

    # 1. Encrypt
    key = encrypt_file(original, encrypted,
                        progress_callback=lambda done, total: None)
    save_key_file(key, keyfile)
    print(f"Encrypted -> {encrypted} ({os.path.getsize(encrypted)} bytes)")

    # 2. Decrypt with correct key
    loaded_key = load_key_file(keyfile)
    decrypt_file(encrypted, decrypted, loaded_key)
    with open(original, "rb") as f1, open(decrypted, "rb") as f2:
        assert f1.read() == f2.read()
    print("PASS: round-trip matches for multi-chunk file")

    # 3. Wrong key rejected
    try:
        decrypt_file(encrypted, os.path.join(test_dir, "fail1.txt"), generate_key())
        print("FAIL: wrong key was accepted")
    except InvalidKeyError:
        print("PASS: wrong key correctly rejected")

    # 4. Corrupted file rejected
    corrupted = os.path.join(test_dir, "corrupted.enc")
    with open(encrypted, "rb") as f:
        data = bytearray(f.read())
    data[20] ^= 0xFF  # flip a byte inside the ciphertext region
    with open(corrupted, "wb") as f:
        f.write(data)
    try:
        decrypt_file(corrupted, os.path.join(test_dir, "fail2.txt"), loaded_key)
        print("FAIL: corrupted file was accepted")
    except (InvalidKeyError, InvalidFileError):
        print("PASS: corrupted file correctly rejected")

    # 5. Empty file rejected
    empty = os.path.join(test_dir, "empty.txt")
    open(empty, "wb").close()
    try:
        encrypt_file(empty, os.path.join(test_dir, "empty.enc"))
        print("FAIL: empty file was accepted")
    except InvalidFileError:
        print("PASS: empty file correctly rejected")

    # 6. Missing file rejected
    try:
        encrypt_file(os.path.join(test_dir, "does_not_exist.txt"), os.path.join(test_dir, "x.enc"))
        print("FAIL: missing file was accepted")
    except InvalidFileError:
        print("PASS: missing input file correctly rejected")

    # 7. Bad key string rejected
    try:
        load_key_file(keyfile)  # sanity: real one still works
        from crypto_core import key_from_string
        key_from_string("not-a-valid-key!!")
        print("FAIL: invalid key string was accepted")
    except InvalidKeyError:
        print("PASS: invalid key string correctly rejected")

    # 8. No leftover .tmp files after success
    leftovers = [f for f in os.listdir(test_dir) if f.endswith(".tmp")]
    assert not leftovers, f"FAIL: leftover tmp files: {leftovers}"
    print("PASS: no leftover temp files")

    print("\nAll tests completed.")

if __name__ == "__main__":
    main()