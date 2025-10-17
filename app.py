"""
WMATA API - Real-time train data API for Washington Metro
"""

from flask import Flask, request, jsonify, render_template_string
from flask_sock import Sock
import requests
import threading
import time
import json
from datetime import datetime, timedelta
from google.transit import gtfs_realtime_pb2
from math import radians, cos, sin, asin, sqrt
import logging

app = Flask(__name__)
sock = Sock(app)

# Configuration
app.config.from_pyfile('settings.cfg', silent=True)

WMATA_API_KEY = app.config.get('WMATA_API_KEY', '')
STATIONS_FILE = app.config.get('STATIONS_FILE', 'stations.json')
CACHE_SECONDS = app.config.get('CACHE_SECONDS', 60)
MAX_TRAINS = app.config.get('MAX_TRAINS', 10)
MAX_MINUTES = app.config.get('MAX_MINUTES', 30)
THREADED = app.config.get('THREADED', True)
DEBUG = app.config.get('DEBUG', False)
CROSS_ORIGIN = app.config.get('CROSS_ORIGIN', '*' if DEBUG else None)

# WMATA GTFS-RT URLs
VEHICLE_POSITIONS_URL = 'https://api.wmata.com/gtfs/rail-gtfsrt-vehiclepositions.pb'
TRIP_UPDATES_URL = 'https://api.wmata.com/gtfs/rail-gtfsrt-tripupdates.pb'
ALERTS_URL = 'https://api.wmata.com/gtfs/rail-gtfsrt-alerts.pb'

# Global data store
_data_cache = {
    'stations': {},
    'last_update': None,
    'vehicles': [],
    'trip_updates': []
}

# WebSocket clients
_ws_clients = []
_ws_lock = threading.Lock()

# Load stations
try:
    with open(STATIONS_FILE, 'r') as f:
        _stations = json.load(f)
except FileNotFoundError:
    _stations = {}
    logging.warning(f"Stations file {STATIONS_FILE} not found. Using empty stations.")


