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

    # Récupérer toutes les tentatives SSH
    cursor.execute("SELECT timestamp, ip, username, password FROM ssh_logs")
    rows = cursor.fetchall()

    attempts_per_hour = Counter()
    attempts_per_day = Counter()
    usernames = Counter()
    passwords = Counter()
    combos = Counter()
    ip_counts = Counter()

    for r in rows:
        ts = r["timestamp"]
        dt = datetime.fromtimestamp(ts)
        hour_str = dt.strftime("%Y-%m-%d %H:00")
        day_str = dt.strftime("%Y-%m-%d")
        attempts_per_hour[hour_str] += 1
        attempts_per_day[day_str] += 1
        if r["username"]:
            usernames[r["username"]] += 1
        if r["password"]:
            passwords[r["password"]] += 1
        if r["username"] and r["password"]:
            combos[f"{r['username']}|{r['password']}"] += 1
        if r["ip"]:
            ip_counts[r["ip"]] += 1

    # Top 100
    top_users = usernames.most_common(100)
    top_passwords = passwords.most_common(100)
    top_combos = combos.most_common(100)
    top_ips = [{"ip": ip, "count": count} for ip, count in ip_counts.most_common(100)]

    # Récupération des infos géolocalisation
    cursor.execute("SELECT * FROM ip_geolocation")
    ips_info = {r["ip"]: r for r in cursor.fetchall()}
    conn.close()

    # Préparer les infos IP pour JS
    ips_info_json = {
        ip: {
            "lat": info.get("lat", 0),
            "lon": info.get("lon", 0),
            "country": info.get("country",""),
            "regionName": info.get("regionName",""),
            "city": info.get("city",""),
            "isp": info.get("isp","")
        } for ip, info in ips_info.items()
    }

    # Convert data pour JS
    hours_labels = list(attempts_per_hour.keys())
    hours_values = list(attempts_per_hour.values())
    days_labels = list(attempts_per_day.keys())
    days_values = list(attempts_per_day.values())

    # Génération HTML
    html = f"""<!DOCTYPE html>
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
.flex-tables table {{ width: 32%; }}
.flex-charts {{ display: flex; gap: 20px; flex-wrap: wrap; }}
.flex-charts canvas {{ width: 48% !important; height: 300px !important; }}
</style>
</head>
<body>
<h1>SSH Honeypot Dashboard</h1>
<p>Généré : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

<h2>Carte des IPs</h2>
<div id="map"></div>

<h2>Tentatives par heure et par jour</h2>
<div class="flex-charts">
<canvas id="hourChart"></canvas>
<canvas id="dayChart"></canvas>
</div>

<h2>Top 100 Usernames & Passwords & Top 100 Combos</h2>
<div class="flex-tables">
<table><tr><th>Username</th><th>Count</th></tr>
{''.join(f"<tr><td>{u}</td><td>{c}</td></tr>" for u,c in top_users)}</table>

<table><tr><th>Password</th><th>Count</th></tr>
{''.join(f"<tr><td>{u}</td><td>{c}</td></tr>" for u,c in top_passwords)}</table>

<table><tr><th>Username</th><th>Password</th><th>Count</th></tr>
{''.join(f"<tr><td>{c.split('|')[0]}</td><td>{c.split('|')[1]}</td><td>{v}</td></tr>" for c,v in top_combos)}</table>

</div>

<h2>Top 100 IPs</h2>
<table>
<tr><th>IP</th><th>Country</th><th>Region</th><th>City</th><th>ISP</th><th>Count</th></tr>
{''.join(
    f"<tr><td>{ip_data['ip']}</td>"
    f"<td>{(ips_info_json.get(ip_data['ip']) or {}).get('country','')}</td>"
    f"<td>{(ips_info_json.get(ip_data['ip']) or {}).get('regionName','')}</td>"
    f"<td>{(ips_info_json.get(ip_data['ip']) or {}).get('city','')}</td>"
    f"<td>{(ips_info_json.get(ip_data['ip']) or {}).get('isp','')}</td>"
    f"<td>{ip_data['count']}</td></tr>"
    for ip_data in top_ips
)}
</table>

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
    options: {{
        responsive: true,
        scales: {{
            y: {{
                beginAtZero: true,
                ticks: {{
                    stepSize: Math.ceil(Math.max(...{json.dumps(hours_values)})/5)
                }}
            }}
        }}
    }}
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
    options: {{
        responsive: true,
        scales: {{
            y: {{
                beginAtZero: true,
                ticks: {{
                    stepSize: Math.ceil(Math.max(...{json.dumps(days_values)})/5)
                }}
            }}
        }}
    }}
}});

// Carte Leaflet
const map = L.map('map').setView([20,0], 2);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 18,
    attribution: '© OpenStreetMap'
}}).addTo(map);

// Export des IP pour JS
const ips_info = {json.dumps(ips_info_json)};
const ipData = {json.dumps(top_ips)};
const aggregated = [];
const distanceThreshold = 0.5; // environ 0.5 degrés

ipData.forEach(ip => {{
    let found = false;
    aggregated.forEach(a => {{
        if (Math.abs(a.lat - (ips_info[ip.ip]?.lat || 0)) < distanceThreshold &&
            Math.abs(a.lon - (ips_info[ip.ip]?.lon || 0)) < distanceThreshold) {{
            a.count += ip.count;
            found = true;
        }}
    }});
    if (!found) {{
        aggregated.push({{
            lat: ips_info[ip.ip]?.lat || 0,
            lon: ips_info[ip.ip]?.lon || 0,
            count: ip.count
        }});
    }}
}});

aggregated.forEach(ip => {{
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
