"""
AISstream WebSocket client for tracking vessels in LATAM ports.
"""
import asyncio
import json
import logging
import websockets
from dotenv import load_dotenv
import os
from ports_config import get_all_bounding_boxes, get_port_by_coordinates

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AISStreamClient:
    """WebSocket client for AISstream API."""

    def __init__(self, api_key, on_vessel_update=None):
        """
        Initialize the AIS client.

        Args:
            api_key: AISstream API key
            on_vessel_update: Callback function to handle vessel updates
        """
        self.api_key = api_key
        self.ws_url = "wss://stream.aisstream.io/v0/stream"
        self.on_vessel_update = on_vessel_update
        self.vessels = {}  # Store vessel data keyed by MMSI

    async def connect(self):
        """Connect to AISstream and start receiving data."""
        logger.info("Connecting to AISstream...")

        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Get bounding boxes
                bboxes = get_all_bounding_boxes()

                # Send subscription message
                subscribe_message = {
                    "APIKey": self.api_key,
                    "BoundingBoxes": bboxes
                }

                logger.info(f"Sending subscription with {len(bboxes)} bounding boxes...")
                logger.info(f"Sample boxes: {bboxes[:2]}")

                await websocket.send(json.dumps(subscribe_message))

                logger.info(f"✓ Subscribed to {len(bboxes)} regions")
                logger.info("Waiting for AIS messages...")

                # Receive and process messages
                async for message_json in websocket:
                    try:
                        message = json.loads(message_json)
                        await self.process_message(message)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")

        except websockets.exceptions.WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

    async def process_message(self, message):
        """
        Process incoming AIS message.

        Args:
            message: Parsed JSON message from AISstream
        """
        # AISstream sends messages with "MessageType" field
        message_type = message.get("MessageType")

        if message_type == "PositionReport":
            await self.handle_position_report(message)
        elif message_type == "ShipStaticData":
            await self.handle_static_data(message)

    async def handle_position_report(self, message):
        """Handle position report messages (vessel movement)."""
        try:
            metadata = message.get("MetaData", {})
            position_report = message.get("Message", {}).get("PositionReport", {})

            mmsi = metadata.get("MMSI")
            if not mmsi:
                return

            # Extract position data
            lat = position_report.get("Latitude")
            lon = position_report.get("Longitude")

            if lat is None or lon is None:
                return

            # Get or create vessel data
            if mmsi not in self.vessels:
                self.vessels[mmsi] = {}

            vessel = self.vessels[mmsi]
            vessel.update({
                "mmsi": mmsi,
                "latitude": lat,
                "longitude": lon,
                "speed": position_report.get("Sog", 0),  # Speed over ground
                "heading": position_report.get("TrueHeading", position_report.get("Cog", 0)),
                "timestamp": metadata.get("time_utc"),
                "nearby_port": get_port_by_coordinates(lat, lon)
            })

            # Call callback if provided
            if self.on_vessel_update:
                await self.on_vessel_update(vessel)

            # Count position reports
            if not hasattr(self, 'position_count'):
                self.position_count = 0
            self.position_count += 1

            # Log every 50th position to track flow
            if self.position_count % 50 == 0:
                location = get_port_by_coordinates(lat, lon)
                vessel_name = vessel.get('name', f'MMSI {mmsi}')
                logger.info(f"📍 Position #{self.position_count}: {vessel_name} at ({lat:.4f}, {lon:.4f}) - {location or 'Unknown'}")

        except Exception as e:
            logger.error(f"Error handling position report: {e}")

    async def handle_static_data(self, message):
        """Handle static data messages (vessel information)."""
        try:
            metadata = message.get("MetaData", {})
            static_data = message.get("Message", {}).get("ShipStaticData", {})

            mmsi = metadata.get("MMSI")
            if not mmsi:
                return

            # Get or create vessel data
            if mmsi not in self.vessels:
                self.vessels[mmsi] = {"mmsi": mmsi}

            vessel = self.vessels[mmsi]
            vessel.update({
                "name": static_data.get("Name", "Unknown").strip(),
                "callsign": static_data.get("CallSign", "").strip(),
                "vessel_type": self.get_vessel_type_name(static_data.get("Type", 0)),
                "destination": static_data.get("Destination", "Unknown").strip(),
                "imo": static_data.get("ImoNumber"),
            })

            # Call callback if provided
            if self.on_vessel_update:
                await self.on_vessel_update(vessel)

            logger.info(f"Static data for {vessel.get('name', 'Unknown')} (MMSI: {mmsi})")

        except Exception as e:
            logger.error(f"Error handling static data: {e}")

    def get_vessel_type_name(self, type_code):
        """Convert AIS vessel type code to readable name."""
        vessel_types = {
            0: "Unknown",
            20: "Wing in ground (WIG)",
            30: "Fishing",
            31: "Towing",
            32: "Towing (large)",
            33: "Dredging/Underwater ops",
            34: "Diving ops",
            35: "Military ops",
            36: "Sailing",
            37: "Pleasure Craft",
            40: "High speed craft",
            50: "Pilot Vessel",
            51: "Search and Rescue",
            52: "Tug",
            53: "Port Tender",
            54: "Anti-pollution",
            55: "Law Enforcement",
            58: "Medical Transport",
            59: "Non-combatant ship",
            60: "Passenger",
            70: "Cargo",
            80: "Tanker",
            90: "Other",
        }

        # Get the main type (tens digit)
        main_type = (type_code // 10) * 10
        return vessel_types.get(main_type, f"Type {type_code}")


async def main():
    """Main function for testing the client standalone."""
    api_key = os.getenv("AISSTREAM_API_KEY")

    if not api_key or api_key == "your_api_key_here":
        logger.error("Please set your AISSTREAM_API_KEY in the .env file")
        return

    async def print_vessel_update(vessel):
        """Print vessel updates to console."""
        print(f"\n{'='*60}")
        print(f"Vessel: {vessel.get('name', 'Unknown')}")
        print(f"MMSI: {vessel.get('mmsi')}")
        print(f"Type: {vessel.get('vessel_type', 'Unknown')}")
        print(f"Position: {vessel.get('latitude', 'N/A')}, {vessel.get('longitude', 'N/A')}")
        print(f"Speed: {vessel.get('speed', 'N/A')} knots")
        print(f"Heading: {vessel.get('heading', 'N/A')}°")
        print(f"Destination: {vessel.get('destination', 'Unknown')}")
        if vessel.get('nearby_port'):
            print(f"Near: {vessel['nearby_port']}")
        print(f"{'='*60}")

    client = AISStreamClient(api_key, on_vessel_update=print_vessel_update)
    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())
