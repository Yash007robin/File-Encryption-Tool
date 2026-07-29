🔒 File Encryption Tool
A fully offline, local file encryption/decryption tool. AES-256-GCM, random per-file keys, no accounts, no servers, no internet required.

Your files and keys never leave your device.

Features
AES-256-GCM encryption — authenticated encryption, tamper-evident by design
Random 256-bit keys — no passwords to remember or brute-force; a new key is generated per file
Fully offline — runs as a local web app on 127.0.0.1, never reachable from your network or the internet
Streaming — large files are processed in chunks, not loaded fully into memory
Key file support — download the key as a .key file, or copy it as text
Quick Start
Windows
git clone <this-repo-url>
cd file-encryption-tool
run.bat
Mac / Linux
git clone <this-repo-url>
cd file-encryption-tool
chmod +x run.sh
./run.sh
Your browser will open automatically to http://127.0.0.1:5000. First run installs dependencies into a local virtual environment (venv/) — subsequent runs start instantly.

Manual setup (any platform)
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
How to Use
Encrypting a file:

Select or drag a file into the tool
Click Encrypt File
The encrypted .enc file downloads automatically
Save the key shown — copy it or download it as a .key file. This key cannot be recovered if lost.
Sharing an encrypted file with someone:

Send them the .enc file through one channel (e.g. email, drive link)
Send them the key through a different channel (e.g. text message, different app)
They need this same tool running locally to decrypt it
Decrypting a file:

Switch to the Decrypt tab
Select the .enc file
Paste the key, or upload the .key file
Click Decrypt File — the original file downloads automatically
Security Notes
This tool removes an entire category of risk by never using a server or network connection — but no tool can protect against everything. Understand what it does and doesn't cover:

What it protects against:

Brute-force attacks on the encrypted file (AES-256 with a truly random key is not practically breakable)
Tampering or corruption (GCM's built-in authentication rejects modified files instead of silently producing garbage)
Server breaches (there is no server — each user's own machine is both client and server)
What it does NOT protect against:

A device that is already compromised (malware, keyloggers) can read files/keys directly from disk
Losing the key — there is no recovery mechanism by design
Sending the file and key through the same channel — if intercepted together, encryption is defeated
Running a modified/untrusted copy of this tool from somewhere other than the official source
Best practices:

Always send the encrypted file and the key through separate channels
Delete .key files after successful decryption if you don't need them long-term
Only download this tool from the official repository
Building a Standalone Executable (optional)
For recipients who don't have Python installed, you can package the app into a single executable:

pip install pyinstaller
python build_exe.py
The built file appears in dist/. Anyone can run it directly — no Python, no pip install, no terminal commands needed.

Note: Build separately on each OS you want to support — a Windows build only runs on Windows, a Mac build only on Mac, etc. PyInstaller does not cross-compile.

Project Structure
file-encryption-tool/
├── app.py              # Flask backend (localhost-only)
├── crypto_core.py       # AES-256-GCM encryption engine
├── build_exe.py          # PyInstaller packaging script
├── templates/
│   └── index.html       # Web UI
├── static/
│   ├── style.css
│   └── script.js
├── test_crypto.py       # Core engine tests
├── requirements.txt
├── run.bat               # Windows one-click launcher
├── run.sh                # Mac/Linux one-click launcher
├── LICENSE
└── .gitignore
Running Tests
python test_crypto.py
Verifies encryption/decryption round-trips, rejects wrong keys and corrupted/tampered files, and confirms no leftover temp files.
