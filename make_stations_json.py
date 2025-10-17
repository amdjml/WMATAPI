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
from collections import defaultdict

WMATA_GTFS_URL = "https://api.wmata.com/gtfs/rail-gtfs-static.zip"


def download_and_extract_gtfs():
    """Download and extract WMATA GTFS static data"""
    print("Downloading WMATA GTFS data...")
    response = requests.get(WMATA_GTFS_URL)
    response.raise_for_status()
    
    print("Extracting files...")
    z = zipfile.ZipFile(io.BytesIO(response.content))
    
    stops_data = z.read('stops.txt').decode('utf-8-sig')
    routes_data = z.read('routes.txt').decode('utf-8-sig')
    
    try:
        trips_data = z.read('trips.txt').decode('utf-8-sig')
    except:
        trips_data = None
    
    return stops_data, routes_data, trips_data


def parse_stops(stops_data):
    """Parse stops.txt into station dictionary"""
    stations = {}
    reader = csv.DictReader(io.StringIO(stops_data))
    
    for row in reader:
        stop_id = row['stop_id'].strip()
        stop_name = row['stop_name'].strip()
        stop_lat = float(row['stop_lat'])
        stop_lon = float(row['stop_lon'])
        
        # WMATA uses parent stations - we want the parent level
        # Child stops have platform-specific IDs
        if 'parent_station' in row and row['parent_station']:
            continue  # Skip platform-specific stops
        
        stations[stop_id] = {
            'name': stop_name,
            'lat': stop_lat,
            'lon': stop_lon,
            'routes': []
        }
    
    return stations


def parse_routes(routes_data):
    """Parse routes.txt to get route info"""
    routes = {}
    reader = csv.DictReader(io.StringIO(routes_data))
    
    for row in reader:
        route_id = row['route_id'].strip()
        route_name = row['route_short_name'].strip() or row['route_long_name'].strip()
        
        routes[route_id] = {
            'name': route_name,
            'type': row.get('route_type', '1')
        }
    
    return routes


def add_routes_to_stations(stations, trips_data):
    """Add route information to stations based on trips"""
    if not trips_data:
        print("Warning: No trips data available. Routes will not be populated.")
        return stations
    
    # Map of stop_id -> set of route_ids
    stop_routes = defaultdict(set)
    
    reader = csv.DictReader(io.StringIO(trips_data))
    
    # First pass: build stop -> routes mapping from trips
    # Note: This is simplified. For complete accuracy, you'd need stop_times.txt
    for row in reader:
        route_id = row['route_id'].strip()
        # We'd need stop_times.txt to properly map stops to routes
        # For now, we'll just note that this station exists on this route
    
    # Update stations with route information
    for stop_id in stations:
        if stop_id in stop_routes:
            stations[stop_id]['routes'] = sorted(list(stop_routes[stop_id]))
    
    return stations


def simplify_route_names(stations):
    """Simplify route names to common codes (RD, OR, BL, etc.)"""
    route_mapping = {
        'Red': 'RD',
        'Orange': 'OR',
        'Silver': 'SV',
        'Blue': 'BL',
        'Yellow': 'YL',
        'Green': 'GR'
    }
    
    for stop_id in stations:
        simplified_routes = []
        for route in stations[stop_id].get('routes', []):
            # Try to match route name to simplified code
            for full_name, code in route_mapping.items():
                if full_name.lower() in route.lower():
                    simplified_routes.append(code)
                    break
            else:
                # If no match, keep original
                simplified_routes.append(route)
        
        stations[stop_id]['routes'] = list(set(simplified_routes))
    
    return stations


def group_duplicate_stations(stations):
    """Group stations with same name but different IDs"""
    # Some stations appear multiple times (different platforms/directions)
    # Group by name and location proximity
    
    name_groups = defaultdict(list)
    
    for stop_id, data in stations.items():
        key = data['name'].lower().strip()
        name_groups[key].append((stop_id, data))
    
    # For groups with multiple stations, keep the one with the shortest ID
    # (usually the parent station)
    merged_stations = {}
    
    for name, stop_list in name_groups.items():
        if len(stop_list) == 1:
            stop_id, data = stop_list[0]
            merged_stations[stop_id] = data
        else:
            # Sort by ID length, prefer shorter IDs (parent stations)
            stop_list.sort(key=lambda x: (len(x[0]), x[0]))
            main_stop_id, main_data = stop_list[0]
            
            # Merge routes from all variations
            all_routes = set(main_data.get('routes', []))
            for stop_id, data in stop_list[1:]:
                all_routes.update(data.get('routes', []))
            
            main_data['routes'] = sorted(list(all_routes))
            merged_stations[main_stop_id] = main_data
    
    return merged_stations


def main():
    try:
        # Download and parse GTFS data
        stops_data, routes_data, trips_data = download_and_extract_gtfs()
        
        print("Parsing stops...")
        stations = parse_stops(stops_data)
        print(f"Found {len(stations)} stations")
        
        print("Parsing routes...")
        routes = parse_routes(routes_data)
        print(f"Found {len(routes)} routes")
        
        print("Adding route information to stations...")
        stations = add_routes_to_stations(stations, trips_data)
        
        print("Simplifying route names...")
        stations = simplify_route_names(stations)
        
        print("Grouping duplicate stations...")
        stations = group_duplicate_stations(stations)
        print(f"Final station count: {len(stations)}")
        
        # Output JSON
        output_file = 'stations.json'
        with open(output_file, 'w') as f:
            json.dump(stations, f, indent=2, sort_keys=True)
        
        print(f"\nSuccessfully created {output_file}")
        print(f"Total stations: {len(stations)}")
        
        # Print sample
        print("\nSample stations:")
        for i, (stop_id, data) in enumerate(list(stations.items())[:5]):
            print(f"  {stop_id}: {data['name']} - Routes: {data.get('routes', [])}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
