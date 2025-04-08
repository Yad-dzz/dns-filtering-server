import socket
import sqlite3
import time
from dnslib import DNSRecord, QTYPE, RR, A
from flask import Flask, request
import threading
import os

# ========== CONFIG ==========
DB_FILE = "domain_cache.db"
TTL = 3600  # seconds = 1 hour
# ============================

# Create SQLite table if it doesn't exist
def init_db():
    if os.path.exists(DB_FILE):
        print("✅ Database already exists, skipping init.")
        return

    print("🛠️ Initializing database...")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE domain_cache (
            domain TEXT PRIMARY KEY,
            is_malicious INTEGER,
            timestamp INTEGER
        )
    ''')
    conn.commit()
    conn.close()

# Check cache for domain info
def check_cache(domain):
    domain = domain.lower().strip('.')
    now = int(time.time())

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT is_malicious, timestamp FROM domain_cache WHERE domain = ?", (domain,))
    row = c.fetchone()
    conn.close()

    if row:
        is_malicious, ts = row
        age = now - ts
        if age < TTL:
            print(f"[CACHE HIT] {domain} -> {'malicious' if is_malicious else 'safe'} (age: {age}s)")
            return bool(is_malicious)
        else:
            print(f"[CACHE EXPIRED] {domain}, re-analyzing...")

    return None  # Cache miss or expired

# Analyze site (with DB-backed cache)
def analyse_site(domain):
    domain = domain.lower().strip('.')
    now = int(time.time())

    cached_result = check_cache(domain)
    if cached_result is not None:
        return cached_result

    # Simulated threat intelligence
    print(f"[ANALYSIS] Analyzing {domain} ...")
    is_malicious = False  # Replace with real logic

    # Upsert into DB
    # Uncomment below if needed
    # conn = sqlite3.connect(DB_FILE)
    # c = conn.cursor()
    # c.execute('''
    #     INSERT INTO domain_cache (domain, is_malicious, timestamp)
    #     VALUES (?, ?, ?)
    #     ON CONFLICT(domain) DO UPDATE SET
    #         is_malicious=excluded.is_malicious,
    #         timestamp=excluded.timestamp
    # ''', (domain, int(is_malicious), now))
    # conn.commit()
    # conn.close()

    return is_malicious

# DNS Server Class
class DNSServer:
    def __init__(self, host='0.0.0.0', port=53):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))

    def handle_request(self, data, addr):
        request = DNSRecord.parse(data)
        qname = str(request.q.qname).lower().strip('.')

        print(f"🔍 DNS Request for: {qname}")
        response = request.reply()
        
        if analyse_site(qname):
            print(f"🚫 Blocking {qname}")
            response.add_answer(RR(qname, QTYPE.A, rdata=A("0.0.0.0")))
        else:
            print(f"✅ Allowing {qname}")

        self.sock.sendto(response.pack(), addr)

    def run(self):
        print(f"🚀 DNS Server listening on {self.host}:{self.port}")
        while True:
            data, addr = self.sock.recvfrom(512)
            self.handle_request(data, addr)

# Start DNS Server in background thread
def start_dns_server():
    server = DNSServer()
    server.run()

# Flask App for testing
app = Flask(__name__)

@app.route('/test', methods=['GET'])
def test():
    url = request.args.get('url', '').lower().strip('.')
    if not url:
        return {"error": "No URL provided"}, 400

    if analyse_site(url):
        return {"status": "bloqué", "url": url}, 403
    return {"status": "autorisé", "url": url}, 200

# Main
if __name__ == "__main__":
    init_db()  # Initialize DB schema
    threading.Thread(target=start_dns_server, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
