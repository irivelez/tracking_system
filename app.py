"""
Flask application with SocketIO for real-time vessel tracking dashboard.
Optimized for high-volume data with throttling and batching.
"""
import asyncio
import os
import time
from threading import Thread, Lock
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
from ais_client import AISStreamClient
from ports_config import MARITIME_REGIONS, MAJOR_PORTS, get_coverage_summary
import logging
import math

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store vessel data with thread-safe lock
vessels_data = {}
vessels_lock = Lock()

# Performance configuration - OPTIMIZED for 1000-1500 vessels
UPDATE_BATCH_INTERVAL = 3.0  # Send batched updates every 3 seconds (increased from 2.0)
MIN_POSITION_CHANGE = 0.001  # ~100 meters (0.001 degrees latitude ≈ 111 meters)
MIN_UPDATE_INTERVAL = 15.0  # Don't update same vessel more than once per 15 seconds (increased from 10.0)
MAX_VESSELS_STORED = 2000  # Maximum vessels to keep in memory (prevent memory bloat)


class VesselDataManager:
    """Manages vessel data with intelligent filtering and batching."""

    def __init__(self):
        self.vessels = {}
        self.pending_updates = {}
        self.last_sent_data = {}  # Track what we last sent to clients
        self.last_update_time = {}  # Track last update timestamp for each vessel
        self.lock = Lock()
        self.stats = {
            'total_updates': 0,
            'filtered_updates': 0,
            'sent_updates': 0,
            'cleaned_vessels': 0
        }

    def should_update_vessel(self, mmsi, vessel_data):
        """
        Determine if vessel update should be sent based on significance.
        Only send updates if:
        1. It's a new vessel
        2. Position changed significantly (>100m)
        3. Static data changed (name, type, destination)
        4. Enough time has passed since last update
        """
        if mmsi not in self.last_sent_data:
            return True  # New vessel

        last_sent = self.last_sent_data[mmsi]
        current_time = time.time()

        # Check if minimum time interval has passed
        last_update_time = last_sent.get('_update_time', 0)
        if current_time - last_update_time < MIN_UPDATE_INTERVAL:
            # Only send if critical data changed
            if (vessel_data.get('name') != last_sent.get('name') or
                vessel_data.get('destination') != last_sent.get('destination')):
                return True
            return False

        # Check position change
        if 'latitude' in vessel_data and 'longitude' in vessel_data:
            last_lat = last_sent.get('latitude')
            last_lon = last_sent.get('longitude')
            curr_lat = vessel_data.get('latitude')
            curr_lon = vessel_data.get('longitude')

            if last_lat is not None and last_lon is not None:
                # Calculate distance moved
                lat_diff = abs(curr_lat - last_lat)
                lon_diff = abs(curr_lon - last_lon)
                distance = math.sqrt(lat_diff**2 + lon_diff**2)

                # If vessel hasn't moved much, skip update
                if distance < MIN_POSITION_CHANGE:
                    return False

        return True

    def add_update(self, vessel_data):
        """Add vessel update to pending batch."""
        self.stats['total_updates'] += 1

        mmsi = vessel_data.get('mmsi')
        if not mmsi:
            return

        with self.lock:
            # Update internal vessel storage
            if mmsi not in self.vessels:
                self.vessels[mmsi] = {}
            self.vessels[mmsi].update(vessel_data)

            # Track last update time for cleanup
            self.last_update_time[mmsi] = time.time()

            # Check if update is significant enough to send
            if self.should_update_vessel(mmsi, vessel_data):
                self.pending_updates[mmsi] = self.vessels[mmsi].copy()
                self.stats['sent_updates'] += 1
            else:
                self.stats['filtered_updates'] += 1

    def get_batch_updates(self):
        """Get and clear pending updates."""
        with self.lock:
            updates = list(self.pending_updates.values())

            # Update last_sent_data with current timestamp
            current_time = time.time()
            for mmsi, data in self.pending_updates.items():
                data['_update_time'] = current_time
                self.last_sent_data[mmsi] = data.copy()

            self.pending_updates.clear()
            return updates

    def get_all_vessels(self):
        """Get all vessel data."""
        with self.lock:
            return list(self.vessels.values())

    def cleanup_stale_vessels(self):
        """
        Remove vessels that haven't been updated in 6 hours (likely out of coverage area).
        Also enforce MAX_VESSELS_STORED limit to prevent memory bloat.
        """
        with self.lock:
            current_time = time.time()
            stale_threshold = 6 * 3600  # 6 hours in seconds
            vessels_to_remove = []

            # Find stale vessels
            for mmsi, last_time in self.last_update_time.items():
                if current_time - last_time > stale_threshold:
                    vessels_to_remove.append(mmsi)

            # If still over limit, remove oldest vessels
            if len(self.vessels) > MAX_VESSELS_STORED:
                # Sort by last update time, oldest first
                sorted_vessels = sorted(
                    self.last_update_time.items(),
                    key=lambda x: x[1]
                )
                # Remove oldest vessels beyond the limit
                excess = len(self.vessels) - MAX_VESSELS_STORED
                for mmsi, _ in sorted_vessels[:excess]:
                    if mmsi not in vessels_to_remove:
                        vessels_to_remove.append(mmsi)

            # Remove vessels
            for mmsi in vessels_to_remove:
                self.vessels.pop(mmsi, None)
                self.last_sent_data.pop(mmsi, None)
                self.last_update_time.pop(mmsi, None)
                self.pending_updates.pop(mmsi, None)

            if vessels_to_remove:
                self.stats['cleaned_vessels'] += len(vessels_to_remove)
                logger.info(f"Cleaned up {len(vessels_to_remove)} stale vessels. Active: {len(self.vessels)}")

    def get_stats(self):
        """Get performance statistics."""
        with self.lock:
            total = self.stats['total_updates']
            filtered = self.stats['filtered_updates']
            sent = self.stats['sent_updates']
            cleaned = self.stats['cleaned_vessels']
            filter_rate = (filtered / total * 100) if total > 0 else 0
            return {
                'total_updates': total,
                'filtered_updates': filtered,
                'sent_updates': sent,
                'cleaned_vessels': cleaned,
                'filter_rate': f"{filter_rate:.1f}%",
                'active_vessels': len(self.vessels)
            }


