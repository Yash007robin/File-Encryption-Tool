"""
Flask backend for the file encryption/decryption tool.
Runs strictly on 127.0.0.1 (localhost) — never exposed to the network.
Every request uses its own temp directory, cleaned up immediately after,
so no plaintext, ciphertext, or key ever lingers on disk longer than needed.

Encrypt/decrypt results are streamed back as the raw file (not JSON+base64)
so the browser can show real upload/download progress, and the key is
passed via a response header rather than embedded in a JSON body.
"""

import io
import os
import sys
import tempfile
import threading
import webbrowser

from flask import Flask, request, render_template, send_file, jsonify
from werkzeug.utils import secure_filename

from crypto_core import (
    encrypt_file, decrypt_file, key_to_string, key_from_string,
    CryptoError, InvalidKeyError, InvalidFileError,
)


def resource_path(relative_path):
    """Resolve a path that works both in normal execution and when bundled
    by PyInstaller into a single executable (which unpacks to a temp dir
    exposed via sys._MEIPASS)."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static"),
)

# Reject absurdly large uploads at the Flask level too (defense in depth,
# on top of the check already inside crypto_core.py)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024 * 1024  # 10 GB


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/encrypt", methods=["POST"])
def encrypt_route():
    uploaded = request.files.get("file")
    if not uploaded or uploaded.filename == "":
        return jsonify({"error": "No file selected."}), 400

    safe_name = secure_filename(uploaded.filename) or "file"

    with tempfile.TemporaryDirectory() as tmp_dir:
        input_path = os.path.join(tmp_dir, safe_name)
        output_path = input_path + ".enc"
        uploaded.save(input_path)

        try:
            key = encrypt_file(input_path, output_path)
        except CryptoError as e:
            return jsonify({"error": str(e)}), 400

        with open(output_path, "rb") as f:
            encrypted_bytes = f.read()

    key_str = key_to_string(key)
    out_name = safe_name + ".enc"

    response = send_file(
        io.BytesIO(encrypted_bytes),
        as_attachment=True,
        download_name=out_name,
        mimetype="application/octet-stream",
    )
    response.headers["X-Encryption-Key"] = key_str
    response.headers["X-Filename"] = out_name
    # Custom headers are hidden from JS by default — this exposes them
    response.headers["Access-Control-Expose-Headers"] = "X-Encryption-Key, X-Filename"
    return response


@app.route("/decrypt", methods=["POST"])
def decrypt_route():
    uploaded = request.files.get("file")
    key_str = request.form.get("key", "")

    if not uploaded or uploaded.filename == "":
        return jsonify({"error": "No file selected."}), 400
    if not key_str.strip():
        return jsonify({"error": "No key provided."}), 400

    safe_name = secure_filename(uploaded.filename) or "file.enc"
    out_name = safe_name[:-4] if safe_name.endswith(".enc") else ("decrypted_" + safe_name)

    with tempfile.TemporaryDirectory() as tmp_dir:
        input_path = os.path.join(tmp_dir, safe_name)
        output_path = os.path.join(tmp_dir, out_name)
        uploaded.save(input_path)

        try:
            key = key_from_string(key_str)
            decrypt_file(input_path, output_path, key)
        except InvalidKeyError as e:
            return jsonify({"error": str(e)}), 400
        except InvalidFileError as e:
            return jsonify({"error": str(e)}), 400
        except CryptoError as e:
            return jsonify({"error": str(e)}), 400

        with open(output_path, "rb") as f:
            decrypted_bytes = f.read()

    response = send_file(
        io.BytesIO(decrypted_bytes),
        as_attachment=True,
        download_name=out_name,
        mimetype="application/octet-stream",
    )
    response.headers["X-Filename"] = out_name
    response.headers["Access-Control-Expose-Headers"] = "X-Filename"
    return response


def _open_browser():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    # Only open the browser on the actual run, not on the Flask reloader's
    # internal subprocess (which would open two tabs).
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Timer(1.0, _open_browser).start()

    # host="127.0.0.1" is deliberate and required — this must never bind
    # to 0.0.0.0 or it becomes reachable from other devices on the network.
    app.run(host="127.0.0.1", port=5000, debug=False)