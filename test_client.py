"""
Test client for WMATA API
Demonstrates how to use both REST endpoints and WebSocket
"""

import requests
import json
import websocket
import threading
import time

BASE_URL = "http://localhost:5000"
WS_URL = "ws://localhost:5000/ws"


def test_rest_endpoints():
    """Test all REST API endpoints"""
    print("=" * 60)
    print("Testing REST API Endpoints")
    print("=" * 60)
    
    # Test /routes
    print("\n1. Getting all routes...")
    response = requests.get(f"{BASE_URL}/routes")
    if response.status_code == 200:
        data = response.json()
        print(f"   Found {len(data['routes'])} routes: {data['routes']}")
    else:
        print(f"   Error: {response.status_code}")
    
    # Test /by-id
    print("\n2. Getting station A01 (Metro Center)...")
    response = requests.get(f"{BASE_URL}/by-id/A01")
    if response.status_code == 200:
        data = response.json()
        print(f"   Station: {data.get('name', 'Unknown')}")
        print(f"   Northbound trains: {len(data.get('N', []))}")
        print(f"   Southbound trains: {len(data.get('S', []))}")
        if data.get('N'):
            print(f"   Next northbound: {data['N'][0]}")
    else:
        print(f"   Error: {response.status_code}")
    
    # Test /by-location (Union Station area)
    print("\n3. Getting stations near Union Station...")
    response = requests.get(
        f"{BASE_URL}/by-location",
        params={'lat': 38.8977, 'lon': -77.0063, 'radius': 1}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   Found {len(data['data'])} nearby stations")
        for station in data['data'][:3]:
            print(f"   - {station['name']} ({station['distance']} km)")
    else:
        print(f"   Error: {response.status_code}")
    
    # Test /by-route (Red Line)
    print("\n4. Getting Red Line stations...")
    response = requests.get(f"{BASE_URL}/by-route/RD")
    if response.status_code == 200:
        data = response.json()
        print(f"   Found {len(data['data'])} stations on Red Line")
        for station in data['data'][:3]:
            print(f"   - {station['name']}")
    else:
        print(f"   Error: {response.status_code}")


def test_websocket():
    """Test WebSocket real-time updates"""
    print("\n" + "=" * 60)
    print("Testing WebSocket Connection")
    print("=" * 60)
    print("\nConnecting to WebSocket...")
    print("(Will receive updates every CACHE_SECONDS interval)")
    print("Press Ctrl+C to stop\n")
    
    update_count = [0]
    
    def on_message(ws, message):
        update_count[0] += 1
        
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            print(f"  ✗ Invalid JSON received")
            return
        
        print(f"\n--- Update #{update_count[0]} ---")
        print(f"Time: {time.strftime('%H:%M:%S')}")
        
        if 'data' in data:
            print(f"Stations with trains: {len(data['data'])}")
            print(f"Last update: {data.get('updated', 'Unknown')}")
            
            # Show first 3 stations with trains
            stations_with_arrivals = [s for s in data['data'] if s.get('N') or s.get('S')]
            if stations_with_arrivals:
                print(f"\nSample stations:")
                for station in stations_with_arrivals[:3]:
                    total_trains = len(station.get('N', [])) + len(station.get('S', []))
                    print(f"  - {station['name']}: {total_trains} trains")
            else:
                print("  No stations with trains currently")
        else:
            print(f"Unexpected message format: {list(data.keys())}")
    
    def on_error(ws, error):
        print(f"\n✗ WebSocket error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print(f"\n✓ WebSocket connection closed")
        if close_status_code:
            print(f"  Status: {close_status_code}")
        if close_msg:
            print(f"  Message: {close_msg}")
    
    def on_open(ws):
        print("✓ WebSocket connected! Waiting for updates...\n")
    
    try:
        ws = websocket.WebSocketApp(
            WS_URL,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        ws.run_forever()
    except ConnectionRefusedError:
        print("\n✗ Connection refused. Is the server running?")
    except Exception as e:
        print(f"\n✗ Error: {e}")


def test_concurrent_requests():
    """Test multiple concurrent requests"""
    print("\n" + "=" * 60)
    print("Testing Concurrent Requests")
    print("=" * 60)
    
    import concurrent.futures
    
    station_ids = ['A01', 'A02', 'A03', 'C01', 'D01']
    
    def fetch_station(stop_id):
        try:
            response = requests.get(f"{BASE_URL}/by-id/{stop_id}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return f"{stop_id}: {data.get('name', 'Unknown')}"
            else:
                return f"{stop_id}: Error {response.status_code}"
        except Exception as e:
            return f"{stop_id}: {str(e)}"
    
    print(f"\nFetching {len(station_ids)} stations concurrently...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_station, sid) for sid in station_ids]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    print("\nResults:")
    for result in results:
        print(f"  {result}")


def main():
    import sys
    
    print("\nWMATA API Test Client")
    print("Make sure the server is running on localhost:5000\n")
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        print("Available test modes:")
        print("  python test_client.py rest       - Test REST endpoints")
        print("  python test_client.py websocket  - Test WebSocket updates")
        print("  python test_client.py concurrent - Test concurrent requests")
        print("  python test_client.py all        - Run all tests")
        print()
        mode = input("Select mode (rest/websocket/concurrent/all): ").strip().lower()
    
    try:
        if mode in ['rest', 'all']:
            test_rest_endpoints()
        
        if mode in ['concurrent', 'all']:
            test_concurrent_requests()
        
        if mode in ['websocket', 'all']:
            test_websocket()
        
        if mode not in ['rest', 'websocket', 'concurrent', 'all']:
            print(f"Unknown mode: {mode}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to server. Is it running on localhost:5000?")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == '__main__':
    main()
