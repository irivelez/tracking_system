"""
Configuration for LATAM maritime regions and ports with bounding boxes.
Bounding boxes are defined as [[min_lat, min_lon], [max_lat, max_lon]]

This configuration covers:
1. Large maritime regions for vessels in transit
2. Specific port areas for detailed port activity tracking
"""

# Large maritime regions covering shipping lanes and coastal waters
MARITIME_REGIONS = {
    "Gulf_of_Mexico": {
        "name": "Gulf of Mexico & Caribbean Approaches",
        "bbox": [[18.0, -98.0], [30.0, -80.0]],
        "description": "Covers Mexican Gulf ports, Yucatan, and northern Caribbean approaches"
    },
    "Caribbean_Sea": {
        "name": "Caribbean Sea & Panama Approaches",
        "bbox": [[8.0, -85.0], [20.0, -60.0]],
        "description": "Covers Panama Canal, Caribbean islands, and major east-west shipping lanes"
    },
    "Northern_South_America_Pacific": {
        "name": "Northern South America - Pacific Coast",
        "bbox": [[-5.0, -82.0], [13.0, -77.0]],
        "description": "Covers Colombia, Ecuador, and Panama Pacific coast"
    },
    "Central_South_America_Pacific": {
        "name": "Central South America - Pacific Coast",
        "bbox": [[-18.0, -82.0], [-5.0, -70.0]],
        "description": "Covers Peru and northern Chile Pacific coast"
    },
    "Southern_South_America_Pacific": {
        "name": "Southern South America - Pacific Coast",
        "bbox": [[-45.0, -78.0], [-18.0, -70.0]],
        "description": "Covers central and southern Chile Pacific coast"
    },
    "Northern_Brazil_Atlantic": {
        "name": "Northern Brazil - Atlantic Coast",
        "bbox": [[-10.0, -50.0], [5.0, -34.0]],
        "description": "Covers northern Brazilian coast and Amazon approaches"
    },
    "Central_Brazil_Atlantic": {
        "name": "Central Brazil - Atlantic Coast",
        "bbox": [[-23.0, -45.0], [-10.0, -34.0]],
        "description": "Covers central Brazilian coast including major ports"
    },
    "Southern_Brazil_Atlantic": {
        "name": "Southern Brazil, Uruguay & Argentina - Atlantic",
        "bbox": [[-38.0, -60.0], [-23.0, -34.0]],
        "description": "Covers southern Brazil, Uruguay, Argentina, and Rio de la Plata"
    },
    "Trans_Atlantic_North": {
        "name": "Trans-Atlantic Shipping Lane - North",
        "bbox": [[0.0, -50.0], [15.0, -20.0]],
        "description": "Covers north trans-Atlantic routes to/from Europe and Africa"
    },
    "Trans_Atlantic_South": {
        "name": "Trans-Atlantic Shipping Lane - South",
        "bbox": [[-25.0, -40.0], [0.0, -10.0]],
        "description": "Covers south trans-Atlantic routes to/from Africa"
    },
}

