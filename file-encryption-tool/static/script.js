const fileInput = document.getElementById("file-input");
const dropZone = document.getElementById("drop-zone");
const fileCard = document.getElementById("file-card");
const fileName = document.getElementById("file-name");
const fileSize = document.getElementById("file-size");
const clearBtn = document.getElementById("clear-file");
const keyField = document.getElementById("key-field");
const decryptKeyInput = document.getElementById("decrypt-key");
const keyFileInput = document.getElementById("key-file-input");
const keyFileName = document.getElementById("key-file-name");

keyFileInput.addEventListener("change", async () => {
  if (!keyFileInput.files.length) return;
  const file = keyFileInput.files[0];
  const text = await file.text();
  decryptKeyInput.value = text.trim();
  keyFileName.textContent = "Loaded from " + file.name;
});
const encryptBtn = document.getElementById("encrypt-btn");
const decryptBtn = document.getElementById("decrypt-btn");

const statusCard = document.getElementById("status-card");
const statusIcon = document.getElementById("status-icon");
const statusFilename = document.getElementById("status-filename");
const statusLabel = document.getElementById("status-label");
const progressFill = document.getElementById("progress-fill");
const statusPct = document.getElementById("status-pct");
const keyResult = document.getElementById("key-result");
const errorResult = document.getElementById("error-result");

let mode = "encrypt"; // toggled by which action button was used

function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

function showFile(file) {
  fileName.textContent = file.name;
  fileSize.textContent = (file.type || "File") + " • " + formatSize(file.size);
  fileCard.hidden = false;
}

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) showFile(fileInput.files[0]);
});

dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("drag-over"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  if (e.dataTransfer.files.length) {
    fileInput.files = e.dataTransfer.files;
    showFile(fileInput.files[0]);
  }
});

clearBtn.addEventListener("click", () => {
  fileInput.value = "";
  fileCard.hidden = true;
});

decryptKeyInput.addEventListener("input", () => {
  keyFileName.textContent = "";
});

const SCRAMBLE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
function scrambleReveal(el, finalText, duration = 650) {
  const len = finalText.length;
  const startTime = performance.now();
  function frame(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const revealCount = Math.floor(progress * len);
    let out = "";
    for (let i = 0; i < len; i++) {
      out += i < revealCount ? finalText[i] : SCRAMBLE_CHARS[Math.floor(Math.random() * SCRAMBLE_CHARS.length)];
    }
    el.textContent = out;
    if (progress < 1) requestAnimationFrame(frame); else el.textContent = finalText;
  }
  requestAnimationFrame(frame);
}

function b64ToBlob(b64) {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new Blob([bytes]);
}
function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

function xhrRequest(url, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.responseType = "blob";

    // Upload phase: 0-50% of the bar
    xhr.upload.addEventListener("progress", e => {
      if (e.lengthComputable) onProgress((e.loaded / e.total) * 50);
    });
    // Download phase (server sending the result back): 50-100%
    xhr.addEventListener("progress", e => {
      if (e.lengthComputable) onProgress(50 + (e.loaded / e.total) * 50);
    });

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve({
          blob: xhr.response,
          filename: xhr.getResponseHeader("X-Filename"),
          key: xhr.getResponseHeader("X-Encryption-Key"),
        });
      } else {
        // Error responses are JSON, but responseType is "blob" — read it as text
        const reader = new FileReader();
        reader.onload = () => {
          try {
            const data = JSON.parse(reader.result);
            reject(new Error(data.error || "Request failed."));
          } catch {
            reject(new Error("Request failed."));
          }
        };
        reader.readAsText(xhr.response);
      }
    };
    xhr.onerror = () => reject(new Error("Network error — is the server still running?"));
    xhr.send(formData);
  });
}

