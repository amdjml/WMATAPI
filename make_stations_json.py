"""
Generate stations.json from WMATA GTFS static data
Downloads WMATA's GTFS feed and creates a stations JSON file
"""

import csv
import json
import requests
import zipfile
import io
import sys
import os
from collections import defaultdict

# WMATA API URLs - require API key
WMATA_RAIL_GTFS_URL = "https://api.wmata.com/gtfs/rail-gtfs-static.zip"
WMATA_BUS_GTFS_URL = "https://api.wmata.com/gtfs/bus-gtfs-static.zip"


def get_api_key():
    """Get API key from environment or settings file"""
    # Try environment variable first
    api_key = os.environ.get('WMATA_API_KEY')
    
    if not api_key:
        # Try to read from settings.cfg
        try:
            with open('settings.cfg', 'r') as f:
                for line in f:
                    if line.startswith('WMATA_API_KEY'):
                        api_key = line.split('=')[1].strip().strip('"').strip("'")
                        break
        except FileNotFoundError:
            pass
    
    if not api_key:
        print("Error: WMATA_API_KEY not found!")
        print("Set it via environment variable or in settings.cfg")
        print("\nExample:")
        print("  export WMATA_API_KEY=your_key_here")
        print("  python make_stations_json.py")
        sys.exit(1)
    
    return api_key


def download_and_extract_gtfs(api_key):
    """Download and extract WMATA GTFS static data"""
    print(f"Downloading WMATA Rail GTFS data from {WMATA_RAIL_GTFS_URL}...")
    
    headers = {'api_key': api_key}
    response = requests.get(WMATA_RAIL_GTFS_URL, headers=headers)
    
    if response.status_code == 401:
        print("Error: 401 Unauthorized. Check your WMATA_API_KEY")
        sys.exit(1)
    elif response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    print("Extracting files...")
    z = zipfile.ZipFile(io.BytesIO(response.content))
    
    # Read required files
    stops_data = z.read('stops.txt').decode('utf-8-sig')
    routes_data = z.read('routes.txt').decode('utf-8-sig')
    
    try:
        stop_times_data = z.read('stop_times.txt').decode('utf-8-sig')
        trips_data = z.read('trips.txt').decode('utf-8-sig')
    except KeyError:
        print("Warning: stop_times.txt or trips.txt not found")
        stop_times_data = None
        trips_data = None
    
    return stops_data, routes_data, stop_times_data, trips_data


def parse_stops(stops_data):
    """Parse stops.txt into station dictionary"""
    stations = {}
    reader = csv.DictReader(io.StringIO(stops_data))
    
    for row in reader:
        stop_id = row['stop_id'].strip()
        stop_name = row['stop_name'].strip()
        stop_lat = float(row['stop_lat'])
        stop_lon = float(row['stop_lon'])
        
        # WMATA uses location_type to distinguish stations from platforms
        # location_type 1 = station, 0 = stop/platform
        location_type = row.get('location_type', '0')
        
        # Skip platform-specific stops if there's a parent station
        if row.get('parent_station') and row['parent_station'].strip():
            continue
        
        stations[stop_id] = {
            'name': stop_name,
            'lat': stop_lat,
            'lon': stop_lon,
            'routes': set(),
            'location_type': location_type
        }
    
    return stations


def parse_routes(routes_data):
    """Parse routes.txt to get route info"""
    routes = {}
    reader = csv.DictReader(io.StringIO(routes_data))
    
    for row in reader:
        route_id = row['route_id'].strip()
        route_short_name = row.get('route_short_name', '').strip()
        route_long_name = row.get('route_long_name', '').strip()
        
        # Use short name if available, otherwise long name
        route_name = route_short_name or route_long_name
        
        routes[route_id] = {
            'name': route_name,
            'short_name': route_short_name,
            'long_name': route_long_name
        }
    
    return routes


def add_routes_to_stations(stations, routes, trips_data, stop_times_data):
    """Add route information to stations based on trips and stop_times"""
    if not trips_data or not stop_times_data:
        print("Warning: Cannot map routes to stations without trips and stop_times data")
        return stations
    
    print("Mapping routes to stations...")
    
    # Build trip_id -> route_id mapping
    trip_routes = {}
    reader = csv.DictReader(io.StringIO(trips_data))
    for row in reader:
        trip_id = row['trip_id'].strip()
        route_id = row['route_id'].strip()
        trip_routes[trip_id] = route_id
    
    # Map stops to routes via stop_times
    reader = csv.DictReader(io.StringIO(stop_times_data))
    for row in reader:
        trip_id = row['trip_id'].strip()
        stop_id = row['stop_id'].strip()
        
        if trip_id in trip_routes:
            route_id = trip_routes[trip_id]
            
            # Find the station (might be parent of this stop)
            if stop_id in stations:
                stations[stop_id]['routes'].add(route_id)
    
    # Convert sets to lists and sort
    for stop_id in stations:
        stations[stop_id]['routes'] = sorted(list(stations[stop_id]['routes']))
    
    return stations


