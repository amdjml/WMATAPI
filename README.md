# WMATA API

A real-time API for Washington Metro (WMATA) train data

## Features

- 🚇 **Real-time train arrivals** - Get live arrival times for any station
- 🗺️ **Location-based search** - Find nearby stations by lat/lon
- 🎯 **Route filtering** - Filter trains by specific metro lines
- ⚡ **Smart caching** - Configurable cache to reduce API calls
- 🔌 **WebSocket support** - Real-time updates pushed to clients
- 🌐 **RESTful API** - Clean JSON endpoints
- 🔄 **Automatic platform mapping** - Consolidates platform-level data into stations

## Quick Start

### 1. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Get WMATA API Key

Sign up for a free API key at: https://developer.wmata.com/

### 3. Generate Stations File

```bash
# Set your API key
export WMATA_API_KEY=your_api_key_here

# Generate stations.json from WMATA GTFS data
python make_stations_json.py
```

This will download WMATA's GTFS static feed and create a complete `stations.json` file with all metro stations, their locations, and routes.

### 4. Configure

```bash
cp settings.cfg.sample settings.cfg
# Edit settings.cfg and add your WMATA API key
```

### 5. Run

```bash
python app.py
```

The server will start on `http://localhost:5000`

You should see:
```
INFO - Built platform mapping with 300+ entries
INFO - Fetching data from WMATA API...
INFO - Processed arrivals for 90+ stations
INFO - Background updater started
 * Running on http://0.0.0.0:5000
```

## API Endpoints

### GET `/`
Web interface with API documentation and server status.

**Example:**
```bash
curl http://localhost:5000/
```

---

### GET `/by-id/:stop_id`
Get train arrivals for a specific station.

**Parameters:**
- `stop_id` - Station ID (accepts multiple formats: `STN_A01_C01`, `A01`, or `PF_A01_1`)

**Example:**
```bash
curl http://localhost:5000/by-id/STN_A01_C01
curl http://localhost:5000/by-id/A01
```

**Response:**
```json
{
  "id": "STN_A01_C01",
  "name": "METRO CENTER METRORAIL STATION",
  "N": [
    {
      "route": "RED",
      "time": "2025-10-17T15:30:00",
      "minutes": 5.2
    }
  ],
  "S": [
    {
      "route": "RED",
      "time": "2025-10-17T15:32:00",
      "minutes": 7.1
    }
  ],
  "location": [38.898303, -77.028099],
  "updated": "2025-10-17T15:28:00"
}
```

---

### GET `/by-location?lat=:lat&lon=:lon&radius=:radius`
Get stations near a location.

**Parameters:**
- `lat` - Latitude (required)
- `lon` - Longitude (required)
- `radius` - Search radius in kilometers (optional, default: 0.5)

**Example:**
```bash
# Stations near Union Station
curl "http://localhost:5000/by-location?lat=38.8977&lon=-77.0063&radius=1"
```

**Response:**
```json
{
  "data": [
    {
      "id": "STN_A01_C01",
      "name": "METRO CENTER METRORAIL STATION",
      "location": [38.898303, -77.028099],
      "distance": 0.32,
      "N": [...],
      "S": [...]
    }
  ],
  "updated": "2025-10-17T15:28:00"
}
```

---

### GET `/by-route/:route`
Get all stations with arrivals for a specific route.

**Parameters:**
- `route` - Route ID (RED, ORANGE, SILVER, BLUE, YELLOW, GREEN)

**Example:**
```bash
curl http://localhost:5000/by-route/RED
```

**Response:**
```json
{
  "route": "RED",
  "data": [
    {
      "id": "STN_A01_C01",
      "name": "METRO CENTER METRORAIL STATION",
      "N": [...],
      "S": [...]
    }
  ],
  "updated": "2025-10-17T15:28:00"
}
```

---

### GET `/routes`
Get list of all currently active routes.

**Example:**
```bash
curl http://localhost:5000/routes
```

**Response:**
```json
{
  "routes": ["BLUE", "GREEN", "ORANGE", "RED", "SILVER", "YELLOW"],
  "updated": "2025-10-17T15:28:00"
}
```

---

### GET `/stations`
Get list of all stations and their current train counts.

**Example:**
```bash
curl http://localhost:5000/stations
```

