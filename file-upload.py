#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import html
import uuid
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer

# Speichert per Default relativ zum Ordner, aus dem du das Skript startest
BASE_DIR = os.getcwd()
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

MAX_UPLOAD_BYTES = 250 * 1024 * 1024  # 250 MB pro Request (anpassen)
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif"}  # optional

HTML_PAGE = """<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover" />
  <title>Upload</title>
  <style>
    :root {{
      --bg: #0b0c10;
      --card: rgba(255,255,255,.06);
      --stroke: rgba(255,255,255,.10);
      --text: rgba(255,255,255,.92);
      --muted: rgba(255,255,255,.65);
      --good: #2ee59d;
      --bad: #ff5577;
    }}
    html, body {{
      height: 100%;
      margin: 0;
      background: radial-gradient(1200px 700px at 20% -10%, rgba(46,229,157,.25), transparent 55%),
                  radial-gradient(1200px 700px at 120% 20%, rgba(255,85,119,.18), transparent 60%),
                  var(--bg);
      color: var(--text);
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    }}
    .wrap {{
      padding: 16px;
      padding-bottom: 28px;
      max-width: 720px;
      margin: 0 auto;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--stroke);
      border-radius: 18px;
      padding: 16px;
      backdrop-filter: blur(10px);
      box-shadow: 0 10px 35px rgba(0,0,0,.35);
    }}
    h1 {{
      font-size: 1.2rem;
      margin: 0 0 8px;
      letter-spacing: .2px;
    }}
    .muted {{
      color: var(--muted);
      font-size: .95rem;
      line-height: 1.35rem;
      margin: 0 0 12px;
    }}
    .row {{
      display: grid;
      gap: 10px;
    }}
    .btn {{
      display: inline-flex;
      justify-content: center;
      align-items: center;
      gap: 8px;
      width: 100%;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--stroke);
      background: rgba(255,255,255,.08);
      color: var(--text);
      font-weight: 600;
      font-size: 1rem;
      cursor: pointer;
      user-select: none;
    }}
    .btn:active {{
      transform: translateY(1px);
    }}
    .btn[disabled] {{
      opacity: .55;
      cursor: not-allowed;
    }}
    .file {{
      position: relative;
      overflow: hidden;
    }}
    input[type=file] {{
      width: 100%;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px dashed rgba(255,255,255,.22);
      background: rgba(255,255,255,.04);
      color: var(--muted);
      font-size: .95rem;
    }}
    .progress {{
      margin-top: 12px;
      padding: 12px;
      border-radius: 16px;
      border: 1px solid var(--stroke);
      background: rgba(0,0,0,.25);
      display: none;
    }}
    .bar {{
      height: 12px;
      border-radius: 999px;
      background: rgba(255,255,255,.12);
      overflow: hidden;
      border: 1px solid rgba(255,255,255,.10);
    }}
    .bar > div {{
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, rgba(46,229,157,.95), rgba(46,229,157,.55));
      border-radius: 999px;
      transition: width .12s linear;
    }}
    .stats {{
      margin-top: 10px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px 10px;
      font-size: .95rem;
      color: var(--muted);
    }}
    .stats b {{
      color: var(--text);
      font-weight: 650;
    }}
    .log {{
      margin-top: 12px;
      font-size: .95rem;
      color: var(--muted);
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .pill {{
      display:inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      border: 1px solid var(--stroke);
      background: rgba(255,255,255,.06);
      color: var(--muted);
      font-size: .85rem;
    }}
    @media (min-width: 640px) {{
      .row {{
        grid-template-columns: 1fr auto;
        align-items: center;
      }}
      .btn {{
        width: auto;
        min-width: 160px;
      }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>📷 Upload auf den Laptop</h1>
      <p class="muted">
        Wähle Dateien aus und lade sie ins WLAN hoch. Mehrere Dateien sind möglich.
      </p>

      <div class="row">
        <div class="file">
          <input id="file" type="file" name="file" accept="image/*" multiple />
        </div>
        <button id="uploadBtn" class="btn">⬆️ Hochladen</button>
      </div>

      <div id="progressBox" class="progress">
        <div class="bar"><div id="barFill"></div></div>
        <div class="stats">
          <div>Fortschritt: <b id="pct">0%</b></div>
          <div>Gesendet: <b id="sent">0 MB</b> / <b id="total">0 MB</b></div>
          <div>Tempo: <b id="speed">—</b></div>
          <div>Restzeit: <b id="eta">—</b></div>
        </div>
        <div id="log" class="log"></div>
      </div>

      <div style="margin-top:14px">
        <span class="pill">Speichert nach: <code>{upload_dir}</code></span>
      </div>
    </div>
  </div>

<script>
(() => {{
  const fileEl = document.getElementById("file");
  const btn = document.getElementById("uploadBtn");
  const box = document.getElementById("progressBox");
  const fill = document.getElementById("barFill");

  const pctEl = document.getElementById("pct");
  const sentEl = document.getElementById("sent");
  const totalEl = document.getElementById("total");
  const speedEl = document.getElementById("speed");
  const etaEl = document.getElementById("eta");
  const logEl = document.getElementById("log");

  const fmtBytes = (n) => {{
    const units = ["B","KB","MB","GB"];
    let i = 0, v = n;
    while (v >= 1024 && i < units.length-1) {{ v /= 1024; i++; }}
    return `${{v.toFixed(i === 0 ? 0 : 1)}} ${{units[i]}}`;
  }};

  const fmtTime = (sec) => {{
    if (!isFinite(sec) || sec < 0) return "—";
    sec = Math.round(sec);
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    if (m <= 0) return `${{s}}s`;
    const h = Math.floor(m / 60);
    const mm = m % 60;
    if (h <= 0) return `${{mm}}m ${{s}}s`;
    return `${{h}}h ${{mm}}m`;
  }};

  btn.addEventListener("click", () => {{
    const files = fileEl.files;
    if (!files || files.length === 0) {{
      alert("Bitte mindestens eine Datei auswählen.");
      return;
    }}

    const fd = new FormData();
    for (const f of files) fd.append("file", f);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/upload", true);

    btn.disabled = true;
    fileEl.disabled = true;
    box.style.display = "block";
    logEl.textContent = "";

    const start = performance.now();
    let lastT = start;
    let lastLoaded = 0;

    const totalBytes = Array.from(files).reduce((a,f)=>a+f.size,0);
    totalEl.textContent = fmtBytes(totalBytes);

    xhr.upload.onprogress = (e) => {{
      if (!e.lengthComputable) return;
      const now = performance.now();
      const loaded = e.loaded;

      const pct = Math.min(100, Math.round((loaded / e.total) * 100));
      pctEl.textContent = pct + "%";
      sentEl.textContent = fmtBytes(loaded);

      fill.style.width = pct + "%";

      // Geschwindigkeit (gleitend über das letzte Intervall)
      const dt = (now - lastT) / 1000;
      if (dt > 0.15) {{
        const dLoaded = loaded - lastLoaded;
        const bps = dLoaded / dt;
        speedEl.textContent = fmtBytes(bps) + "/s";

        const remaining = e.total - loaded;
        const eta = bps > 1 ? remaining / bps : Infinity;
        etaEl.textContent = fmtTime(eta);

        lastT = now;
        lastLoaded = loaded;
      }}
    }};

    xhr.onreadystatechange = () => {{
      if (xhr.readyState === 4) {{
        btn.disabled = false;
        fileEl.disabled = false;

        if (xhr.status >= 200 && xhr.status < 300) {{
          // Server liefert HTML Ergebnis -> zeigen wir direkt an
          document.open();
          document.write(xhr.responseText);
          document.close();
        }} else {{
          logEl.textContent = "Fehler: HTTP " + xhr.status + "\\n" + (xhr.responseText || "");
          fill.style.width = "0%";
          pctEl.textContent = "0%";
          speedEl.textContent = "—";
          etaEl.textContent = "—";
        }}
      }}
    }};

    xhr.onerror = () => {{
      btn.disabled = false;
      fileEl.disabled = false;
      logEl.textContent = "Netzwerkfehler (XHR).";
    }};

    xhr.send(fd);
  }});
}})();
</script>
</body>
</html>
"""