def simplify_route_names(stations, routes):
    """Simplify route IDs to match WMATA line codes"""
    # WMATA uses route IDs like "RED", "ORANGE", "BLUE", etc.
    # Map them to standard abbreviations
    route_mapping = {
        'RED': 'RD',
        'ORANGE': 'OR',
        'SILVER': 'SV',
        'BLUE': 'BL',
        'YELLOW': 'YL',
        'GREEN': 'GR'
    }
    
    for stop_id in stations:
        simplified_routes = []
        for route in stations[stop_id].get('routes', []):
            route_upper = route.upper()
            # Direct mapping
            if route_upper in route_mapping:
                simplified_routes.append(route_mapping[route_upper])
            else:
                # Try partial match
                mapped = False
                for full_name, code in route_mapping.items():
                    if full_name in route_upper:
                        simplified_routes.append(code)
                        mapped = True
                        break
                if not mapped:
                    # Keep original if no match
                    simplified_routes.append(route)
        
        stations[stop_id]['routes'] = list(set(simplified_routes))
    
    return stations


def group_by_station_name(stations):
    """Group stops by station name and keep parent stations"""
    # Group by name
    name_groups = defaultdict(list)
    
    for stop_id, data in stations.items():
        name_key = data['name'].lower().strip()
        name_groups[name_key].append((stop_id, data))
    
    # For each group, prefer station (location_type=1) over platforms
    merged_stations = {}
    
    for name, stop_list in name_groups.items():
        # Sort: prefer location_type=1 (stations), then shorter IDs
        stop_list.sort(key=lambda x: (
            0 if x[1].get('location_type') == '1' else 1,
            len(x[0]),
            x[0]
        ))
        
        main_stop_id, main_data = stop_list[0]
        
        # Merge routes from all variants
        all_routes = set(main_data.get('routes', []))
        for stop_id, data in stop_list[1:]:
            all_routes.update(data.get('routes', []))
        
        main_data['routes'] = sorted(list(all_routes))
        
        # Remove internal fields
        if 'location_type' in main_data:
            del main_data['location_type']
        
        # Convert sets to lists if any remain
        for key, value in main_data.items():
            if isinstance(value, set):
                main_data[key] = sorted(list(value))
        
        merged_stations[main_stop_id] = main_data
    
    return merged_stations


def main():
    try:
        # Get API key
        api_key = get_api_key()
        print(f"Using API key: {api_key[:10]}...")
        
        # Download and parse GTFS data
        stops_data, routes_data, stop_times_data, trips_data = download_and_extract_gtfs(api_key)
        
        print("\nParsing stops...")
        stations = parse_stops(stops_data)
        print(f"Found {len(stations)} stops/stations")
        
        print("Parsing routes...")
        routes = parse_routes(routes_data)
        print(f"Found {len(routes)} routes")
        
        if trips_data and stop_times_data:
            print("Mapping routes to stations (this may take a moment)...")
            stations = add_routes_to_stations(stations, routes, trips_data, stop_times_data)
        
        print("Simplifying route names...")
        stations = simplify_route_names(stations, routes)
        
        print("Grouping stations...")
        stations = group_by_station_name(stations)
        print(f"Final station count: {len(stations)}")
        
        # Output JSON
        output_file = 'stations.json'
        with open(output_file, 'w') as f:
            json.dump(stations, f, indent=2, sort_keys=True)
        
        print(f"\n✓ Successfully created {output_file}")
        print(f"  Total stations: {len(stations)}")
        
        # Count stations by route
        route_counts = defaultdict(int)
        for station in stations.values():
            for route in station.get('routes', []):
                route_counts[route] += 1
        
        if route_counts:
            print(f"\n  Stations by route:")
            for route in sorted(route_counts.keys()):
                print(f"    {route}: {route_counts[route]} stations")
        
        # Print sample
        print("\n  Sample stations:")
        for i, (stop_id, data) in enumerate(list(stations.items())[:5]):
            routes_str = ', '.join(data.get('routes', [])) or 'none'
            print(f"    {stop_id}: {data['name']} [{routes_str}]")
        
        print(f"\n✓ Done! Use this file with your WMATA API server.")
        
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
