#!/usr/bin/env python3

import sys
import json
import psycopg2
import os

def get_administrative_boundaries(lat, lon):
    """
    Returns a JSON string of all administrative boundaries
    containing the point (lat, lon).
    """
    # Adjust these to match your database credentials:
    dbname = "reverse_geo"
    dbuser = os.environ.get("USER", "gabin")  # Use system username instead of postgres
    dbpass = ""               # fill in if you require a password
    dbhost = "localhost"      # or your DB host
    dbport = 5432             # or your DB port

    connection = psycopg2.connect(
        dbname=dbname,
        user=dbuser,
        password=dbpass,
        host=dbhost,
        port=dbport
    )
    cursor = connection.cursor()

    # NOTE: ST_Point(x, y) => x=lon, y=lat
    query = """
        SELECT admin_level, name
        FROM boundaries
        WHERE ST_Contains(
            geom,
            ST_SetSRID(ST_Point(%s, %s), 4326)
        )
        ORDER BY admin_level::int;
    """

    # We pass (lon, lat) since ST_Point expects (x=lon, y=lat).
    cursor.execute(query, (lon, lat))
    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    # Build a JSON-compatible list
    boundaries_list = []
    for admin_level, name in rows:
        boundaries_list.append({
            "admin_level": admin_level,
            "name": name
        })

    # Wrap in a dict for clarity, then serialize to JSON.
    return json.dumps({"administrative_boundaries": boundaries_list}, indent=2)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 script.py <latitude> <longitude>")
        sys.exit(1)

    lat = float(sys.argv[1])
    lon = float(sys.argv[2])

    # Get the JSON of boundaries
    boundaries_json = get_administrative_boundaries(lat, lon)
    print(boundaries_json)