# Initialize vessel manager
vessel_manager = VesselDataManager()


@app.route('/')
def index():
    """Render the main dashboard."""
    coverage = get_coverage_summary()
    return render_template('index.html',
                         regions=MARITIME_REGIONS,
                         ports=MAJOR_PORTS,
                         coverage=coverage)


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info('Client connected')
    # Send all current vessels data to newly connected client
    vessels = vessel_manager.get_all_vessels()
    logger.info(f"Sending {len(vessels)} vessels to new client in batches")

    # Send in batches to avoid overwhelming the client
    batch_size = 100
    for i in range(0, len(vessels), batch_size):
        batch = vessels[i:i + batch_size]
        if i == 0:
            # First batch uses initial_vessels
            emit('initial_vessels', batch)
        else:
            # Subsequent batches use batch update
            emit('vessel_batch_update', {
                'vessels': batch,
                'timestamp': time.time()
            })
        logger.info(f"Sent batch {i//batch_size + 1}: {len(batch)} vessels")

    logger.info(f"✓ Sent all {len(vessels)} vessels")


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info('Client disconnected')


@socketio.on('request_stats')
def handle_stats_request():
    """Send performance statistics to client."""
    stats = vessel_manager.get_stats()
    emit('stats_update', stats)


def send_batched_updates():
    """
    Background task that sends batched vessel updates at regular intervals.
    This prevents overwhelming the clients with individual updates.
    """
    logger.info("Starting batch update sender...")
    last_cleanup_time = time.time()

    while True:
        try:
            time.sleep(UPDATE_BATCH_INTERVAL)

            # Get pending updates
            updates = vessel_manager.get_batch_updates()

            if updates:
                # Send batch to all connected clients
                socketio.emit('vessel_batch_update', {
                    'vessels': updates,
                    'timestamp': time.time()
                })
                logger.debug(f"Sent batch of {len(updates)} vessel updates")

            # Log stats every 30 seconds
            if int(time.time()) % 30 == 0:
                stats = vessel_manager.get_stats()
                logger.info(f"Performance stats: {stats}")

            # Cleanup stale vessels every 10 minutes
            current_time = time.time()
            if current_time - last_cleanup_time > 600:  # 10 minutes
                vessel_manager.cleanup_stale_vessels()
                last_cleanup_time = current_time

        except Exception as e:
            logger.error(f"Error in batch sender: {e}")


async def vessel_update_callback(vessel):
    """
    Callback function to handle vessel updates from AIS client.
    Adds updates to batch queue instead of sending immediately.
    """
    vessel_manager.add_update(vessel)


def run_ais_client():
    """Run the AIS client in a separate thread."""
    api_key = os.getenv("AISSTREAM_API_KEY")

    if not api_key or api_key == "your_api_key_here":
        logger.error("Please set your AISSTREAM_API_KEY in the .env file")
        return

    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    client = AISStreamClient(api_key, on_vessel_update=vessel_update_callback)

    try:
        loop.run_until_complete(client.connect())
    except KeyboardInterrupt:
        logger.info("AIS client stopped by user")
    except Exception as e:
        logger.error(f"AIS client error: {e}")
    finally:
        loop.close()


def start_background_tasks():
    """Start background tasks (AIS client and batch sender)."""
    # Start AIS client
    ais_thread = Thread(target=run_ais_client, daemon=True)
    ais_thread.start()
    logger.info("AIS client thread started")

    # Start batch update sender
    batch_thread = Thread(target=send_batched_updates, daemon=True)
    batch_thread.start()
    logger.info("Batch update sender started")


if __name__ == '__main__':
    coverage = get_coverage_summary()
    logger.info("Starting optimized vessel tracking system...")
    logger.info(f"Coverage: {coverage['maritime_regions']} maritime regions, {coverage['major_ports']} major ports")
    logger.info(f"Total bounding boxes: {coverage['total_bounding_boxes']}")
    logger.info(f"Update batch interval: {UPDATE_BATCH_INTERVAL}s")
    logger.info(f"Minimum position change filter: {MIN_POSITION_CHANGE}° (~{MIN_POSITION_CHANGE * 111:.0f}m)")

    # Start the AIS client in background
    start_background_tasks()

    # Run Flask app with SocketIO
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, use_reloader=False)