# Specific major ports for detailed tracking
MAJOR_PORTS = {
    # Mexico - Gulf Coast
    "Veracruz_MX": {
        "name": "Port of Veracruz, Mexico",
        "bbox": [[19.0, -96.3], [19.4, -95.9]],
        "region": "Gulf_of_Mexico"
    },
    "Altamira_MX": {
        "name": "Port of Altamira, Mexico",
        "bbox": [[22.3, -97.9], [22.5, -97.7]],
        "region": "Gulf_of_Mexico"
    },

    # Mexico - Pacific Coast
    "Manzanillo_MX": {
        "name": "Port of Manzanillo, Mexico",
        "bbox": [[18.8, -104.5], [19.3, -104.1]],
        "region": "Northern_South_America_Pacific"
    },
    "Lazaro_Cardenas_MX": {
        "name": "Port of Lázaro Cárdenas, Mexico",
        "bbox": [[17.8, -102.4], [18.2, -102.0]],
        "region": "Northern_South_America_Pacific"
    },

    # Central America - Panama
    "Panama_Canal_Atlantic": {
        "name": "Panama Canal - Atlantic Entrance",
        "bbox": [[9.2, -80.0], [9.5, -79.8]],
        "region": "Caribbean_Sea"
    },
    "Panama_Canal_Pacific": {
        "name": "Panama Canal - Pacific Entrance",
        "bbox": [[8.8, -79.7], [9.1, -79.4]],
        "region": "Northern_South_America_Pacific"
    },
    "Colon_PA": {
        "name": "Port of Colón, Panama",
        "bbox": [[9.2, -80.0], [9.5, -79.8]],
        "region": "Caribbean_Sea"
    },
    "Balboa_PA": {
        "name": "Port of Balboa, Panama",
        "bbox": [[8.8, -79.7], [9.1, -79.4]],
        "region": "Northern_South_America_Pacific"
    },

    # Colombia
    "Cartagena_CO": {
        "name": "Port of Cartagena, Colombia",
        "bbox": [[10.2, -75.7], [10.6, -75.3]],
        "region": "Caribbean_Sea"
    },
    "Buenaventura_CO": {
        "name": "Port of Buenaventura, Colombia",
        "bbox": [[3.7, -77.3], [4.1, -76.9]],
        "region": "Northern_South_America_Pacific"
    },

    # Ecuador
    "Guayaquil_EC": {
        "name": "Port of Guayaquil, Ecuador",
        "bbox": [[-2.4, -80.1], [-2.0, -79.8]],
        "region": "Northern_South_America_Pacific"
    },

    # Peru
    "Callao_PE": {
        "name": "Port of Callao, Peru",
        "bbox": [[-12.2, -77.3], [-11.8, -76.9]],
        "region": "Central_South_America_Pacific"
    },

    # Chile
    "Valparaiso_CL": {
        "name": "Port of Valparaíso, Chile",
        "bbox": [[-33.2, -71.8], [-32.8, -71.4]],
        "region": "Southern_South_America_Pacific"
    },
    "San_Antonio_CL": {
        "name": "Port of San Antonio, Chile",
        "bbox": [[-33.7, -71.8], [-33.4, -71.5]],
        "region": "Southern_South_America_Pacific"
    },

    # Brazil - Atlantic Coast
    "Santos_BR": {
        "name": "Port of Santos, Brazil",
        "bbox": [[-24.1, -46.5], [-23.8, -46.1]],
        "region": "Central_Brazil_Atlantic"
    },
    "Rio_de_Janeiro_BR": {
        "name": "Port of Rio de Janeiro, Brazil",
        "bbox": [[-23.1, -43.4], [-22.7, -43.0]],
        "region": "Central_Brazil_Atlantic"
    },
    "Paranagua_BR": {
        "name": "Port of Paranaguá, Brazil",
        "bbox": [[-25.7, -48.7], [-25.3, -48.3]],
        "region": "Southern_Brazil_Atlantic"
    },
    "Itajai_BR": {
        "name": "Port of Itajaí, Brazil",
        "bbox": [[-27.0, -48.8], [-26.8, -48.5]],
        "region": "Southern_Brazil_Atlantic"
    },
    "Salvador_BR": {
        "name": "Port of Salvador, Brazil",
        "bbox": [[-13.1, -38.7], [-12.7, -38.3]],
        "region": "Central_Brazil_Atlantic"
    },
    "Fortaleza_BR": {
        "name": "Port of Fortaleza, Brazil",
        "bbox": [[-3.9, -38.7], [-3.5, -38.3]],
        "region": "Northern_Brazil_Atlantic"
    },
    "Recife_BR": {
        "name": "Port of Recife, Brazil",
        "bbox": [[-8.2, -35.0], [-7.9, -34.7]],
        "region": "Northern_Brazil_Atlantic"
    },

    # Argentina
    "Buenos_Aires_AR": {
        "name": "Port of Buenos Aires, Argentina",
        "bbox": [[-34.8, -58.6], [-34.4, -58.2]],
        "region": "Southern_Brazil_Atlantic"
    },

    # Uruguay
    "Montevideo_UY": {
        "name": "Port of Montevideo, Uruguay",
        "bbox": [[-35.0, -56.4], [-34.8, -56.1]],
        "region": "Southern_Brazil_Atlantic"
    },
}


def get_all_bounding_boxes():
    """
    Returns a list of all bounding boxes for AISstream API subscription.
    Includes both large maritime regions and specific ports.
    Format: [[south_lat, west_lon], [north_lat, east_lon]]
    """
    boxes = []

    # Add all maritime regions (large coverage areas)
    for region in MARITIME_REGIONS.values():
        boxes.append(region["bbox"])

    # Add major ports for detailed tracking
    # Note: These overlap with regions but provide granular port-level data
    for port in MAJOR_PORTS.values():
        boxes.append(port["bbox"])

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

    # Check if in a specific port (priority check)
    for port_id, port_data in MAJOR_PORTS.items():
        bbox = port_data["bbox"]
        if (bbox[0][0] <= lat <= bbox[1][0] and
            bbox[0][1] <= lon <= bbox[1][1]):
            location_info["port"] = port_data["name"]
            location_info["in_port"] = True
            location_info["region"] = port_data.get("region")
            return location_info

    # Check if in a maritime region
    for region_id, region_data in MARITIME_REGIONS.items():
        bbox = region_data["bbox"]
        if (bbox[0][0] <= lat <= bbox[1][0] and
            bbox[0][1] <= lon <= bbox[1][1]):
            location_info["region"] = region_data["name"]
            location_info["in_port"] = False
            return location_info

    return location_info


def get_port_by_coordinates(lat, lon):
    """
    Find which port a vessel is near based on coordinates.
    Legacy function for backward compatibility.
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
