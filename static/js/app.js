// Optimized real-time vessel tracking application
class VesselTracker {
    constructor() {
        this.vessels = new Map();
        this.markers = new Map();
        this.selectedVesselMMSI = null;
        this.markerCluster = null;
        this.updateStats = {
            count: 0,
            lastReset: Date.now()
        };

        // Performance optimization: debounce list updates
        this.updateListDebounced = this.debounce(this.updateVesselList.bind(this), 500);

        this.initMap();
        this.initSocketIO();
        this.initEventListeners();
        this.startStatsMonitor();
    }

    initMap() {
        // Initialize Leaflet map centered on LATAM
        this.map = L.map('map').setView([-15, -60], 4);

        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(this.map);

        // Initialize marker clustering with zoom-aware dynamic clustering
        // Optimized for coastal AIS coverage (921+ vessels)
        this.markerCluster = L.markerClusterGroup({
            chunkedLoading: true,
            chunkInterval: 200,
            chunkDelay: 50,
            maxClusterRadius: this.getClusterRadiusForZoom(4),  // Dynamic radius
            disableClusteringAtZoom: 11,  // Show all individual vessels at port detail level
            spiderfyOnMaxZoom: true,
            spiderfyDistanceMultiplier: 2,  // Better vessel separation on click
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true,
            removeOutsideVisibleBounds: true,  // Performance: remove markers outside viewport
            iconCreateFunction: this.createClusterIcon.bind(this)  // Custom cluster icons
        });
        this.map.addLayer(this.markerCluster);

        // Update cluster radius dynamically on zoom
        this.map.on('zoomend', () => {
            const zoom = this.map.getZoom();
            const newRadius = this.getClusterRadiusForZoom(zoom);

            // Note: Leaflet doesn't support runtime radius changes
            // This is for future reference if we implement multi-layer clustering
            this.currentZoom = zoom;
        });

        // Define status color scheme (matching MarineTraffic convention)
        this.statusColors = {
            'underway': '#22c55e',    // Green - vessel is moving
            'anchored': '#3b82f6',    // Blue - at anchor
            'moored': '#ef4444',      // Red - moored/stopped
            'restricted': '#eab308',  // Yellow - restricted maneuverability
            'special': '#a855f7',     // Purple - fishing/special ops
            'unknown': '#6b7280'      // Gray - no status
        };

        // Status symbols (emojis)
        this.statusSymbols = {
            'underway': '🚢',
            'anchored': '⚓',
            'moored': '🔴',
            'restricted': '⚠️',
            'special': '🎣',
            'unknown': '❓'
        };
    }

    /**
     * Get optimal cluster radius for given zoom level
     * @param {number} zoom - Current map zoom level
     * @returns {number} Cluster radius in pixels
     */
    getClusterRadiusForZoom(zoom) {
        if (zoom <= 4) return 80;      // Continental view - aggressive clustering
        if (zoom <= 7) return 60;      // Regional view - moderate clustering
        if (zoom <= 9) return 40;      // Coastal view - light clustering
        return 20;                     // Detail view - minimal clustering
    }

