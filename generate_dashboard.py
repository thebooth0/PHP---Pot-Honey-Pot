#!/usr/bin/env python3
import pymysql
import json
from collections import Counter
from datetime import datetime
from sql_config import DB_CONFIG

OUTPUT_HTML = "index.html"

def get_db():
    return pymysql.connect(**DB_CONFIG)

def main():
    conn = get_db()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Tentatives par heure
    cursor.execute("SELECT timestamp FROM ssh_logs")
    rows = cursor.fetchall()

    attempts_per_hour = Counter()
    attempts_per_day = Counter()
    usernames = Counter()
    passwords = Counter()
    combos = Counter()
    ips = {}

    for r in rows:
        ts = r["timestamp"]
        dt = datetime.fromtimestamp(ts)
        hour_str = dt.strftime("%Y-%m-%d %H:00")
        day_str = dt.strftime("%Y-%m-%d")
        attempts_per_hour[hour_str] += 1
        attempts_per_day[day_str] += 1

    cursor.execute("SELECT username FROM ssh_logs")
    usernames.update([r["username"] for r in cursor.fetchall() if r["username"]])
    cursor.execute("SELECT password FROM ssh_logs")
    passwords.update([r["password"] for r in cursor.fetchall() if r["password"]])
    cursor.execute("SELECT username, password FROM ssh_logs")
    combos.update([f"{r['username']}|{r['password']}" for r in cursor.fetchall()])

    cursor.execute("SELECT * FROM ip_geolocation")
    for r in cursor.fetchall():
        ips[r["ip"]] = r

    conn.close()

    # Convert data pour JS
    hours_labels = list(attempts_per_hour.keys())
    hours_values = list(attempts_per_hour.values())
    days_labels = list(attempts_per_day.keys())
    days_values = list(attempts_per_day.values())
    top_users = usernames.most_common(100)
    top_passwords = passwords.most_common(100)
    top_combos = combos.most_common(100)
    top_ips = sorted(ips.values(), key=lambda x: x.get("id",0), reverse=True)[:100]

    # Génération HTML
    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>SSH Honeypot Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
<style>
body {{ font-family: Arial; margin: 30px; background: #f4f4f4; }}
h2 {{ margin-top: 50px; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 40px; }}
th, td {{ border: 1px solid #999; padding: 5px; text-align: left; font-size: 14px; }}
canvas {{ background: white; border: 1px solid #ccc; margin-bottom: 40px; }}
#map {{ height: 500px; width: 100%; margin-bottom: 40px; }}
.flex-tables {{ display: flex; gap: 20px; flex-wrap: wrap; }}
.flex-tables table {{ width: 48%; }}
</style>
</head>
<body>
<h1>SSH Honeypot Dashboard</h1>
<p>Généré : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

<h2>Tentatives par heure</h2>
<canvas id="hourChart" width="800" height="300"></canvas>

<h2>Tentatives par jour</h2>
<canvas id="dayChart" width="800" height="300"></canvas>

<h2>Top 100 Usernames & Passwords</h2>
<div class="flex-tables">
<table><tr><th>Username</th><th>Count</th></tr>
{''.join(f"<tr><td>{u}</td><td>{c}</td></tr>" for u,c in top_users)}</table>

<table><tr><th>Password</th><th>Count</th></tr>
{''.join(f"<tr><td>{u}</td><td>{c}</td></tr>" for u,c in top_passwords)}</table>
</div>

<h2>Top 100 Combos</h2>
<table><tr><th>Username</th><th>Password</th><th>Count</th></tr>
{''.join(f"<tr><td>{c.split('|')[0]}</td><td>{c.split('|')[1]}</td><td>{v}</td></tr>" for c,v in top_combos)}</table>

<h2>Top 100 IPs</h2>
<table><tr><th>IP</th><th>Country</th><th>Region</th><th>City</th><th>ISP</th></tr>
{''.join(f"<tr><td>{i['ip']}</td><td>{i.get('country')}</td><td>{i.get('regionName')}</td><td>{i.get('city')}</td><td>{i.get('isp')}</td></tr>" for i in top_ips)}
</table>

<h2>Carte des IPs</h2>
<div id="map"></div>

<script>
const hourChart = new Chart(document.getElementById('hourChart'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(hours_labels)},
        datasets: [{{
            label: 'Tentatives par heure',
            data: {json.dumps(hours_values)},
            borderWidth: 2,
            fill: false
        }}]
    }},
    options: {{ responsive: true }}
}});

const dayChart = new Chart(document.getElementById('dayChart'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(days_labels)},
        datasets: [{{
            label: 'Tentatives par jour',
            data: {json.dumps(days_values)},
            borderWidth: 2,
            fill: false
        }}]
    }},
    options: {{ responsive: true }}
}});

// Carte Leaflet
const map = L.map('map').setView([20,0], 2);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 18,
    attribution: '© OpenStreetMap'
}}).addTo(map);

const ipData = {json.dumps([
    {"lat": i.get("lat"), "lon": i.get("lon"), "count": 1} 
    for i in ips.values() if i.get("lat") and i.get("lon")
])};

ipData.forEach(ip => {{
    let radius = Math.min(ip.count * 20000, 80000);
    L.circle([ip.lat, ip.lon], {{
        color: 'red',
        fillColor: '#f03',
        fillOpacity: 0.5,
        radius: radius
    }}).addTo(map).bindPopup("Lat: " + ip.lat + ", Lon: " + ip.lon + ", count: " + ip.count);
}});
</script>
</body>
</html>
"""
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[+] Dashboard généré : {OUTPUT_HTML}")

if __name__ == "__main__":
    main()
