# WMATA API

A real-time API for Washington Metro (WMATA) train data

## Features

- 🚇 **Real-time train arrivals** - Get live arrival times for any station
- 🗺️ **Location-based search** - Find nearby stations by lat/lon
- 🎯 **Route filtering** - Filter trains by specific metro lines
- ⚡ **Smart caching** - Configurable cache to reduce API calls
- 🔌 **WebSocket support** - Real-time updates pushed to clients
- 🌐 **RESTful API** - Clean JSON endpoints

## Quick Start

### 1. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp settings.cfg.sample settings.cfg
# Edit settings.cfg and add your WMATA API key
```

Get your API key from: https://developer.wmata.com/

### 3. Run

```bash
python app.py
```

The server will start on `http://localhost:5000`

## API Endpoints

### GET `/by-id/:stop_id`
Get train arrivals for a specific station.

**Example:**
```bash
curl http://localhost:5000/by-id/A01
```

**Response:**
```json
{
  "id": "A01",
  "name": "Metro Center",
  "N": [
    {"route": "RD", "time": "2025-10-17T15:30:00"}
  ],
  "S": [
    {"route": "RD", "time": "2025-10-17T15:32:00"}
  ],
  "location": [38.898303, -77.028099],
  "updated": "2025-10-17T15:28:00"
}
```

### GET `/by-location?lat=:lat&lon=:lon&radius=:radius`
Get stations near a location (radius in km, default 0.5).

**Example:**
```bash
curl "http://localhost:5000/by-location?lat=38.898&lon=-77.028&radius=1"
```

### GET `/by-route/:route`
Get all stations with arrivals for a specific route.

**Example:**
```bash
curl http://localhost:5000/by-route/RD
```

### GET `/routes`
Get list of all currently active routes.

**Example:**
```bash
curl http://localhost:5000/routes
```

### WebSocket `/ws`
Real-time updates via WebSocket.

**JavaScript Example:**
```javascript
const ws = new WebSocket('ws://localhost:5000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Updated stations:', data);
};
```

**Python Example:**
```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    print(f"Received update: {len(data['data'])} stations")

ws = websocket.WebSocketApp("ws://localhost:5000/ws",
                           on_message=on_message)
ws.run_forever()
```

## Configuration

Edit `settings.cfg`:

- **WMATA_API_KEY** - Your API key from WMATA (required)
- **STATIONS_FILE** - Path to stations.json file
- **CACHE_SECONDS** - How often to fetch new data (default: 60)
- **MAX_TRAINS** - Max trains to show per station (default: 10)
- **MAX_MINUTES** - Only show trains within X minutes (default: 30)
- **THREADED** - Enable background updates (default: True)
- **DEBUG** - Enable debug mode (default: False)
- **CROSS_ORIGIN** - CORS header (default: '*' in debug)

## Station Data

The `stations.json` file contains station metadata. You can:

1. Use the sample provided
2. Create your own from WMATA's GTFS static data
3. Download from WMATA's [Developer Portal](https://developer.wmata.com/)

### WMATA Route IDs

- **RD** - Red Line
- **OR** - Orange Line
- **SV** - Silver Line
- **BL** - Blue Line
- **YL** - Yellow Line
- **GR** - Green Line

## Production Deployment

### Using uWSGI

```bash
uwsgi --http :5000 --wsgi-file app.py --callable app --enable-threads
```

### Using Gunicorn (with eventlet for WebSocket support)

```bash
pip install gunicorn eventlet
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
```

### Environment Variables

Set `MTAPI_SETTINGS` to use a different config file:

```bash
export MTAPI_SETTINGS=/path/to/production.cfg
python app.py
```

## How It Works

1. **Data Fetching**: Pulls GTFS-RT feeds from WMATA every 60 seconds (configurable)
2. **Processing**: Converts Protocol Buffers to JSON, organizes by station
3. **Caching**: Stores processed data in memory to serve requests quickly
4. **Broadcasting**: Pushes updates to all WebSocket clients when new data arrives

## Differences from MTAPI

- Uses WMATA's GTFS-RT feeds instead of MTA
- Different station ID format (WMATA uses alphanumeric codes)
- Simplified direction logic (N/S instead of complex NYC routing)
- Added route filtering by WMATA line codes

## Contributing

Issues and pull requests welcome! This project is under active development.

## License

MIT License

## Credits

Inspired by [MTAPI](https://github.com/jonthornton/MTAPI) by Jon Thornton