    /**
     * Create custom cluster icon based on vessel composition
     * @param {L.MarkerCluster} cluster - Cluster object containing child markers
     * @returns {L.DivIcon} Custom cluster icon
     */
    createClusterIcon(cluster) {
        const count = cluster.getChildCount();
        const markers = cluster.getAllChildMarkers();

        // Analyze vessel statuses in cluster
        const statusCounts = {
            underway: 0,
            anchored: 0,
            moored: 0,
            restricted: 0,
            special: 0,
            unknown: 0
        };

        markers.forEach(marker => {
            // Get vessel data from marker (stored when marker was created)
            const mmsi = marker.mmsi;
            if (mmsi && this.vessels.has(mmsi)) {
                const vessel = this.vessels.get(mmsi);
                const status = vessel.status_category || 'unknown';
                if (statusCounts.hasOwnProperty(status)) {
                    statusCounts[status]++;
                }
            }
        });

        // Determine dominant status
        let dominantStatus = 'unknown';
        let maxCount = 0;
        for (const [status, statusCount] of Object.entries(statusCounts)) {
            if (statusCount > maxCount) {
                maxCount = statusCount;
                dominantStatus = status;
            }
        }

        // Determine cluster size based on vessel count
        let size, fontSize, borderWidth, className;
        if (count < 10) {
            size = 40;
            fontSize = 14;
            borderWidth = 2;
            className = 'marker-cluster-small';
        } else if (count < 50) {
            size = 50;
            fontSize = 16;
            borderWidth = 3;
            className = 'marker-cluster-medium';
        } else if (count < 100) {
            size = 60;
            fontSize = 18;
            borderWidth = 3;
            className = 'marker-cluster-large';
        } else {
            size = 70;
            fontSize = 20;
            borderWidth = 4;
            className = 'marker-cluster-mega';
        }

        // Get color for dominant status
        const color = this.statusColors[dominantStatus] || this.statusColors.unknown;
        const symbol = this.statusSymbols[dominantStatus] || this.statusSymbols.unknown;

        // Create custom HTML for cluster
        const html = `
            <div class="custom-cluster ${className}" style="
                width: ${size}px;
                height: ${size}px;
                background: linear-gradient(135deg, ${color} 0%, ${this.adjustColor(color, -20)} 100%);
                border: ${borderWidth}px solid rgba(255, 255, 255, 0.95);
                border-radius: 50%;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3), inset 0 1px 3px rgba(255, 255, 255, 0.3);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
                line-height: 1;
            ">
                <div style="font-size: ${fontSize}px; text-shadow: 0 1px 2px rgba(0,0,0,0.5);">
                    ${count >= 100 ? count + '+' : count}
                </div>
                <div style="font-size: ${Math.max(10, size / 6)}px; margin-top: 2px; opacity: 0.9;">
                    ${symbol}
                </div>
            </div>
        `;

        return L.divIcon({
            html: html,
            className: 'custom-cluster-icon',
            iconSize: [size, size],
            iconAnchor: [size / 2, size / 2]
        });
    }

    /**
     * Adjust color brightness
     * @param {string} color - Hex color
     * @param {number} amount - Amount to adjust (-255 to 255)
     * @returns {string} Adjusted hex color
     */
    adjustColor(color, amount) {
        const clamp = (val) => Math.min(255, Math.max(0, val));
        const num = parseInt(color.slice(1), 16);
        const r = clamp((num >> 16) + amount);
        const g = clamp(((num >> 8) & 0x00FF) + amount);
        const b = clamp((num & 0x0000FF) + amount);
        return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0');
    }

    /**
     * Create a directional vessel marker icon
     * @param {number} heading - Vessel heading in degrees (0-360)
     * @param {string} statusCategory - Status category (underway, anchored, moored, etc.)
     * @param {boolean} isSelected - Whether this vessel is selected
     * @returns {L.DivIcon} Leaflet DivIcon with rotated triangle
     */
    createVesselIcon(heading, statusCategory = 'unknown', isSelected = false) {
        const color = this.statusColors[statusCategory] || this.statusColors.unknown;
        const size = isSelected ? 24 : 18; // Larger when selected
        const strokeWidth = isSelected ? 3 : 2;
        const rotation = heading || 0;

        // Create SVG triangle pointing up (north), will be rotated based on heading
        const svg = `
            <svg width="${size}" height="${size}" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"
                 style="transform: rotate(${rotation}deg); filter: drop-shadow(0 2px 4px rgba(0,0,0,0.4));">
                <path d="M12 2 L22 20 L12 17 L2 20 Z"
                      fill="${color}"
                      stroke="${isSelected ? '#ffffff' : 'rgba(255,255,255,0.9)'}"
                      stroke-width="${strokeWidth}"
                      stroke-linejoin="round"/>
            </svg>
        `;

        return L.divIcon({
            className: 'vessel-marker-icon',
            html: svg,
            iconSize: [size, size],
            iconAnchor: [size / 2, size / 2],
            popupAnchor: [0, -size / 2]
        });
    }

