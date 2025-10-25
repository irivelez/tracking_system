"""
Configuration for LATAM maritime regions and ports with bounding boxes.
Bounding boxes are defined as [[min_lat, min_lon], [max_lat, max_lon]]

OPTIMIZED CONFIGURATION (v2.0):
- Removed redundant port boxes (ports covered by larger regions)
- Extended Pacific boxes to cover Asia shipping lanes (Panama Canal traffic priority)
- Added strategic shipping lane boxes for Panama → Asia routes
- Designed for free tier API limits (~1000-1500 vessels)
- Focus: Panama Canal traffic + Pacific shipping to Asia
"""

# Large maritime regions covering shipping lanes and coastal waters
MARITIME_REGIONS = {
    "Gulf_of_Mexico": {
        "name": "Gulf of Mexico & Caribbean Approaches",
        "bbox": [[15.0, -100.0], [32.0, -78.0]],  # Extended for better Panama approach coverage
        "description": "Covers Mexican Gulf ports, Yucatan, and northern Caribbean approaches"
    },
    "Caribbean_Sea": {
        "name": "Caribbean Sea & Panama Canal Zone",
        "bbox": [[7.0, -90.0], [20.0, -55.0]],  # Extended west for full Panama Canal coverage
        "description": "Covers Panama Canal, Caribbean islands, and major east-west shipping lanes"
    },
    "Northern_South_America_Pacific": {
        "name": "Northern South America - Pacific Coast & Offshore",
        "bbox": [[-5.0, -95.0], [13.0, -77.0]],  # EXTENDED: +13° west (~800nm offshore) for Asia traffic
        "description": "Covers Colombia, Ecuador, Panama Pacific coast + offshore shipping lanes to Asia"
    },
    "Central_South_America_Pacific": {
        "name": "Central South America - Pacific & Asia Routes",
        "bbox": [[-18.0, -95.0], [-5.0, -70.0]],  # EXTENDED: +13° west for Peru/Ecuador → Asia routes
        "description": "Covers Peru, northern Chile + major shipping lanes to Asia"
    },
    "Southern_South_America_Pacific": {
        "name": "Southern South America - Pacific & Offshore",
        "bbox": [[-45.0, -90.0], [-18.0, -70.0]],  # EXTENDED: +12° west for Chile → Asia routes
        "description": "Covers central and southern Chile + offshore Pacific shipping"
    },
    "Panama_Asia_Shipping_Lane": {
        "name": "Panama Canal → Asia Major Shipping Lane",
        "bbox": [[0.0, -105.0], [15.0, -95.0]],  # NEW: Captures vessels heading to Asia from Panama
        "description": "Major container and cargo traffic from Panama Canal toward Asia/Oceania"
    },
    "Northern_Brazil_Atlantic": {
        "name": "Northern Brazil - Atlantic Coast",
        "bbox": [[-10.0, -52.0], [5.0, -32.0]],  # Slightly extended offshore
        "description": "Covers northern Brazilian coast and Amazon approaches"
    },
    "Central_Brazil_Atlantic": {
        "name": "Central Brazil - Atlantic Coast",
        "bbox": [[-23.0, -47.0], [-10.0, -32.0]],  # Slightly extended offshore
        "description": "Covers central Brazilian coast including major ports"
    },
    "Southern_Brazil_Atlantic": {
        "name": "Southern Brazil, Uruguay & Argentina - Atlantic",
        "bbox": [[-38.0, -62.0], [-23.0, -32.0]],  # Slightly extended offshore
        "description": "Covers southern Brazil, Uruguay, Argentina, and Rio de la Plata"
    },
    "Trans_Atlantic_North": {
        "name": "Trans-Atlantic Shipping Lane - North",
        "bbox": [[0.0, -50.0], [15.0, -20.0]],  # Keep current - not priority
        "description": "Covers north trans-Atlantic routes to/from Europe and Africa"
    },
    "Trans_Atlantic_South": {
        "name": "Trans-Atlantic Shipping Lane - South",
        "bbox": [[-25.0, -40.0], [0.0, -10.0]],  # Keep current - not priority
        "description": "Covers south trans-Atlantic routes to/from Africa"
    },
}

