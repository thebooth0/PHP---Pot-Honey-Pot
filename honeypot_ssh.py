#!/usr/bin/env python3
import socket
import threading
import time
import paramiko
import pymysql
from geoip_cache import get_ip_info
from sql_config import DB_CONFIG

# Clé privée du faux serveur SSH
host_key = paramiko.RSAKey.generate(2048)
SSH_BANNER = "SSH-2.0-OpenSSH_8.4p1 Raspbian-5+deb11u1"

# ---------------------------------------------------------
#   Connexion DB
# ---------------------------------------------------------
def get_db():
    return pymysql.connect(**DB_CONFIG)

# ---------------------------------------------------------
#   Logging SSH + Géoloc
# ---------------------------------------------------------
def log_event(ip, username, password):
    conn = get_db()
    cursor = conn.cursor()
    ts = time.time()

    # Log SSH
    cursor.execute("""
        INSERT INTO ssh_logs (timestamp, ip, username, password)
        VALUES (%s, %s, %s, %s)
    """, (ts, ip, username, password))

    # Geo DB
    geo = get_ip_info(ip) or {}
    cursor.execute("""
        INSERT INTO ip_geolocation
        (ip,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,asn,last_update)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            country=VALUES(country),
            countryCode=VALUES(countryCode),
            region=VALUES(region),
            regionName=VALUES(regionName),
            city=VALUES(city),
            zip=VALUES(zip),
            lat=VALUES(lat),
            lon=VALUES(lon),
            timezone=VALUES(timezone),
            isp=VALUES(isp),
            org=VALUES(org),
            asn=VALUES(asn),
            last_update=VALUES(last_update)
    """, (
        ip,
        geo.get("country"),
        geo.get("countryCode"),
        geo.get("region"),
        geo.get("regionName"),
        geo.get("city"),
        geo.get("zip"),
        geo.get("lat"),
        geo.get("lon"),
        geo.get("timezone"),
        geo.get("isp"),
        geo.get("org"),
        geo.get("as"),
        ts
    ))

    conn.close()

# ---------------------------------------------------------
#   PROXY PROTOCOL (HAProxy send-proxy)
# ---------------------------------------------------------
def receive_proxy_header(client):
    client.settimeout(2.0)
    header = b""
    while b"\r\n" not in header:
        try:
            chunk = client.recv(1)
        except socket.timeout:
            return None
        if not chunk:
            return None
        header += chunk
        if len(header) > 108:
            return None
    line = header.decode(errors="ignore").strip()
    if line.startswith("PROXY "):
        parts = line.split()
        if len(parts) >= 3:
            return parts[2]
    return None

# ---------------------------------------------------------
#   PARAMIKO SERVER
# ---------------------------------------------------------
class HoneyServer(paramiko.ServerInterface):
    def __init__(self, client_ip):
        self.client_ip = client_ip

    def get_banner(self):
        return (SSH_BANNER, "en")

    def check_auth_password(self, username, password):
        try:
            log_event(self.client_ip, username, password)
        except Exception as e:
            print("Unknown exception:", e)
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

# ---------------------------------------------------------
#   Client handler
# ---------------------------------------------------------
def handle_client(client_socket, addr):
    real_ip = receive_proxy_header(client_socket)
    ip = real_ip or addr[0]

    transport = paramiko.Transport(client_socket)
    try:
        transport.add_server_key(host_key)
        transport.local_version = SSH_BANNER
        server = HoneyServer(ip)
        try:
            transport.start_server(server=server)
        except paramiko.SSHException:
            return

        chan = transport.accept(10)
        if chan is None:
            return

        # Simule shell Raspberry Pi
        chan.send("Linux raspberrypi 5.10.0 armv7l\n")
        chan.send("raspberrypi login: ")
        time.sleep(3)
        chan.close()
    except Exception:
        pass
    finally:
        transport.close()

# ---------------------------------------------------------
#   Main listener
# ---------------------------------------------------------
def start_ssh_honeypot(port=2022):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("0.0.0.0", port))
    sock.listen(100)
    print(f"[+] SSH Honeypot actif sur le port {port}")
    while True:
        client, addr = sock.accept()
        t = threading.Thread(target=handle_client, args=(client, addr))
        t.daemon = True
        t.start()

if __name__ == "__main__":
    start_ssh_honeypot()