    initSocketIO() {
        // Connect to SocketIO server
        this.socket = io();

        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.updateConnectionStatus(true);
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.updateConnectionStatus(false);
        });

        // Handle initial vessel data
        this.socket.on('initial_vessels', (vessels) => {
            console.log('Received initial vessels:', vessels.length);

            // Debug: show sample vessels
            if (vessels.length > 0) {
                console.log('Sample vessel data:', vessels.slice(0, 3));

                // Count vessels with position data
                const withPosition = vessels.filter(v => v.latitude != null && v.longitude != null);
                console.log(`Vessels with position: ${withPosition.length} / ${vessels.length}`);
            }

            this.processBatchUpdate(vessels);
        });

        // Handle batch updates (new optimized method)
        this.socket.on('vessel_batch_update', (data) => {
            if (this.vessels.size < 50) {
                console.log(`📦 Batch update: ${data.vessels.length} vessels (total: ${this.vessels.size})`);
            }
            this.processBatchUpdate(data.vessels);
            this.trackUpdateRate(data.vessels.length);
        });

        // Keep legacy single update for backward compatibility
        this.socket.on('vessel_update', (vessel) => {
            this.updateVessel(vessel);
        });

        // Handle stats updates
        this.socket.on('stats_update', (stats) => {
            console.log('Server stats:', stats);
        });
    }

    initEventListeners() {
        // Search functionality with debouncing
        const searchInput = document.getElementById('search-vessel');
        searchInput.addEventListener('input', this.debounce((e) => {
            this.filterVessels(e.target.value);
        }, 300));
    }

    startStatsMonitor() {
        // Update stats display every second
        setInterval(() => {
            const elapsed = (Date.now() - this.updateStats.lastReset) / 1000;
            const rate = (this.updateStats.count / elapsed).toFixed(1);
            document.getElementById('update-rate').textContent = `Updates: ${rate}/s`;

            // Reset stats every 10 seconds
            if (elapsed >= 10) {
                this.updateStats.count = 0;
                this.updateStats.lastReset = Date.now();
            }
        }, 1000);

        // Request server stats every 30 seconds
        setInterval(() => {
            this.socket.emit('request_stats');
        }, 30000);
    }

    trackUpdateRate(count) {
        this.updateStats.count += count;
    }

    processBatchUpdate(vessels) {
        // Process multiple vessel updates efficiently
        const startTime = performance.now();

        let markersToUpdate = [];
        let vesselsWithoutPosition = 0;

        vessels.forEach(vessel => {
            const mmsi = vessel.mmsi;

            // Store vessel data
            this.vessels.set(mmsi, vessel);

            // Collect markers to update - check for valid numeric coordinates
            const lat = vessel.latitude;
            const lon = vessel.longitude;

            if (lat != null && lon != null &&
                typeof lat === 'number' && typeof lon === 'number' &&
                !isNaN(lat) && !isNaN(lon) &&
                lat >= -90 && lat <= 90 &&
                lon >= -180 && lon <= 180) {
                markersToUpdate.push(vessel);
            } else {
                vesselsWithoutPosition++;
            }
        });

        if (vesselsWithoutPosition > 0 && vessels.length <= 20) {
            console.log(`⚠️ ${vesselsWithoutPosition} vessels without valid position data`);
        }

        // Batch update markers
        this.updateMarkersBatch(markersToUpdate);

        // Debounced list update to avoid excessive re-renders
        this.updateListDebounced();

        const duration = performance.now() - startTime;
        if (duration > 100) {
            console.warn(`Batch update took ${duration.toFixed(2)}ms for ${vessels.length} vessels`);
        }
    }

    updateVessel(vessel) {
        const mmsi = vessel.mmsi;
        this.vessels.set(mmsi, vessel);

        if (vessel.latitude && vessel.longitude) {
            this.updateMarker(vessel);
        }

        this.updateListDebounced();
    }

    updateMarkersBatch(vessels) {
        // Efficiently update multiple markers at once
        vessels.forEach(vessel => {
            const mmsi = vessel.mmsi;
            const statusCategory = vessel.status_category || 'unknown';
            const heading = vessel.heading || 0;
            const isSelected = this.selectedVesselMMSI === mmsi;

            if (this.markers.has(mmsi)) {
                // Update existing marker
                const marker = this.markers.get(mmsi);
                const lat = vessel.latitude;
                const lon = vessel.longitude;

                // Update position
                marker.setLatLng([lat, lon]);

                // Update icon (heading and status might have changed)
                const newIcon = this.createVesselIcon(heading, statusCategory, isSelected);
                marker.setIcon(newIcon);

                // Update popup content
                marker.getPopup().setContent(this.createPopupContent(vessel));
            } else {
                // Create new marker with directional icon
                const lat = vessel.latitude;
                const lon = vessel.longitude;
                const icon = this.createVesselIcon(heading, statusCategory, isSelected);

                const marker = L.marker([lat, lon], { icon: icon })
                    .bindPopup(this.createPopupContent(vessel));

                // Store MMSI in marker for cluster icon generation
                marker.mmsi = mmsi;

                marker.on('click', () => {
                    this.selectVessel(mmsi);
                });

                this.markers.set(mmsi, marker);
                this.markerCluster.addLayer(marker);
            }
        });
    }

    updateMarker(vessel) {
        const mmsi = vessel.mmsi;
        const lat = vessel.latitude;
        const lon = vessel.longitude;
        const statusCategory = vessel.status_category || 'unknown';
        const heading = vessel.heading || 0;
        const isSelected = this.selectedVesselMMSI === mmsi;

        if (this.markers.has(mmsi)) {
            // Update existing marker
            const marker = this.markers.get(mmsi);
            marker.setLatLng([lat, lon]);

            // Update icon with current heading and status
            const newIcon = this.createVesselIcon(heading, statusCategory, isSelected);
            marker.setIcon(newIcon);

            marker.getPopup().setContent(this.createPopupContent(vessel));
        } else {
            // Create new marker with directional icon
            const icon = this.createVesselIcon(heading, statusCategory, isSelected);
            const marker = L.marker([lat, lon], { icon: icon })
                .bindPopup(this.createPopupContent(vessel));

            // Store MMSI in marker for cluster icon generation
            marker.mmsi = mmsi;

            marker.on('click', () => {
                this.selectVessel(mmsi);
            });

            this.markers.set(mmsi, marker);
            this.markerCluster.addLayer(marker);
        }
    }

    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connection-status');
        if (connected) {
            statusElement.textContent = 'Connected';
            statusElement.className = 'status-indicator connected';
        } else {
            statusElement.textContent = 'Disconnected';
            statusElement.className = 'status-indicator disconnected';
        }
    }

    createPopupContent(vessel) {
        const name = vessel.name || 'Unknown';
        const type = vessel.vessel_type || 'Unknown';
        const destination = vessel.destination || 'Unknown';
        const speed = vessel.speed !== undefined ? vessel.speed.toFixed(1) : 'N/A';
        const heading = vessel.heading !== undefined ? vessel.heading.toFixed(0) : 'N/A';
        const nearbyPort = vessel.nearby_port || 'N/A';

        // Get status information
        const statusCategory = vessel.status_category || 'unknown';
        const statusName = vessel.navigational_status || 'Unknown';
        const statusColor = this.statusColors[statusCategory] || this.statusColors.unknown;
        const statusSymbol = this.statusSymbols[statusCategory] || this.statusSymbols.unknown;

        return `
            <div class="vessel-popup">
                <div class="popup-header">
                    <div class="popup-name">${name}</div>
                    <div class="popup-status-badge" style="background-color: ${statusColor};">
                        ${statusSymbol}
                    </div>
                </div>
                <div class="popup-info">
                    <strong>MMSI:</strong> ${vessel.mmsi}<br>
                    <strong>Status:</strong> <span style="color: ${statusColor}; font-weight: 600;">${statusName}</span><br>
                    <strong>Type:</strong> ${type}<br>
                    <strong>Destination:</strong> ${destination}<br>
                    <strong>Speed:</strong> ${speed} knots<br>
                    <strong>Heading:</strong> ${heading}°<br>
                    <strong>Location:</strong> ${nearbyPort}
                </div>
            </div>
        `;
    }

    updateVesselList() {
        const vesselListContainer = document.getElementById('vessel-list');
        const searchValue = document.getElementById('search-vessel').value;

        if (this.vessels.size === 0) {
            vesselListContainer.innerHTML = '<div class="no-vessels">Waiting for vessel data...</div>';
            return;
        }

        // Update vessel count
        document.getElementById('vessel-count').textContent = `Vessels: ${this.vessels.size}`;

        // Sort vessels by name
        const sortedVessels = Array.from(this.vessels.values()).sort((a, b) => {
            const nameA = (a.name || 'Unknown').toLowerCase();
            const nameB = (b.name || 'Unknown').toLowerCase();
            return nameA.localeCompare(nameB);
        });

        // Filter vessels if search is active
        const filteredVessels = searchValue
            ? sortedVessels.filter(v => this.matchesSearch(v, searchValue))
            : sortedVessels;

        // Limit to first 150 vessels for performance (increased from 100 for better coverage)
        const displayVessels = filteredVessels.slice(0, 150);
        const hasMore = filteredVessels.length > 150;

        // Render vessel cards
        let html = displayVessels.map(v => this.createVesselCard(v)).join('');

        if (hasMore) {
            html += `<div class="more-vessels">Showing 150 of ${filteredVessels.length} vessels. Use search to narrow results.</div>`;
        }

        vesselListContainer.innerHTML = html || '<div class="no-vessels">No vessels match your search</div>';

        // Add click listeners
        displayVessels.forEach(vessel => {
            const card = document.getElementById(`vessel-${vessel.mmsi}`);
            if (card) {
                card.addEventListener('click', () => {
                    this.selectVessel(vessel.mmsi);
                });
            }
        });
    }

    createVesselCard(vessel) {
        const name = vessel.name || 'Unknown';
        const type = vessel.vessel_type || 'Unknown';
        const destination = vessel.destination || 'Unknown';
        const speed = vessel.speed !== undefined ? vessel.speed.toFixed(1) : 'N/A';
        const lat = vessel.latitude !== undefined ? vessel.latitude.toFixed(4) : 'N/A';
        const lon = vessel.longitude !== undefined ? vessel.longitude.toFixed(4) : 'N/A';
        const location = vessel.nearby_port || 'Unknown';
        const isSelected = this.selectedVesselMMSI === vessel.mmsi;

        // Get status information
        const statusCategory = vessel.status_category || 'unknown';
        const statusName = vessel.navigational_status || 'Unknown';
        const statusColor = this.statusColors[statusCategory] || this.statusColors.unknown;
        const statusSymbol = this.statusSymbols[statusCategory] || this.statusSymbols.unknown;

        return `
            <div id="vessel-${vessel.mmsi}" class="vessel-card ${isSelected ? 'selected' : ''}">
                <div class="vessel-header">
                    <div class="vessel-name">${name}</div>
                    <div class="vessel-status-badge" style="background-color: ${statusColor};" title="${statusName}">
                        ${statusSymbol}
                    </div>
                </div>
                <div class="vessel-info">
                    <div class="vessel-info-row">
                        <span class="vessel-info-label">MMSI:</span>
                        <span>${vessel.mmsi}</span>
                    </div>
                    <div class="vessel-info-row">
                        <span class="vessel-info-label">Status:</span>
                        <span class="status-text" style="color: ${statusColor}; font-weight: 500;">${statusName}</span>
                    </div>
                    <div class="vessel-info-row">
                        <span class="vessel-info-label">Position:</span>
                        <span>${lat}, ${lon}</span>
                    </div>
                    <div class="vessel-info-row">
                        <span class="vessel-info-label">Speed:</span>
                        <span>${speed} knots</span>
                    </div>
                    <div class="vessel-info-row">
                        <span class="vessel-info-label">Destination:</span>
                        <span>${destination}</span>
                    </div>
                    <div class="vessel-info-row">
                        <span class="vessel-info-label">Location:</span>
                        <span style="font-size: 0.85em;">${location}</span>
                    </div>
                </div>
                <div class="vessel-type">${type}</div>
            </div>
        `;
    }

    matchesSearch(vessel, searchTerm) {
        const term = searchTerm.toLowerCase();
        const name = (vessel.name || '').toLowerCase();
        const mmsi = (vessel.mmsi || '').toString().toLowerCase();
        const destination = (vessel.destination || '').toLowerCase();
        const type = (vessel.vessel_type || '').toLowerCase();
        const location = (vessel.nearby_port || '').toLowerCase();

        return name.includes(term) ||
               mmsi.includes(term) ||
               destination.includes(term) ||
               type.includes(term) ||
               location.includes(term);
    }

    filterVessels() {
        this.updateVesselList();
    }

    selectVessel(mmsi) {
        const previousSelection = this.selectedVesselMMSI;
        this.selectedVesselMMSI = mmsi;
        const vessel = this.vessels.get(mmsi);

        if (vessel && vessel.latitude && vessel.longitude) {
            // Update previous marker to unselected state
            if (previousSelection && this.markers.has(previousSelection)) {
                const prevVessel = this.vessels.get(previousSelection);
                if (prevVessel) {
                    const prevMarker = this.markers.get(previousSelection);
                    const prevIcon = this.createVesselIcon(
                        prevVessel.heading || 0,
                        prevVessel.status_category || 'unknown',
                        false
                    );
                    prevMarker.setIcon(prevIcon);
                }
            }

            // Update selected marker to highlighted state
            const marker = this.markers.get(mmsi);
            if (marker) {
                // Update icon to show selected state (larger, thicker border)
                const selectedIcon = this.createVesselIcon(
                    vessel.heading || 0,
                    vessel.status_category || 'unknown',
                    true
                );
                marker.setIcon(selectedIcon);

                // Ensure marker is visible (handle clustering)
                // If marker is in a cluster, zoom in to uncluster it
                this.markerCluster.zoomToShowLayer(marker, () => {
                    // Center map on vessel with smooth animation
                    this.map.setView([vessel.latitude, vessel.longitude], Math.max(this.map.getZoom(), 10), {
                        animate: true,
                        duration: 0.5
                    });

                    // Open popup after zoom completes
                    setTimeout(() => {
                        marker.openPopup();
                    }, 300);
                });
            }
        }

        // Update vessel list to show selection
        this.updateVesselList();
    }

    // Utility: debounce function to limit execution rate
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize the application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing Optimized Vessel Tracker...');
    window.tracker = new VesselTracker();
});