def haversine(lon1, lat1, lon2, lat2):
    """Calculate distance between two points in km"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km


def fetch_gtfs_data(url):
    """Fetch and parse GTFS-RT data from WMATA"""
    headers = {'api_key': WMATA_API_KEY}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)
    return feed


def process_trip_updates(feed):
    """Process trip updates into station arrival times"""
    station_data = {}
    
    logging.info(f"Processing {len(feed.entity)} trip update entities...")
    
    for entity in feed.entity:
        if not entity.HasField('trip_update'):
            continue
            
        trip = entity.trip_update.trip
        route_id = trip.route_id if trip.HasField('route_id') else 'UNKNOWN'
        
        for stop_update in entity.trip_update.stop_time_update:
            stop_id = stop_update.stop_id if stop_update.HasField('stop_id') else None
            
            if not stop_id:
                continue
            
            # Get arrival or departure time
            if stop_update.HasField('arrival') and stop_update.arrival.HasField('time'):
                arrival_time = stop_update.arrival.time
            elif stop_update.HasField('departure') and stop_update.departure.HasField('time'):
                arrival_time = stop_update.departure.time
            else:
                continue
            
            # Convert to datetime
            arrival_dt = datetime.fromtimestamp(arrival_time)
            
            # Check if within MAX_MINUTES
            now = datetime.now()
            minutes_away = (arrival_dt - now).total_seconds() / 60
            
            if minutes_away > MAX_MINUTES or minutes_away < -5:  # Skip trains that left >5 min ago
                continue
            
            # Initialize station data
            if stop_id not in station_data:
                station_data[stop_id] = {
                    'N': [],  # Northbound
                    'S': []   # Southbound
                }
            
            # Determine direction
            direction = 'N' if (trip.HasField('direction_id') and trip.direction_id == 0) else 'S'
            
            train_info = {
                'route': route_id,
                'time': arrival_dt.isoformat(),
                'minutes': round(minutes_away, 1)
            }
            
            station_data[stop_id][direction].append(train_info)
    
    # Sort and limit trains per station
    for stop_id in station_data:
        for direction in ['N', 'S']:
            station_data[stop_id][direction].sort(key=lambda x: x['time'])
            station_data[stop_id][direction] = station_data[stop_id][direction][:MAX_TRAINS]
    
    logging.info(f"Processed arrivals for {len(station_data)} stops")
    
    return station_data


def update_data():
    """Fetch fresh data from WMATA API"""
    try:
        logging.info("Fetching data from WMATA API...")
        
        # Fetch trip updates (arrivals)
        trip_feed = fetch_gtfs_data(TRIP_UPDATES_URL)
        station_data = process_trip_updates(trip_feed)
        
        # Fetch vehicle positions
        vehicle_feed = fetch_gtfs_data(VEHICLE_POSITIONS_URL)
        vehicles = []
        for entity in vehicle_feed.entity:
            if entity.HasField('vehicle'):
                v = entity.vehicle
                vehicles.append({
                    'id': entity.id,
                    'route': v.trip.route_id if v.HasField('trip') else None,
                    'lat': v.position.latitude if v.HasField('position') else None,
                    'lon': v.position.longitude if v.HasField('position') else None,
                    'stop_id': v.stop_id if v.HasField('stop_id') else None,
                    'status': v.current_status if v.HasField('current_status') else None
                })
        
        # Update cache
        _data_cache['stations'] = station_data
        _data_cache['vehicles'] = vehicles
        _data_cache['last_update'] = datetime.now().isoformat()
        
        logging.info(f"Data updated. {len(station_data)} stations with arrivals.")
        
        # Broadcast to WebSocket clients
        broadcast_to_websockets()
        
    except Exception as e:
        logging.error(f"Error updating data: {e}")


def broadcast_to_websockets():
    """Send updated data to all connected WebSocket clients"""
    with _ws_lock:
        data = get_all_stations_data()
        message = json.dumps(data)
        
        dead_clients = []
        for client in _ws_clients:
            try:
                client.send(message)
            except:
                dead_clients.append(client)
        
        # Remove dead connections
        for client in dead_clients:
            _ws_clients.remove(client)


def background_updater():
    """Background thread to update data periodically"""
    while True:
        update_data()
        time.sleep(CACHE_SECONDS)


def get_all_stations_data():
    """Get formatted data for all stations"""
    stations_with_trains = []
    
    for stop_id, arrivals in _data_cache['stations'].items():
        station_info = _stations.get(stop_id, {})
        
        station_data = {
            'id': stop_id,
            'name': station_info.get('name', stop_id),
            'N': arrivals.get('N', []),
            'S': arrivals.get('S', [])
        }
        
        # Add location if available
        if 'lat' in station_info and 'lon' in station_info:
            station_data['location'] = [station_info['lat'], station_info['lon']]
        
        stations_with_trains.append(station_data)
    
    return {
        'data': stations_with_trains,
        'updated': _data_cache['last_update']
    }


@app.route('/')
def index():
    """API documentation"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WMATA API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            h1 { color: #333; }
            code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
            .endpoint { background: #f9f9f9; padding: 15px; margin: 10px 0; border-left: 4px solid #007bff; }
        </style>
    </head>
    <body>
        <h1>WMATA API</h1>
        <p>Real-time train data for Washington Metro</p>
        
        <h2>Endpoints</h2>
        
        <div class="endpoint">
            <h3>GET /by-id/:stop_id</h3>
            <p>Get train arrivals for a specific station</p>
            <code>curl http://localhost:5000/by-id/A01</code>
        </div>
        
        <div class="endpoint">
            <h3>GET /by-location?lat=:lat&lon=:lon</h3>
            <p>Get stations near a location (within 0.5km by default)</p>
            <code>curl http://localhost:5000/by-location?lat=38.8977&lon=-77.0063</code>
        </div>
        
        <div class="endpoint">
            <h3>GET /by-route/:route</h3>
            <p>Get all stations served by a specific route</p>
            <code>curl http://localhost:5000/by-route/RD</code>
        </div>
        
        <div class="endpoint">
            <h3>GET /stations</h3>
            <p>Get list of all stations and their current train counts</p>
            <code>curl http://localhost:5000/stations</code>
        </div>
        
        <div class="endpoint">
            <h3>GET /debug</h3>
            <p>Debug info about cached data</p>
            <code>curl http://localhost:5000/debug</code>
        </div>
        
        <div class="endpoint">
            <h3>WS /ws</h3>
            <p>WebSocket endpoint for real-time updates</p>
            <code>ws://localhost:5000/ws</code>
        </div>
        
        <h2>Status</h2>
        <p>Last Update: {{ last_update }}</p>
        <p>Stations with Trains: {{ station_count }}</p>
        <p>Active Vehicles: {{ vehicle_count }}</p>
    </body>
    </html>
    """
    return render_template_string(
        html,
        last_update=_data_cache['last_update'],
        station_count=len(_data_cache['stations']),
        vehicle_count=len(_data_cache['vehicles'])
    )


@app.route('/by-id/<stop_id>')
def by_id(stop_id):
    """Get train arrivals for a specific station"""
    
    # Check if this stop_id exists in our stations file
    station_info = _stations.get(stop_id, {})
    
    # Check if we have real-time data for this stop
    arrivals = _data_cache['stations'].get(stop_id, {'N': [], 'S': []})
    
    # If no station info and no arrivals, it's truly not found
    if not station_info and not arrivals.get('N') and not arrivals.get('S'):
        # Log available stations for debugging
        logging.warning(f"Station {stop_id} not found. Available stations: {len(_stations)}, "
                       f"Stations with arrivals: {len(_data_cache['stations'])}")
        if len(_data_cache['stations']) > 0:
            sample_ids = list(_data_cache['stations'].keys())[:5]
            logging.warning(f"Sample stop IDs with arrivals: {sample_ids}")
        return jsonify({'error': 'Station not found', 
                       'hint': 'Check /routes endpoint or logs for available station IDs'}), 404
    
    response = {
        'id': stop_id,
        'name': station_info.get('name', stop_id),
        'N': arrivals.get('N', []),
        'S': arrivals.get('S', []),
        'updated': _data_cache['last_update']
    }
    
    if 'lat' in station_info and 'lon' in station_info:
        response['location'] = [station_info['lat'], station_info['lon']]
    
    return jsonify(response)


@app.route('/by-location')
def by_location():
    """Get stations near a location"""
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        radius = float(request.args.get('radius', 0.5))  # km
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid lat/lon parameters'}), 400
    
    nearby_stations = []
    
    for stop_id in _data_cache['stations']:
        station_info = _stations.get(stop_id, {})
        if 'lat' not in station_info or 'lon' not in station_info:
            continue
        
        distance = haversine(lon, lat, station_info['lon'], station_info['lat'])
        
        if distance <= radius:
            arrivals = _data_cache['stations'][stop_id]
            nearby_stations.append({
                'id': stop_id,
                'name': station_info.get('name', stop_id),
                'location': [station_info['lat'], station_info['lon']],
                'distance': round(distance, 2),
                'N': arrivals.get('N', []),
                'S': arrivals.get('S', [])
            })
    
    nearby_stations.sort(key=lambda x: x['distance'])
    
    return jsonify({
        'data': nearby_stations,
        'updated': _data_cache['last_update']
    })


@app.route('/by-route/<route_id>')
def by_route(route_id):
    """Get all stations with arrivals for a specific route"""
    route_stations = []
    
    for stop_id, arrivals in _data_cache['stations'].items():
        station_info = _stations.get(stop_id, {})
        
        # Filter trains for this route
        n_trains = [t for t in arrivals.get('N', []) if t['route'] == route_id]
        s_trains = [t for t in arrivals.get('S', []) if t['route'] == route_id]
        
        if n_trains or s_trains:
            route_stations.append({
                'id': stop_id,
                'name': station_info.get('name', stop_id),
                'N': n_trains,
                'S': s_trains
            })
    
    return jsonify({
        'route': route_id,
        'data': route_stations,
        'updated': _data_cache['last_update']
    })


@app.route('/routes')
def routes():
    """Get list of all active routes"""
    route_set = set()
    
    for arrivals in _data_cache['stations'].values():
        for direction in ['N', 'S']:
            for train in arrivals.get(direction, []):
                route_set.add(train['route'])
    
    return jsonify({
        'routes': sorted(list(route_set)),
        'updated': _data_cache['last_update']
    })


@app.route('/stations')
def stations_list():
    """Get list of all stations with current data"""
    stations_with_data = []
    
    # From real-time data
    for stop_id in _data_cache['stations']:
        station_info = _stations.get(stop_id, {})
        arrivals = _data_cache['stations'][stop_id]
        train_count = len(arrivals.get('N', [])) + len(arrivals.get('S', []))
        
        stations_with_data.append({
            'id': stop_id,
            'name': station_info.get('name', stop_id),
            'trains': train_count
        })
    
    # Also show stations from config even if no current trains
    all_station_ids = set(list(_data_cache['stations'].keys()) + list(_stations.keys()))
    
    return jsonify({
        'stations_with_trains': stations_with_data,
        'total_stations_configured': len(_stations),
        'total_stations_with_trains': len(_data_cache['stations']),
        'all_station_ids': sorted(list(all_station_ids))[:20],  # First 20 for reference
        'updated': _data_cache['last_update']
    })


@app.route('/debug')
def debug():
    """Debug endpoint to see what data is available"""
    return jsonify({
        'last_update': _data_cache['last_update'],
        'stations_configured': len(_stations),
        'stations_with_arrivals': len(_data_cache['stations']),
        'sample_configured_station_ids': list(_stations.keys())[:10],
        'sample_arrival_station_ids': list(_data_cache['stations'].keys())[:10],
        'total_vehicles': len(_data_cache['vehicles']),
        'websocket_clients': len(_ws_clients)
    })


@sock.route('/ws')
def websocket(ws):
    """WebSocket endpoint for real-time updates"""
    with _ws_lock:
        _ws_clients.append(ws)
    
    logging.info(f"WebSocket client connected. Total clients: {len(_ws_clients)}")
    
    # Send initial data
    try:
        data = get_all_stations_data()
        ws.send(json.dumps(data))
    except:
        pass
    
    # Keep connection alive
    try:
        while True:
            message = ws.receive()
            if message is None:
                break
    except:
        pass
    finally:
        with _ws_lock:
            if ws in _ws_clients:
                _ws_clients.remove(ws)
        logging.info(f"WebSocket client disconnected. Total clients: {len(_ws_clients)}")


@app.after_request
def after_request(response):
    """Add CORS headers if enabled"""
    if CROSS_ORIGIN:
        response.headers['Access-Control-Allow-Origin'] = CROSS_ORIGIN
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if not WMATA_API_KEY:
        logging.error("WMATA_API_KEY not set!")
        exit(1)
    
    # Initial data load
    update_data()
    
    # Start background updater if threaded mode
    if THREADED:
        updater_thread = threading.Thread(target=background_updater, daemon=True)
        updater_thread.start()
        logging.info("Background updater started")
    
    app.run(debug=DEBUG, host='0.0.0.0', port=5000)