def get_local_ip():
    """Ermittelt eine brauchbare LAN-IP, damit du sie am Smartphone eintippen kannst."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # nur zur Interface-Auswahl
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

def safe_filename(name: str) -> str:
    name = os.path.basename(name).strip().replace("\x00", "")
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name)
    return name or f"upload_{uuid.uuid4().hex}"

class UploadHandler(BaseHTTPRequestHandler):
    server_version = "MiniUploadHTTP/1.1"

    def _send(self, status: int, body: str, content_type="text/html; charset=utf-8"):
        data = body.encode("utf-8", errors="replace")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            page = HTML_PAGE.format(upload_dir=html.escape(UPLOAD_DIR))
            return self._send(200, page)

        if self.path == "/health":
            return self._send(200, "ok\n", content_type="text/plain; charset=utf-8")

        return self._send(404, "<h3>404 Not Found</h3>")

    def do_POST(self):
        if self.path != "/upload":
            return self._send(404, "<h3>404 Not Found</h3>")

        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return self._send(400, "<p>Kein Body empfangen.</p>")

        if length > MAX_UPLOAD_BYTES:
            return self._send(
                413,
                f"<p>Upload zu groß (max {MAX_UPLOAD_BYTES//1024//1024} MB).</p>"
            )

        ctype = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ctype:
            return self._send(400, "<p>Erwarte multipart/form-data.</p>")

        m = re.search(r'boundary=(?:"([^"]+)"|([^;]+))', ctype)
        if not m:
            return self._send(400, "<p>Boundary fehlt.</p>")
        boundary = (m.group(1) or m.group(2)).encode("utf-8")

        body = self.rfile.read(length)

        saved = []
        errors = []

        delim = b"--" + boundary
        parts = body.split(delim)

        os.makedirs(UPLOAD_DIR, exist_ok=True)

        for part in parts:
            part = part.strip()
            if not part or part in (b"--", b"--\r\n"):
                continue
            if part.startswith(b"--"):
                continue

            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue

            raw_headers = part[:header_end].decode("utf-8", errors="replace")
            content = part[header_end + 4:]
            if content.endswith(b"\r\n"):
                content = content[:-2]

            filename_m = re.search(r'filename="([^"]*)"', raw_headers, re.IGNORECASE)
            if not filename_m:
                continue

            filename = safe_filename(filename_m.group(1))
            ext = os.path.splitext(filename)[1].lower()

            if ALLOWED_EXT and ext and ext not in ALLOWED_EXT:
                errors.append(f"{html.escape(filename)}: Dateityp nicht erlaubt ({html.escape(ext)}).")
                continue

            ts = time.strftime("%Y%m%d-%H%M%S")
            unique = uuid.uuid4().hex[:8]
            out_name = f"{ts}_{unique}_{filename}"
            out_path = os.path.join(UPLOAD_DIR, out_name)

            try:
                with open(out_path, "wb") as f:
                    f.write(content)
                saved.append(out_name)
            except Exception as e:
                errors.append(f"{html.escape(filename)}: Fehler beim Speichern: {html.escape(str(e))}")

        items = "".join(f"<li style='color:#2ee59d'>{html.escape(n)}</li>" for n in saved) or "<li>—</li>"
        errs = "".join(f"<li style='color:#ff5577'>{e}</li>" for e in errors)

        resp = f"""<!doctype html><html lang="de">
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Upload Ergebnis</title>
<body style="margin:0;background:#0b0c10;color:rgba(255,255,255,.92);font-family:system-ui;padding:16px">
  <div style="max-width:720px;margin:0 auto;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.06);border-radius:18px;padding:16px">
    <h2 style="margin:0 0 8px">✅ Upload abgeschlossen</h2>
    <p style="margin:0 0 14px;color:rgba(255,255,255,.65)"><a href="/" style="color:rgba(255,255,255,.92)">← zurück</a></p>
    <h3 style="margin:12px 0 6px">Gespeichert</h3>
    <ul style="margin:0 0 12px; padding-left:18px">{items}</ul>
    {("<h3 style='margin:12px 0 6px'>Probleme</h3><ul style='margin:0; padding-left:18px'>"+errs+"</ul>") if errs else ""}
    <p style="margin-top:14px;color:rgba(255,255,255,.65)">Ordner: <code>{html.escape(UPLOAD_DIR)}</code></p>
  </div>
</body></html>"""

        return self._send(200, resp)

    def log_message(self, fmt, *args):
        sys.stdout.write("%s - - [%s] %s\n" % (
            self.address_string(),
            self.log_date_time_string(),
            fmt % args
        ))

def main():
    host = "0.0.0.0"
    port = 8000
    if len(sys.argv) >= 2:
        port = int(sys.argv[1])

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    httpd = HTTPServer((host, port), UploadHandler)
    local_ip = get_local_ip()

    print("Server läuft.")
    print(f"Auf dem Laptop:           http://127.0.0.1:{port}/")
    print(f"Im WLAN vom Smartphone:   http://{local_ip}:{port}/")
    print(f"Speicherort:              {UPLOAD_DIR}")
    print("Beenden mit Ctrl+C")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("\nServer beendet.")

if __name__ == "__main__":
    main()
