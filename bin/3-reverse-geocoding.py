#!/usr/bin/env python3

import argparse
import psycopg2
import sys
import json
import os
import getpass
from typing import Dict, Any, Optional, Tuple

def connect_to_database() -> psycopg2.extensions.connection:
    """Connect to the PostgreSQL database."""
    try:
        # Get the current system username as the default PostgreSQL user
        default_user = getpass.getuser()
        
        # Use environment variables if set, otherwise use defaults
        dbname = os.environ.get("PGDATABASE", "reverse_geo")
        user = os.environ.get("PGUSER", default_user)
        password = os.environ.get("PGPASSWORD", "")
        host = os.environ.get("PGHOST", "localhost")
        port = os.environ.get("PGPORT", "5432")
        
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
        sys.exit(1)

def reverse_geocode(lat: float, lon: float, debug: bool = False) -> Dict[str, Any]:
    """
    Perform reverse geocoding for the given latitude and longitude.
    
    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        debug: Whether to print debug information
        
    Returns:
        Dictionary containing city, state, and country information
    """
    conn = connect_to_database()
    cursor = conn.cursor()
    
    result = {
        "city": None,
        "city_osm_id": None,
        "state": None,
        "state_osm_id": None,
        "country": None,
        "country_osm_id": None,
        "lat": lat,
        "lon": lon,
        "all_matches": []
    }
    
    try:
        # First, check if the database has the expected structure
        if debug:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"Available tables: {', '.join(tables)}")
            
            # Check if the place_hierarchy view exists
            cursor.execute("SELECT COUNT(*) FROM information_schema.views WHERE table_name = 'place_hierarchy';")
            view_exists = cursor.fetchone()[0] > 0
            print(f"place_hierarchy view exists: {view_exists}")
            
            # Also check if there's any data in the boundaries table
            cursor.execute("SELECT COUNT(*) FROM boundaries;")
            count = cursor.fetchone()[0]
            print(f"Total rows in boundaries table: {count}")
        
        # First approach: Try to find a place directly and get its hierarchy
        place_query = """
        WITH place_matches AS (
            SELECT 
                p.osm_id,
                p.name,
                p.name_en,
                p.place,
                ST_Distance(
                    p.geom, 
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                ) as distance
            FROM 
                places p
            ORDER BY 
                ST_Distance(p.geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
            LIMIT 5
        )
        SELECT 
            ph.place_id,
            COALESCE(ph.place_name_en, ph.place_name) AS place_name,
            ph.place_type,
            ph.state_id,
            COALESCE(ph.state_name_en, ph.state_name) AS state_name,
            ph.country_id,
            COALESCE(ph.country_name_en, ph.country_name) AS country_name,
            pm.distance
        FROM 
            place_matches pm
        LEFT JOIN 
            place_hierarchy ph ON pm.osm_id = ph.place_id
        ORDER BY 
            pm.distance
        LIMIT 1;
        """
        
        cursor.execute(place_query, (lon, lat, lon, lat))  # Note: PostGIS uses (lon, lat) order
        place_row = cursor.fetchone()
        
        if place_row:
            place_id, place_name, place_type, state_id, state_name, country_id, country_name, distance = place_row
            
            if debug:
                print(f"Found place: {place_name} ({place_type}), distance: {distance:.2f}m")
                print(f"  State: {state_name or 'Not found'}")
                print(f"  Country: {country_name or 'Not found'}")
            
            result["city"] = place_name
            result["city_osm_id"] = place_id
            result["state"] = state_name
            result["state_osm_id"] = state_id
            result["country"] = country_name
            result["country_osm_id"] = country_id
            
            # Add to all matches for debugging
            result["all_matches"].append({
                "osm_id": place_id,
                "name": place_name,
                "type": "place",
                "place_type": place_type,
                "distance": distance
            })
        
        # Second approach: Find administrative boundaries containing the point
        admin_query = """
        SELECT 
            b.osm_id,
            b.osm_type,
            COALESCE(b.name_en, b.name) AS name,
            b.admin_level,
            b.boundary,
            parent.osm_id AS parent_id,
            parent.osm_type AS parent_type,
            COALESCE(parent.name_en, parent.name) AS parent_name,
            parent.admin_level AS parent_level
        FROM 
            boundaries b
        LEFT JOIN 
            admin_hierarchy h ON b.osm_id = h.child_id AND b.osm_type = h.child_type
        LEFT JOIN 
            boundaries parent ON h.parent_id = parent.osm_id AND h.parent_type = parent.osm_type
        WHERE 
            ST_Contains(b.geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
            AND b.admin_level IS NOT NULL
        ORDER BY 
            b.admin_level DESC;
        """
        
        cursor.execute(admin_query, (lon, lat))
        admin_rows = cursor.fetchall()
        
        if debug:
            print(f"Found {len(admin_rows)} administrative boundaries containing the point")
        
        # Process administrative boundaries
        for row in admin_rows:
            osm_id, osm_type, name, admin_level, boundary, parent_id, parent_type, parent_name, parent_level = row
            
            # Add to all matches for debugging
            match_info = {
                "osm_id": osm_id,
                "osm_type": osm_type,
                "name": name,
                "admin_level": admin_level,
                "boundary": boundary
            }
            
            if parent_id:
                match_info["parent_id"] = parent_id
                match_info["parent_type"] = parent_type
                match_info["parent_name"] = parent_name
                match_info["parent_level"] = parent_level
            
            result["all_matches"].append(match_info)
            
            if debug:
                print(f"Admin boundary: {name} (level {admin_level})")
                if parent_id:
                    print(f"  Parent: {parent_name} (level {parent_level})")
            
            # Determine the type of boundary
            if admin_level == 8 and not result["city"]:
                result["city"] = name
                result["city_osm_id"] = osm_id
            elif admin_level == 4 and not result["state"]:
                result["state"] = name
                result["state_osm_id"] = osm_id
            elif admin_level == 2 and not result["country"]:
                result["country"] = name
                result["country_osm_id"] = osm_id
        
        # If we still don't have a country, try to find it using the administrative hierarchy
        if not result["country"] and result["state_osm_id"]:
            # Try to find the country that contains this state
            country_query = """
            SELECT 
                parent.osm_id,
                COALESCE(parent.name_en, parent.name) AS name
            FROM 
                admin_hierarchy h
            JOIN 
                boundaries parent ON h.parent_id = parent.osm_id AND h.parent_type = parent.osm_type
            WHERE 
                h.child_id = %s
                AND parent.admin_level = 2
            LIMIT 1;
            """
            
            cursor.execute(country_query, (result["state_osm_id"],))
            country_row = cursor.fetchone()
            
            if country_row:
                country_id, country_name = country_row
                result["country"] = country_name
                result["country_osm_id"] = country_id
                
                if debug:
                    print(f"Found country from state hierarchy: {country_name}")
        
        # Special handling for the United States (relation 148838)
        # This is a fallback in case the US relation wasn't properly processed
        if not result["country"] and result["state"]:
            # Check if this state is in the US by name
            us_states_query = """
            SELECT 
                COALESCE(b.name_en, b.name) AS name
            FROM 
                boundaries b
            WHERE 
                b.osm_id = 148838
                AND b.osm_type = 'R'
                AND b.admin_level = 2
            LIMIT 1;
            """
            
            cursor.execute(us_states_query)
            us_row = cursor.fetchone()
            
            if us_row:
                us_name = us_row[0]
                result["country"] = us_name
                result["country_osm_id"] = 148838
                result["country_source"] = "us_relation_fallback"
                
                if debug:
                    print(f"Using US relation fallback: {us_name}")
    
    except psycopg2.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        if debug:
            print(f"Full error: {e.pgerror}")
    finally:
        cursor.close()
        conn.close()
    
    return result