**Response:**
```json
{
  "stations_with_trains": [
    {
      "id": "STN_A01_C01",
      "name": "METRO CENTER METRORAIL STATION",
      "trains": 12
    }
  ],
  "total_stations_configured": 98,
  "total_stations_with_trains": 90,
  "updated": "2025-10-17T15:28:00"
}
```

---

### GET `/debug`
Debug endpoint showing server state and data availability.

**Example:**
```bash
curl http://localhost:5000/debug
```

---

### WebSocket `/ws`
Real-time updates via WebSocket. Automatically broadcasts updates when new data is fetched.

**JavaScript Example:**
```javascript
const ws = new WebSocket('ws://localhost:5000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Received update for ${data.data.length} stations`);
  
  // Process station data
  data.data.forEach(station => {
    console.log(`${station.name}: ${station.N.length + station.S.length} trains`);
  });
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

**Python Example:**
```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    print(f"Received update: {len(data['data'])} stations")
    
    for station in data['data']:
        train_count = len(station.get('N', [])) + len(station.get('S', []))
        if train_count > 0:
            print(f"  {station['name']}: {train_count} trains")

ws = websocket.WebSocketApp(
    "ws://localhost:5000/ws",
    on_message=on_message
)
ws.run_forever()
```

## Configuration

Edit `settings.cfg`:

| Setting | Description | Default |
|---------|-------------|---------|
| `WMATA_API_KEY` | Your API key from WMATA (required) | None |
| `STATIONS_FILE` | Path to stations.json file | `stations.json` |
| `CACHE_SECONDS` | How often to fetch new data from WMATA | 60 |
| `MAX_TRAINS` | Max trains to show per station | 10 |
| `MAX_MINUTES` | Only show trains within X minutes | 30 |
| `THREADED` | Enable background updates | True |
| `DEBUG` | Enable debug mode | False |
| `CROSS_ORIGIN` | CORS header | `*` in debug |

## Station ID Formats

WMATA uses multiple ID formats. This API automatically handles all of them:

- **Parent Station IDs**: `STN_A01_C01`, `STN_A02` (from stations.json)
- **Station Codes**: `A01`, `B02`, `C01` (short format)
- **Platform IDs**: `PF_A01_1`, `PF_A01_2`, `PF_A01_C` (from real-time feed)

The server automatically maps all platform-level data to their parent stations.

## WMATA Route IDs

- **RED** - Red Line
- **ORANGE** - Orange Line
- **SILVER** - Silver Line
- **BLUE** - Blue Line
- **YELLOW** - Yellow Line
- **GREEN** - Green Line

## Generating Stations File

The `make_stations_json.py` script downloads WMATA's GTFS static data and creates a complete stations file:

```bash
# Set API key
export WMATA_API_KEY=your_key_here

# Run script
python make_stations_json.py
```

**What it does:**
1. Downloads WMATA's rail GTFS static feed
2. Parses stops.txt for station locations
3. Maps routes to stations via stop_times.txt and trips.txt
4. Groups platforms into parent stations
5. Outputs clean stations.json

**Output:**
```
Downloading WMATA Rail GTFS data...
Extracting files...
Parsing stops...
Found 98 parent stations
Found 200 platform->station mappings
Mapping routes to stations...
  Processed 50000 stop times
Final station count: 98
✓ Successfully created stations.json
```

## Production Deployment

### Using Gunicorn (Recommended)

```bash
pip install gunicorn eventlet

# Run with eventlet worker for WebSocket support
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
```

### Using uWSGI

```bash
uwsgi --http :5000 --wsgi-file app.py --callable app --enable-threads
```

**Note:** uWSGI may have issues with WebSockets. Gunicorn with eventlet is recommended.

### Using systemd

```bash
# Copy service file
sudo cp wmata-api.service /etc/systemd/system/

# Edit service file to set your API key and paths
sudo nano /etc/systemd/system/wmata-api.service

# Enable and start
sudo systemctl enable wmata-api
sudo systemctl start wmata-api

# Check status
sudo systemctl status wmata-api

# View logs
sudo journalctl -u wmata-api -f
```

### Using Docker

Build and run with Docker:

