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

        // Initialize marker clustering for better performance
        this.markerCluster = L.markerClusterGroup({
            chunkedLoading: true,
            chunkInterval: 200,
            chunkDelay: 50,
            maxClusterRadius: 50,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true
        });
        this.map.addLayer(this.markerCluster);

        // Custom ship icon
        this.shipIcon = L.divIcon({
            className: 'vessel-marker',
            html: '<div style="background: #667eea; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
            iconSize: [16, 16],
            iconAnchor: [8, 8]
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

            if (this.markers.has(mmsi)) {
                // Update existing marker
                const marker = this.markers.get(mmsi);
                const lat = vessel.latitude;
                const lon = vessel.longitude;
                marker.setLatLng([lat, lon]);
                marker.getPopup().setContent(this.createPopupContent(vessel));
            } else {
                // Create new marker
                const lat = vessel.latitude;
                const lon = vessel.longitude;
                const marker = L.marker([lat, lon], { icon: this.shipIcon })
                    .bindPopup(this.createPopupContent(vessel));

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

        if (this.markers.has(mmsi)) {
            // Update existing marker
            const marker = this.markers.get(mmsi);
            marker.setLatLng([lat, lon]);
            marker.getPopup().setContent(this.createPopupContent(vessel));
        } else {
            // Create new marker
            const marker = L.marker([lat, lon], { icon: this.shipIcon })
                .bindPopup(this.createPopupContent(vessel));

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

        return `
            <div class="vessel-popup">
                <div class="popup-name">${name}</div>
                <div class="popup-info">
                    <strong>MMSI:</strong> ${vessel.mmsi}<br>
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

        // Limit to first 100 vessels for performance (virtual scrolling would be better)
        const displayVessels = filteredVessels.slice(0, 100);
        const hasMore = filteredVessels.length > 100;

        // Render vessel cards
        let html = displayVessels.map(v => this.createVesselCard(v)).join('');

        if (hasMore) {
            html += `<div class="more-vessels">Showing 100 of ${filteredVessels.length} vessels. Use search to narrow results.</div>`;
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

        return `
            <div id="vessel-${vessel.mmsi}" class="vessel-card ${isSelected ? 'selected' : ''}">
                <div class="vessel-name">${name}</div>
                <div class="vessel-info">
                    <div class="vessel-info-row">
                        <span class="vessel-info-label">MMSI:</span>
                        <span>${vessel.mmsi}</span>
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
        this.selectedVesselMMSI = mmsi;
        const vessel = this.vessels.get(mmsi);

        if (vessel && vessel.latitude && vessel.longitude) {
            // Center map on vessel
            this.map.setView([vessel.latitude, vessel.longitude], 10);

            // Open marker popup
            const marker = this.markers.get(mmsi);
            if (marker) {
                marker.openPopup();
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