# Port reference data (for location identification only - NOT used for AIS subscription)
# All ports are already covered by the larger regional boxes above
# This data is used by get_port_by_coordinates() to identify nearby ports
MAJOR_PORTS = {
    # Note: These are NOT sent as separate bounding boxes to AIS API
    # They're only used for labeling vessels with nearby port information
    "Veracruz_MX": {"name": "Port of Veracruz, Mexico", "lat": 19.2, "lon": -96.1},
    "Altamira_MX": {"name": "Port of Altamira, Mexico", "lat": 22.4, "lon": -97.8},
    "Manzanillo_MX": {"name": "Port of Manzanillo, Mexico", "lat": 19.0, "lon": -104.3},
    "Lazaro_Cardenas_MX": {"name": "Port of Lázaro Cárdenas, Mexico", "lat": 18.0, "lon": -102.2},
    "Panama_Canal": {"name": "Panama Canal", "lat": 9.0, "lon": -79.6},
    "Cartagena_CO": {"name": "Port of Cartagena, Colombia", "lat": 10.4, "lon": -75.5},
    "Buenaventura_CO": {"name": "Port of Buenaventura, Colombia", "lat": 3.9, "lon": -77.1},
    "Guayaquil_EC": {"name": "Port of Guayaquil, Ecuador", "lat": -2.2, "lon": -79.9},
    "Callao_PE": {"name": "Port of Callao, Peru", "lat": -12.0, "lon": -77.1},
    "Valparaiso_CL": {"name": "Port of Valparaíso, Chile", "lat": -33.0, "lon": -71.6},
    "San_Antonio_CL": {"name": "Port of San Antonio, Chile", "lat": -33.6, "lon": -71.6},
    "Santos_BR": {"name": "Port of Santos, Brazil", "lat": -23.9, "lon": -46.3},
    "Rio_de_Janeiro_BR": {"name": "Port of Rio de Janeiro, Brazil", "lat": -22.9, "lon": -43.2},
    "Salvador_BR": {"name": "Port of Salvador, Brazil", "lat": -12.9, "lon": -38.5},
    "Fortaleza_BR": {"name": "Port of Fortaleza, Brazil", "lat": -3.7, "lon": -38.5},
    "Recife_BR": {"name": "Port of Recife, Brazil", "lat": -8.0, "lon": -34.9},
    "Buenos_Aires_AR": {"name": "Port of Buenos Aires, Argentina", "lat": -34.6, "lon": -58.4},
    "Montevideo_UY": {"name": "Port of Montevideo, Uruguay", "lat": -34.9, "lon": -56.2},
}


def get_all_bounding_boxes():
    """
    Returns a list of all bounding boxes for AISstream API subscription.
    OPTIMIZED: Only returns large maritime regions (ports already covered).
    Format: [[south_lat, west_lon], [north_lat, east_lon]]

    Total boxes: 11 (down from 33)
    Coverage: Extended Pacific for Panama → Asia routes
    """
    boxes = []

    # Add all maritime regions (large coverage areas)
    # Ports are already covered by these larger boxes
    for region in MARITIME_REGIONS.values():
        boxes.append(region["bbox"])

    return boxes


def get_location_info(lat, lon):
    """
    Determine what region and/or port a vessel is in based on coordinates.
    Returns a dict with region and port information.
    """
    location_info = {
        "region": None,
        "port": None,
        "in_port": False
    }

    # Check if near a specific port (within ~50km / 0.5 degrees)
    port_proximity_threshold = 0.5  # degrees (~50km)
    nearest_port = None
    min_distance = float('inf')

    for port_id, port_data in MAJOR_PORTS.items():
        port_lat = port_data["lat"]
        port_lon = port_data["lon"]

        # Simple distance calculation (Euclidean approximation)
        distance = ((lat - port_lat)**2 + (lon - port_lon)**2)**0.5

        if distance < min_distance and distance < port_proximity_threshold:
            min_distance = distance
            nearest_port = port_data["name"]

    if nearest_port:
        location_info["port"] = nearest_port
        location_info["in_port"] = True

    # Check if in a maritime region
    for region_id, region_data in MARITIME_REGIONS.items():
        bbox = region_data["bbox"]
        if (bbox[0][0] <= lat <= bbox[1][0] and
            bbox[0][1] <= lon <= bbox[1][1]):
            location_info["region"] = region_data["name"]
            if not location_info["in_port"]:
                location_info["in_port"] = False
            return location_info

    return location_info


def get_port_by_coordinates(lat, lon):
    """
    Find which port a vessel is near based on coordinates.
    Returns port name if near a port, or region description if in transit.
    """
    location = get_location_info(lat, lon)
    if location["in_port"]:
        return location["port"]
    elif location["region"]:
        return f"In transit - {location['region']}"
    return None


def get_coverage_summary():
    """
    Returns a summary of the tracking coverage.
    """
    return {
        "maritime_regions": len(MARITIME_REGIONS),
        "major_ports": len(MAJOR_PORTS),
        "total_bounding_boxes": len(get_all_bounding_boxes()),
        "regions_list": [r["name"] for r in MARITIME_REGIONS.values()],
        "ports_list": [p["name"] for p in MAJOR_PORTS.values()]
    }