```bash
# Build image
docker build -t wmata-api .

# Run container
docker run -d -p 5000:5000 \
  -e WMATA_API_KEY=your_key_here \
  --name wmata-api \
  wmata-api

# Or use docker-compose
docker-compose up -d
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  wmata-api:
    build: .
    ports:
      - "5000:5000"
    environment:
      - WMATA_API_KEY=${WMATA_API_KEY}
    volumes:
      - ./stations.json:/app/stations.json
      - ./settings.cfg:/app/settings.cfg
    restart: unless-stopped
```

### Environment Variables

Set `MTAPI_SETTINGS` to use a different config file:

```bash
export MTAPI_SETTINGS=/path/to/production.cfg
python app.py
```

## Testing

Test the API with the included test client:

```bash
# Install test dependencies
pip install websocket-client

# Test REST endpoints
python test_client.py rest

# Test WebSocket
python test_client.py websocket

# Test concurrent requests
python test_client.py concurrent

# Run all tests
python test_client.py all
```

**Example output:**
```
============================================================
Testing REST API Endpoints
============================================================

1. Getting all routes...
   Found 6 routes: ['BLUE', 'GREEN', 'ORANGE', 'RED', 'SILVER', 'YELLOW']

2. Getting station STN_A01_C01 (Metro Center)...
   Station: METRO CENTER METRORAIL STATION
   Northbound trains: 6
   Southbound trains: 6
   Next northbound: {'route': 'RED', 'time': '2025-10-17T15:30:00', 'minutes': 5.2}
```

## How It Works

1. **Data Fetching**: 
   - Pulls GTFS-RT feeds from WMATA every 60 seconds (configurable)
   - Uses both Trip Updates (arrivals) and Vehicle Positions (train locations)

2. **Processing**: 
   - Converts Protocol Buffers to JSON
   - Maps platform IDs to parent stations
   - Organizes arrivals by station and direction
   - Filters trains beyond MAX_MINUTES threshold

3. **Caching**: 
   - Stores processed data in memory
   - Serves requests from cache for better performance
   - Reduces API calls to WMATA

4. **Broadcasting**: 
   - Pushes updates to all WebSocket clients when new data arrives
   - No polling required from clients

## Troubleshooting

### "Station not found" error

Check available station IDs:
```bash
curl http://localhost:5000/stations
curl http://localhost:5000/debug
```

### No trains showing

- Check if trains are currently running (metro hours of operation)
- Verify your WMATA API key is valid
- Check server logs for errors
- Increase `MAX_MINUTES` in settings.cfg

### Platform IDs not mapping

The server automatically builds platform mappings on startup. Check logs:
```
INFO - Built platform mapping with 300+ entries
```

If you see issues, regenerate stations.json:
```bash
python make_stations_json.py
```

## Differences from MTAPI (NYC)

- Uses WMATA's GTFS-RT feeds instead of MTA
- Different station ID format (WMATA uses alphanumeric codes with STN_ prefix)
- Automatic platform-to-station mapping (WMATA has complex station/platform hierarchy)
- Simplified direction logic (N/S instead of complex NYC routing)
- Route filtering by WMATA line codes (RED, ORANGE, etc.)

## API Rate Limits

WMATA API has rate limits:
- **Standard Tier**: 10 requests per second, 50,000 per day
- The server caches data (default 60 seconds) to stay well within limits
- WebSocket clients don't count toward rate limits (they receive cached updates)

## Contributing

Issues and pull requests welcome! This project is under active development.

### Development Setup

```bash
# Clone repo
git clone https://github.com/yourusername/wmata-api.git
cd wmata-api

# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp settings.cfg.sample settings.cfg
# Edit settings.cfg with your API key

# Generate stations
python make_stations_json.py

# Run in debug mode
python app.py
```

## License

MIT License

## Credits

Inspired by [MTAPI](https://github.com/jonthornton/MTAPI) by Jon Thornton and the [fork with WebSocket support](https://github.com/rpsmith77/MTAPI) by rpsmith77.

## Resources

- [WMATA Developer Portal](https://developer.wmata.com/)
- [GTFS Realtime Reference](https://developers.google.com/transit/gtfs-realtime)
- [WMATA System Map](https://www.wmata.com/rider-guide/new-riders/upload/2023-System-Map.pdf)