async function runAction(actionMode) {
  errorResult.innerHTML = "";
  keyResult.innerHTML = "";

  if (!fileInput.files.length) {
    errorResult.innerHTML = '<p class="error-text">Select a file first.</p>';
    return;
  }
  if (actionMode === "decrypt" && !decryptKeyInput.value.trim()) {
    keyField.hidden = false;
    errorResult.innerHTML = '<p class="error-text">Paste the decryption key.</p>';
    return;
  }

  const file = fileInput.files[0];
  statusCard.hidden = false;
  statusIcon.textContent = actionMode === "encrypt" ? "🔒" : "🔓";
  statusFilename.textContent = file.name;
  statusLabel.textContent = actionMode === "encrypt" ? "Encrypting…" : "Decrypting…";
  encryptBtn.disabled = true;
  decryptBtn.disabled = true;
  progressFill.style.width = "0%";
  statusPct.textContent = "0%";

  const formData = new FormData();
  formData.append("file", file);
  if (actionMode === "decrypt") formData.append("key", decryptKeyInput.value.trim());

  try {
    const result = await xhrRequest(
      actionMode === "encrypt" ? "/encrypt" : "/decrypt",
      formData,
      pct => {
        progressFill.style.width = pct + "%";
        statusPct.textContent = Math.floor(pct) + "%";
      }
    );

    progressFill.style.width = "100%";
    statusPct.textContent = "100%";
    encryptBtn.disabled = false;
    decryptBtn.disabled = false;

    downloadBlob(result.blob, result.filename);

    if (actionMode === "encrypt") {
      statusLabel.textContent = "Encrypted — downloaded as " + result.filename;
      keyResult.innerHTML = `
        <p class="key-warning">SAVE THIS KEY NOW — IT CANNOT BE RECOVERED</p>
        <div class="key-box" id="key-display"></div>
        <div class="key-download-row">
          <button id="copy-key-btn" class="copy-btn">Copy Key</button>
          <button id="download-key-btn" class="copy-btn">Download .key File</button>
        </div>
      `;
      scrambleReveal(document.getElementById("key-display"), result.key);
      document.getElementById("copy-key-btn").addEventListener("click", () => {
        navigator.clipboard.writeText(result.key);
        const b = document.getElementById("copy-key-btn");
        b.textContent = "Copied"; setTimeout(() => b.textContent = "Copy Key", 1500);
      });
      document.getElementById("download-key-btn").addEventListener("click", () => {
        const keyBlob = new Blob([result.key], { type: "text/plain" });
        const baseName = result.filename.endsWith(".enc") ? result.filename.slice(0, -4) : result.filename;
        downloadBlob(keyBlob, baseName + ".key");
      });
    } else {
      statusLabel.textContent = "Decrypted — downloaded as " + result.filename;
      // Clear the key from the UI after a successful decrypt so it doesn't
      // linger on screen or get accidentally reused for a different file.
      decryptKeyInput.value = "";
      keyFileName.textContent = "";
      keyFileInput.value = "";
    }
  } catch (err) {
    encryptBtn.disabled = false;
    decryptBtn.disabled = false;
    statusLabel.textContent = "Failed";
    progressFill.style.width = "100%";
    statusPct.textContent = "—";
    errorResult.innerHTML = `<p class="error-text">✗ ${err.message}</p>`;
  }
}

function setActiveMode(newMode) {
  mode = newMode;
  encryptBtn.classList.toggle("primary", newMode === "encrypt");
  decryptBtn.classList.toggle("primary", newMode === "decrypt");
}

encryptBtn.addEventListener("click", () => {
  setActiveMode("encrypt");
  keyField.hidden = true;
  runAction("encrypt");
});

decryptBtn.addEventListener("click", () => {
  setActiveMode("decrypt");
  keyField.hidden = false;
  if (!decryptKeyInput.value.trim()) {
    errorResult.innerHTML = "";
    decryptKeyInput.focus();
    return; // let user paste key, they'll click Decrypt again
  }
  runAction("decrypt");
});