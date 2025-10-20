# WMATA API - Quick Start Guide

Get up and running in 5 minutes!

## Step 1: Get API Key (2 minutes)

1. Go to https://developer.wmata.com/
2. Sign up for a free account
3. Create an API key
4. Copy your API key

## Step 2: Setup (2 minutes)

### Option A: Automatic (Linux/Mac)
```bash
chmod +x run.sh
./run.sh
```

### Option B: Automatic (Windows)
```bash
run.bat
```

### Option C: Manual
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set API key
export WMATA_API_KEY=your_api_key_here  # Windows: set WMATA_API_KEY=your_api_key_here

# Generate stations file
python make_stations_json.py

# Configure
cp settings.cfg.sample settings.cfg
# Edit settings.cfg and add your API key

# Check setup
python check_setup.py

# Run server
python app.py
```

## Step 3: Test (1 minute)

Open your browser to: http://localhost:5000

Or test with curl:
```bash
# Get all routes
curl http://localhost:5000/routes

# Get all stations
curl http://localhost:5000/stations

# Get specific station (Metro Center)
curl http://localhost:5000/by-id/STN_A01_C01
curl http://localhost:5000/by-id/A01

# Stations near Union Station
curl "http://localhost:5000/by-location?lat=38.8977&lon=-77.0063&radius=1"

# Red Line stations
curl http://localhost:5000/by-route/RED
```

## Step 4: WebSocket Test

```bash
python test_client.py websocket
```

Or with JavaScript:
```javascript
const ws = new WebSocket('ws://localhost:5000/ws');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

## Troubleshooting

### "Station not found"
Check available stations:
```bash
curl http://localhost:5000/stations
curl http://localhost:5000/debug
```

### "API key not found"
Make sure you:
1. Set environment variable: `export WMATA_API_KEY=your_key`
2. OR edit `settings.cfg` with your key

### "stations.json not found"
Generate it:
```bash
python make_stations_json.py
```

### Port 5000 already in use
Kill the process:
```bash
# Linux/Mac
lsof -ti:5000 | xargs kill -9

# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Dependencies not installed
```bash
pip install -r requirements.txt
```

### Check everything
```bash
python check_setup.py
```

## What's Next?

- Read the full [README.md](README.md) for all API endpoints
- Check [API documentation](http://localhost:5000/) in your browser
- Deploy to production (see README.md)

## Quick Commands Reference

```bash
# Start server
python app.py

# Run all tests
python test_client.py all

# Check setup
python check_setup.py

# Regenerate stations
python make_stations_json.py

# View logs (if running as service)
sudo journalctl -u wmata-api -f
```

## Common Issues

| Issue | Solution |
|-------|----------|
| 401 Unauthorized | Check API key |
| No trains showing | Check metro operating hours |
| Empty stations.json | Run `python make_stations_json.py` |
| Port in use | Change port in app.py or kill process |
| Module not found | Run `pip install -r requirements.txt` |

## Need Help?

1. Run `python check_setup.py` to diagnose issues
2. Check server logs for errors
3. Visit `/debug` endpoint: http://localhost:5000/debug
4. Read the full README.md

## API Endpoints Summary

- `GET /` - Documentation
- `GET /by-id/:id` - Station arrivals
- `GET /by-location?lat=X&lon=Y&radius=Z` - Nearby stations
- `GET /by-route/:route` - Route stations
- `GET /routes` - All routes
- `GET /stations` - All stations
- `GET /debug` - Debug info
- `WS /ws` - Real-time updates

Happy coding! 🚇