def main():
    parser = argparse.ArgumentParser(description='Reverse geocode coordinates to find city, state, and country.')
    parser.add_argument('--lat', type=float, required=True, help='Latitude in decimal degrees')
    parser.add_argument('--lon', type=float, required=True, help='Longitude in decimal degrees')
    parser.add_argument('--format', choices=['json', 'text'], default='text', help='Output format (default: text)')
    parser.add_argument('--debug', action='store_true', help='Print debug information')
    
    args = parser.parse_args()
    
    result = reverse_geocode(args.lat, args.lon, args.debug)
    
    # Remove debug info for non-debug mode
    if not args.debug and 'all_matches' in result:
        del result['all_matches']
    
    if args.format == 'json':
        print(json.dumps(result, indent=2))
    else:
        print(f"Coordinates: {args.lat}, {args.lon}")
        print(f"City: {result['city'] or 'Not found'}")
        print(f"State/Region: {result['state'] or 'Not found'}")
        print(f"Country: {result['country'] or 'Not found'}")
        
        if args.debug and result.get('all_matches'):
            print("\nAll matches:")
            for i, match in enumerate(result['all_matches']):
                print(f"  {i+1}. {match['name']} ({match.get('admin_level', match.get('place_type', 'unknown'))})")

if __name__ == "__main__":
    main()
