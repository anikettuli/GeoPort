// Leaflet Map Manager with Modern Open Map Providers
let map = null;
let currentMarker = null;
let gpxLayer = null;
let tileLayers = {};
let currentTileLayer = null;

// Custom animated SVG pin icon
const createPinIcon = (isSimulating = false) => {
  const color = isSimulating ? "#059669" : "#2563eb";
  const pulseClass = isSimulating ? "sim-pulse" : "";

  return L.divIcon({
    className: "custom-map-pin-container",
    html: `
      <div class="custom-pin ${pulseClass}" style="position: relative; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center;">
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" fill="${color}" stroke="#ffffff" stroke-width="1.8"/>
          <circle cx="12" cy="9" r="3" fill="#ffffff"/>
        </svg>
      </div>
    `,
    iconSize: [34, 34],
    iconAnchor: [17, 34],
    popupAnchor: [0, -32],
  });
};

function initMap(initialLat = 37.774929, initialLng = -122.419418) {
  map = L.map("map", {
    center: [initialLat, initialLng],
    zoom: 14,
    zoomControl: false,
    attributionControl: true,
  });

  // Zoom control in bottom right
  L.control.zoom({ position: "bottomright" }).addTo(map);

  // Modern Tile Providers
  tileLayers = {
    cartoLight: L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap',
    }),
    cartoDark: L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap',
    }),
    osm: L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }),
    topo: L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
      maxZoom: 17,
      attribution: 'Map: &copy; <a href="https://opentopomap.org">OpenTopoMap</a>',
    }),
    satellite: L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 19,
      attribution: 'Tiles &copy; Esri',
    }),
  };

  // Set default tile layer according to current theme
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  currentTileLayer = isDark ? tileLayers.cartoDark : tileLayers.cartoLight;
  currentTileLayer.addTo(map);

  // Layer Control Switcher
  const baseLayers = {
    "CARTO Voyager (Light)": tileLayers.cartoLight,
    "CARTO Dark Matter (Dark)": tileLayers.cartoDark,
    "OpenStreetMap": tileLayers.osm,
    "OpenTopoMap (Topographic)": tileLayers.topo,
    "Satellite Imagery": tileLayers.satellite,
  };
  L.control.layers(baseLayers, null, { position: "topright" }).addTo(map);

  // Initial Marker
  currentMarker = L.marker([initialLat, initialLng], {
    icon: createPinIcon(false),
    draggable: true,
  }).addTo(map);

  // Marker Drag Event
  currentMarker.on("dragend", function (e) {
    const pos = currentMarker.getLatLng();
    updateCoordinateInputs(pos.lat, pos.lng);
  });

  // Map Click Event
  map.on("click", function (e) {
    setMarkerLocation(e.latlng.lat, e.latlng.lng);
  });

  updateCoordinateInputs(initialLat, initialLng);
  return map;
}

function setMarkerLocation(lat, lng, fly = false, isSimulating = false) {
  if (!map || !currentMarker) return;
  const targetLatLng = L.latLng(lat, lng);

  currentMarker.setLatLng(targetLatLng);
  currentMarker.setIcon(createPinIcon(isSimulating));
  updateCoordinateInputs(lat, lng);

  if (fly) {
    map.flyTo(targetLatLng, Math.max(map.getZoom(), 15), {
      duration: 1.2,
      easeLinearity: 0.25,
    });
  }
}

function updateCoordinateInputs(lat, lng) {
  const latInput = document.getElementById("inputLat");
  const lngInput = document.getElementById("inputLng");
  if (latInput) latInput.value = Number(lat).toFixed(6);
  if (lngInput) lngInput.value = Number(lng).toFixed(6);
}

function switchMapTheme(theme) {
  if (!map) return;
  const newLayer = theme === "dark" ? tileLayers.cartoDark : tileLayers.cartoLight;
  if (currentTileLayer !== newLayer) {
    map.removeLayer(currentTileLayer);
    currentTileLayer = newLayer;
    currentTileLayer.addTo(map);
  }
}

function renderGPXRoute(waypoints) {
  if (!map) return;
  if (gpxLayer) {
    map.removeLayer(gpxLayer);
  }
  const latLngs = waypoints.map((wp) => [wp.latitude, wp.longitude]);
  gpxLayer = L.polyline(latLngs, {
    color: "#2563eb",
    weight: 4,
    opacity: 0.8,
    dashArray: "6, 8",
  }).addTo(map);

  map.fitBounds(gpxLayer.getBounds(), { padding: [50, 50] });
}

function clearGPXRoute() {
  if (map && gpxLayer) {
    map.removeLayer(gpxLayer);
    gpxLayer = null;
  }
}
