"""
SRAM AXS Real-time Data Monitor
Connects to SRAM AXS, Wahoo, and Quarq devices via Bluetooth
Provides text interface and REST API
"""

import asyncio
import argparse
import threading
import time
from flask import Flask, jsonify
from sram_axs import SRAMManager

# Global variables for sharing data between async and Flask
manager = None
latest_data = {}
app = Flask(__name__)


def update_data(new_data):
    """Callback function to update data from BLE notifications"""
    global latest_data
    device_name = new_data.get("device", "Unknown")
    latest_data[device_name] = new_data


def print_text_display():
    """Display real-time data in terminal"""
    print("\n" + "=" * 80)
    print("SRAM AXS Real-time Monitor")
    print("=" * 80)

    if not latest_data:
        print("\nWaiting for data...")
        return

    for device_name, data in latest_data.items():
        print(f"\n{device_name}:")
        if data.get("type") == "power":
            print(f"  Power: {data.get('power_watts', 0)} W")
            print(f"  Cadence: {data.get('cadence_rpm', 0)} RPM")
        elif data.get("type") == "heart_rate":
            print(f"  Heart Rate: {data.get('bpm', 0)} BPM")

    print("\n" + "=" * 80)


async def monitor_loop(show_text=True):
    """Main monitoring loop"""
    global manager

    manager = SRAMManager()

    # Scan for devices
    await manager.scan_devices(duration=10)

    if not manager.devices:
        print("No compatible devices found!")
        return

    # Connect to all devices
    await manager.connect_all()

    # Start notifications
    await manager.start_all_notifications(update_data)

    print("\nMonitoring started. Press Ctrl+C to stop.")

    # Main loop
    try:
        while True:
            if show_text:
                print_text_display()
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        await manager.disconnect_all()


def run_flask_app(port=8080):
    """Run Flask API server"""
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


@app.route('/get', methods=['GET'])
def get_data():
    """API endpoint to get current sensor data"""
    return jsonify(latest_data)


@app.route('/health', methods=['GET'])
def health():
    """API health check endpoint"""
    return jsonify({
        "status": "ok",
        "connected_devices": len(latest_data)
    })


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='SRAM AXS Real-time Monitor')
    parser.add_argument('--no-text', action='store_true',
                        help='Suppress text display')
    parser.add_argument('--no-api', action='store_true',
                        help='Skip running the API server')
    parser.add_argument('--port', type=int, default=8080,
                        help='API server port (default: 8080)')

    args = parser.parse_args()

    show_text = not args.no_text
    run_api = not args.no_api

    # Start Flask API in a separate thread if enabled
    if run_api:
        api_thread = threading.Thread(
            target=run_flask_app,
            args=(args.port,),
            daemon=True
        )
        api_thread.start()
        print(f"API server started on port {args.port}")
        time.sleep(1)  # Give Flask a moment to start

    # Run the async monitoring loop
    try:
        asyncio.run(monitor_loop(show_text=show_text))
    except KeyboardInterrupt:
        print("\nShutdown complete.")


if __name__ == "__main__":
    main()
