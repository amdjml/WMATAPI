"""
Check WMATA API setup and configuration
Run this before starting the server to verify everything is configured correctly
"""

import os
import sys
import json

def check_python_version():
    """Check Python version"""
    print("✓ Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print(f"  ✗ Python {version.major}.{version.minor} detected. Python 3.7+ required.")
        return False
    print(f"  ✓ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_dependencies():
    """Check if required packages are installed"""
    print("\n✓ Checking dependencies...")
    required = {
        'flask': 'Flask',
        'flask_sock': 'flask-sock',
        'requests': 'requests',
        'google.transit': 'gtfs-realtime-bindings'
    }
    
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - NOT INSTALLED")
            missing.append(package)
    
    if missing:
        print(f"\n  Install missing packages:")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    return True


def check_api_key():
    """Check if API key is configured"""
    print("\n✓ Checking WMATA API key...")
    
    # Check environment variable
    api_key = os.environ.get('WMATA_API_KEY')
    if api_key:
        print(f"  ✓ Found in environment: {api_key[:10]}...")
        return True
    
    # Check settings.cfg
    if os.path.exists('settings.cfg'):
        with open('settings.cfg', 'r') as f:
            for line in f:
                if line.startswith('WMATA_API_KEY'):
                    key = line.split('=')[1].strip().strip('"').strip("'")
                    if key and key != 'your_api_key_here':
                        print(f"  ✓ Found in settings.cfg: {key[:10]}...")
                        return True
    
    print("  ✗ API key not found!")
    print("  Set it via:")
    print("    export WMATA_API_KEY=your_key_here")
    print("  OR edit settings.cfg")
    return False


def check_stations_file():
    """Check if stations.json exists and is valid"""
    print("\n✓ Checking stations.json...")
    
    if not os.path.exists('stations.json'):
        print("  ✗ stations.json not found!")
        print("  Generate it with:")
        print("    python make_stations_json.py")
        return False
    
    try:
        with open('stations.json', 'r') as f:
            stations = json.load(f)
        
        if not stations:
            print("  ✗ stations.json is empty!")
            return False
        
        print(f"  ✓ Found {len(stations)} stations")
        
        # Check format
        sample = list(stations.values())[0]
        required_fields = ['name', 'lat', 'lon']
        missing = [f for f in required_fields if f not in sample]
        
        if missing:
            print(f"  ⚠ Missing fields in stations: {missing}")
            print("  Regenerate with: python make_stations_json.py")
            return False
        
        # Show sample
        sample_id = list(stations.keys())[0]
        print(f"  Sample: {sample_id} -> {stations[sample_id]['name']}")
        
        return True
        
    except json.JSONDecodeError:
        print("  ✗ stations.json is not valid JSON!")
        return False
    except Exception as e:
        print(f"  ✗ Error reading stations.json: {e}")
        return False


def check_settings_file():
    """Check if settings.cfg exists"""
    print("\n✓ Checking settings.cfg...")
    
    if not os.path.exists('settings.cfg'):
        print("  ⚠ settings.cfg not found")
        if os.path.exists('settings.cfg.sample'):
            print("  Copy sample:")
            print("    cp settings.cfg.sample settings.cfg")
        return False
    
    print("  ✓ settings.cfg exists")
    return True


def test_wmata_connection():
    """Test connection to WMATA API"""
    print("\n✓ Testing WMATA API connection...")
    
    api_key = os.environ.get('WMATA_API_KEY')
    if not api_key and os.path.exists('settings.cfg'):
        with open('settings.cfg', 'r') as f:
            for line in f:
                if line.startswith('WMATA_API_KEY'):
                    api_key = line.split('=')[1].strip().strip('"').strip("'")
                    break
    
    if not api_key or api_key == 'your_api_key_here':
        print("  ⚠ Skipping (no API key)")
        return False
    
    try:
        import requests
        
        url = "https://api.wmata.com/gtfs/rail-gtfsrt-tripupdates.pb"
        headers = {'api_key': api_key}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"  ✓ Connection successful ({len(response.content)} bytes)")
            return True
        elif response.status_code == 401:
            print("  ✗ Authentication failed - check your API key")
            return False
        else:
            print(f"  ✗ HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ✗ Connection error: {e}")
        return False


def check_port():
    """Check if port 5000 is available"""
    print("\n✓ Checking port 5000...")
    
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 5000))
        sock.close()
        
        if result == 0:
            print("  ⚠ Port 5000 is already in use")
            print("  Stop other services or change port in app.py")
            return False
        else:
            print("  ✓ Port 5000 is available")
            return True
    except Exception as e:
        print(f"  ⚠ Could not check port: {e}")
        return True


def main():
    print("=" * 60)
    print("WMATA API Setup Check")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version()),
        ("Dependencies", check_dependencies()),
        ("API Key", check_api_key()),
        ("Settings File", check_settings_file()),
        ("Stations File", check_stations_file()),
        ("WMATA Connection", test_wmata_connection()),
        ("Port Availability", check_port())
    ]
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    for name, result in checks:
        status = "✓" if result else "✗"
        print(f"  {status} {name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All checks passed! Ready to start server:")
        print("  python app.py")
        return 0
    else:
        print("\n✗ Some checks failed. Fix the issues above before starting.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
