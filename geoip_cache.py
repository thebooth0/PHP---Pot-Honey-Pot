#!/usr/bin/python3
from sql_config import DB_CONFIG
import requests
import pymysql
import time

def get_db():
    return pymysql.connect(**DB_CONFIG)

def get_ip_info(ip):
    """
    Cherche dans DB, sinon appelle l'API IP-API.
    """
    conn = get_db()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("SELECT * FROM ip_geolocation WHERE ip = %s", (ip,))
    row = cursor.fetchone()
    if row:
        conn.close()
        return row

    # Sinon appel API
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        geo = resp.json()
    except:
        geo = {}

    ts = time.time()
    cursor.execute("""
        INSERT INTO ip_geolocation
        (ip,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,asn,last_update)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
    return geo
