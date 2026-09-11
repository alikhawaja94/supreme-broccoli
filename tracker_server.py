#!/usr/bin/env python3
"""
BeeSafe AI Simulation Telemetry & Visitor Tracking Server
Captures page accesses, public IP addresses, User-Agents, and form submission events.
No external dependencies required (uses standard library).
"""

import http.server
import socketserver
import json
import datetime
import os
import sys
from urllib.parse import urlparse

# Reconfigure stdout/stderr for UTF-8 if supported on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PORT = int(os.environ.get("PORT", 8000))
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
JSONL_LOG_FILE = os.path.join(LOGS_DIR, "visitor_logs.jsonl")
TEXT_LOG_FILE = os.path.join(LOGS_DIR, "visitor_logs.txt")

os.makedirs(LOGS_DIR, exist_ok=True)

def get_client_ip(handler):
    """Extract true public IP from tunnel/proxy headers or socket connection."""
    # Cloudflare / reverse proxy headers
    for header in ("CF-Connecting-IP", "X-Real-IP", "True-Client-IP"):
        val = handler.headers.get(header)
        if val:
            return val.strip()
    
    # X-Forwarded-For can contain a comma-separated list of hops: client, proxy1, proxy2
    xff = handler.headers.get("X-Forwarded-For")
    if xff:
        parts = [p.strip() for p in xff.split(",")]
        if parts:
            return parts[0]
            
    # Direct TCP socket fallback
    return handler.client_address[0]

def log_event(event_type, client_ip, user_agent, data=None):
    """Write telemetry event to console and persistent log files."""
    now = datetime.datetime.now(datetime.timezone.utc)
    iso_time = now.isoformat()
    readable_time = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    log_entry = {
        "timestamp": iso_time,
        "event": event_type,
        "client_ip": client_ip,
        "user_agent": user_agent,
        "data": data or {}
    }

    # 1. Append structured JSONL
    try:
        with open(JSONL_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"[ERROR] Failed to write to {JSONL_LOG_FILE}: {e}", file=sys.stderr)

    # 2. Append Human-readable log
    try:
        with open(TEXT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{readable_time}] [{event_type.upper()}] IP: {client_ip}\n")
            if data:
                for k, v in data.items():
                    f.write(f"    {k}: {v}\n")
            f.write("-" * 50 + "\n")
    except Exception as e:
        print(f"[ERROR] Failed to write to {TEXT_LOG_FILE}: {e}", file=sys.stderr)

    # 3. Terminal Print Output (Windows console safe)
    if event_type == "page_visit":
        print(f"\n[{readable_time}] [!] PAGE VISIT DETECTED")
        print(f"  +- Public IP:    {client_ip}")
        print(f"  +- User Agent:   {user_agent}")
        if data:
            if data.get("referrer"):
                print(f"  +- Referrer:     {data.get('referrer')}")
            if data.get("url"):
                print(f"  +- URL / Hash:   {data.get('url')}")
        print(f"  +- Logged to:    {JSONL_LOG_FILE}")
    elif event_type == "submit":
        action = data.get("action", "SUBMIT_EVENT") if data else "SUBMIT_EVENT"
        print(f"\n[{readable_time}] [*] {action}")
        print(f"  +- Public IP:    {client_ip}")
        if data:
            print(f"  +- Applicant:    {data.get('candidateName', 'N/A')}")
            print(f"  +- Email:        {data.get('candidateEmail', 'N/A')}")
            print(f"  +- Phone:        {data.get('candidatePhone', 'N/A')}")
            print(f"  +- Visa Needed:  {data.get('selectedVisa', 'N/A')}")
            print(f"  +- Position:     {data.get('jobTitle', 'N/A')} ({data.get('jobId', 'N/A')})")
            print(f"  +- Resume File:  {data.get('resumeName', 'None')}")
            print(f"  +- Validated:    {data.get('validationPassed', False)}")
        print(f"  +- Logged to:    {JSONL_LOG_FILE}")
    else:
        print(f"\n[{readable_time}] [{event_type}] IP: {client_ip} | Data: {data}")

class TelemetryHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS so GitHub Pages or any client domain can post telemetry
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Requested-With, ngrok-skip-browser-warning")
        super().end_headers()

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests."""
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        """Handle incoming telemetry events from the website."""
        parsed_path = urlparse(self.path).path

        if parsed_path in ("/api/telemetry", "/telemetry"):
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length)

            client_ip = get_client_ip(self)
            user_agent = self.headers.get("User-Agent", "Unknown")

            try:
                payload = json.loads(post_body.decode("utf-8"))
            except Exception:
                payload = {"raw": post_body.decode("utf-8", errors="ignore")}

            event_type = payload.get("event", "unknown")
            data_fields = payload.get("data", payload)

            # Store and display event
            log_event(event_type, client_ip, user_agent, data_fields)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            response = json.dumps({"status": "recorded", "ip": client_ip}).encode("utf-8")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        else:
            self.send_error(404, "Not Found")

    def do_GET(self):
        """Serve static files or status summary."""
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            client_ip = get_client_ip(self)
            # Count logged events
            count = 0
            if os.path.exists(JSONL_LOG_FILE):
                with open(JSONL_LOG_FILE, "r", encoding="utf-8") as f:
                    count = sum(1 for _ in f)

            status = {
                "server": "BeeSafe Simulation Telemetry Server",
                "status": "online",
                "your_ip": client_ip,
                "total_events_logged": count,
                "log_path": JSONL_LOG_FILE
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            body = json.dumps(status, indent=2).encode("utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == "/logs":
            # Quick plain-text log view in browser
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            if os.path.exists(TEXT_LOG_FILE):
                with open(TEXT_LOG_FILE, "rb") as f:
                    content = f.read()
            else:
                content = b"No logs captured yet."
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            # Fall back to standard SimpleHTTPRequestHandler to serve index.html locally
            super().do_GET()

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), TelemetryHandler) as httpd:
        print("=" * 65)
        print("[*] BEESAFE SIMULATION TELEMETRY & TRACKING SERVER")
        print("=" * 65)
        print(f"[+] Local listener running at: http://localhost:{PORT}")
        print(f"[+] Live log destination:     {JSONL_LOG_FILE}")
        print(f"[+] View logs in browser:     http://localhost:{PORT}/logs")
        print(f"[+] Check server status:       http://localhost:{PORT}/api/status")
        print("=" * 65)
        print("Tunnel command to expose over HTTPS (built-in Windows SSH):")
        print(f"  ssh -R 80:localhost:{PORT} localhost.run")
        print("=" * 65)
        print("Waiting for incoming visits and submissions...\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == "__main__":
    run_server()

