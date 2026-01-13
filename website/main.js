// ===== MAP SETUP =====

// Definition Rijksdriehoekstelsel (EPSG:28992)
let res = [3440.640, 1720.320, 860.160, 430.080, 215.040, 107.520, 53.760, 26.880, 13.440, 6.720, 3.360, 1.680, 0.840, 0.420, 0.210, 0.105];
let map = L.map('map-canvas', {
  continuousWorld: true,
  crs: new L.Proj.CRS('EPSG:28992', '+proj=sterea +lat_0=52.15616055555555 +lon_0=5.38763888888889 +k=0.9999079 +x_0=155000 +y_0=463000 +ellps=bessel +units=m +towgs84=565.2369,50.0087,465.658,-0.406857330322398,0.350732676542563,-1.8703473836068,4.0812 +no_defs', {
    //transformation: L.Transformation(-1, -1, 0, 0),
    resolutions: res,
    origin: [-285401.920, 903401.920],
    bounds: L.bounds([-285401.920, 903401.920], [595401.920, 22598.080])
  }),
  layers: [],
  center: [52.010, 4.36744],
  zoom: 9,

});
map.attributionControl.setPrefix('');

L.DomEvent.disableClickPropagation(
  document.querySelector('.control-panel')
);

// BRT - (Base Registry Topography) BaseMap PDOK:
let options = { maxZoom: 14, attribution: 'Map data: <a href="http://www.pdok.nl">BRT Achtergrondkaart</a>' }
let basemap_pdok = new L.tileLayer('https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0/standaard/EPSG:28992/{z}/{x}/{y}.png', options);

basemap_pdok.getAttribution = function () {
  return 'BRT Background Map <a href="http://www.kadaster.nl">Kadaster</a>.';
}
basemap_pdok.addTo(map);

// To group the base layers (background) and make the ToC widget
let baseLayers = {
  "Topographical map": basemap_pdok
};
let toc = L.control.layers(baseLayers).addTo(map);


// ===== BUILDING VISUALIZATION =====

// Layer to hold building geometries
let buildingsLayer = L.layerGroup().addTo(map);

// VERSION 1: Load single test building
async function loadTestBuilding() {
    const testPandId = '0503100000032914';
    const apiUrl = `http://127.0.0.1:8000/collections/panden/items/${testPandId}`;

    try {
        console.log('Loading test building from:', apiUrl);
        const response = await fetch(apiUrl);

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        console.log('Test building data:', data);

        // Add the building to the map
        displayBuilding(data);

    } catch (error) {
        console.error('Failed to load test building:', error);
    }
}

//// VERSION 2: Load buildings in visible viewport
//async function loadBuildingsInView() {
//    // Get visible map bounds
//    const bounds = getVisibleBounds();
//
//    // Build API URL with bbox filter
//    const apiUrl = `http://127.0.0.1:8000/bbox?minx=${bounds.xmin}&miny=${bounds.ymin}&maxx=${bounds.xmax}&maxy=${bounds.ymax}`;
//
//    try {
//        console.log('Loading buildings in viewport from:', apiUrl);
//        const response = await fetch(apiUrl);
//
//        if (!response.ok) {
//            throw new Error(`API error: ${response.status}`);
//        }
//
//        const data = await response.json();
//        console.log(`Loaded ${data.features ? data.features.length : 0} buildings`);
//
//        // Clear existing buildings
//        buildingsLayer.clearLayers();
//
//        // Add each building to the map
//        if (data.features && data.features.length > 0) {
//            data.features.forEach(feature => {
//                displayBuilding(feature);
//            });
//        }
//
//    } catch (error) {
//        console.error('Failed to load buildings in viewport:', error);
//    }
//}

// Function: Display a single building on the map
function displayBuilding(feature) {
    // Check if feature has geometry
    if (!feature.geometry || !feature.geometry.coordinates) {
        console.warn('Building has no geometry:', feature);
        return;
    }

    // Convert GeoJSON to Leaflet layer
    let buildingLayer = L.geoJSON(feature, {
        style: {
            color: '#ef4444',        // Red outline
            weight: 2,               // Line thickness
            fillColor: '#fca5a5',    // Light red fill
            fillOpacity: 0.4         // Semi-transparent
        },
//        // Handle coordinate conversion if needed
//        coordsToLatLng: function(coords) {
//            // If your API returns RD coordinates, convert them
//            // Assuming API returns WGS84 (standard GeoJSON)
//            return L.latLng(coords[1], coords[0]);
//        },
        onEachFeature: function(feature, layer) {
            // Add popup with building info
            if (feature.properties) {
                let popupContent = '<div style="font-size: 0.875rem;">';
                popupContent += `<strong>Building ID:</strong> ${feature.id || 'N/A'}<br>`;

                // Add other properties
                for (let key in feature.properties) {
                    popupContent += `<strong>${key}:</strong> ${feature.properties[key]}<br>`;
                }

                popupContent += '</div>';
                layer.bindPopup(popupContent);
            }
        }
    });

    // Add to buildings layer
    buildingLayer.addTo(buildingsLayer);
}


// Load test building on page load (VERSION 1 - for testing)
// Comment this out when VERSION 2 is ready
loadTestBuilding();

// VERSION 2: Load buildings when map moves/zooms
// Uncomment these lines when your bbox API endpoint is ready:
/*
map.on('moveend', loadBuildingsInView);  // Reload when map stops moving
map.on('zoomend', loadBuildingsInView);  // Reload when zoom changes
loadBuildingsInView();  // Initial load
*/


// Register a geocoder to the map app
register_geocoder = function (mapInstance) {
  let polygon = null;

  function clear() {
    if (polygon !== null) {
      mapInstance.removeLayer(polygon);
    }
  }

  var geocoder = L.Control.geocoder({
    defaultMarkGeocode: false
  })
    .on('markgeocode', function (e) {
      clear()
      var bbox = e.geocode.bbox;
      polygon = L.polygon([
        bbox.getSouthEast(),
        bbox.getNorthEast(),
        bbox.getNorthWest(),
        bbox.getSouthWest()
      ]);
      mapInstance.addLayer(polygon);
      mapInstance.fitBounds(polygon.getBounds());
      setTimeout(clear, 2500);
    })
    .addTo(mapInstance);
  return geocoder;
}

register_geocoder(map)


// ===== BOUNDING BOX DRAWING =====

// Variables to store state
let isDrawing = false;           // Are we currently drawing?
let firstPoint = null;           // First corner clicked
let secondPoint = null;          // Second corner clicked
let currentRectangle = null;     // The rectangle shape on the map
let tempMarker = null;           // Temporary marker for first point
let currentBboxCoords = null;    // Store current bbox coordinates for download

// Function: Toggle panel open/closed
function togglePanel() {
    let panel = document.getElementById('panel-content');
    panel.classList.toggle('open');
}

// Function: Start drawing mode
function startDrawing() {
    // Clear any existing box first
    clearBoundingBox();

    // Enable drawing mode
    isDrawing = true;

    // Update button states
    document.getElementById('draw-btn').disabled = true;
    document.getElementById('draw-btn').textContent = 'Click first corner...';

    // Change cursor to crosshair
    document.getElementById('map-canvas').style.cursor = 'crosshair';

    // Listen for clicks on the map
    map.on('click', onMapClick);
}

// Function: Handle map clicks while drawing
function onMapClick(e) {
    if (!isDrawing) return;

    if (firstPoint === null) {
        // FIRST CLICK - store first corner
        firstPoint = e.latlng;

        // Add a temporary marker to show where we clicked
        tempMarker = L.circleMarker(firstPoint, {
            radius: 5,
            color: '#2563eb',
            fillColor: '#2563eb',
            fillOpacity: 0.5
        }).addTo(map);

        // Update button text
        document.getElementById('draw-btn').textContent = 'Click second corner...';

    } else {
        // SECOND CLICK - store second corner and draw rectangle
        secondPoint = e.latlng;

        // Remove temporary marker
        if (tempMarker) {
            map.removeLayer(tempMarker);
            tempMarker = null;
        }

        // Draw the rectangle
        drawRectangle(firstPoint, secondPoint);

        // Convert to RD coordinates and display
        displayCoordinates(firstPoint, secondPoint);

        // Stop drawing mode
        isDrawing = false;
        document.getElementById('map-canvas').style.cursor = '';
        document.getElementById('draw-btn').disabled = false;
        document.getElementById('draw-btn').textContent = 'Draw Bounding Box';
        document.getElementById('clear-btn').disabled = false;

        // Stop listening for clicks
        map.off('click', onMapClick);
    }
}

// Function: Draw the rectangle on the map
function drawRectangle(point1, point2) {
    // Create a rectangle between the two points
    let bounds = [
    [point1.lat, point1.lng],  // First corner you clicked
    [point2.lat, point2.lng]   // Second corner you clicked
];

    currentRectangle = L.rectangle(bounds, {
        color: '#2563eb',      // Blue outline
        weight: 3,              // Line thickness
        fillColor: '#2563eb',   // Blue fill
        fillOpacity: 0.1        // Transparent fill
    }).addTo(map);
}

// Function: Convert coordinates and display them
function displayCoordinates(point1, point2) {
    // Convert lat/lng to RD coordinates (EPSG:28992)
    // Leaflet stores coordinates as [lat, lng] but proj4 needs [lng, lat]

    let rdPoint1 = proj4('EPSG:4326', 'EPSG:28992', [point1.lng, point1.lat]);
    let rdPoint2 = proj4('EPSG:4326', 'EPSG:28992', [point2.lng, point2.lat]);

    // Calculate min and max values (because user can click in any order)
    let xmin = Math.min(rdPoint1[0], rdPoint2[0]);
    let xmax = Math.max(rdPoint1[0], rdPoint2[0]);
    let ymin = Math.min(rdPoint1[1], rdPoint2[1]);
    let ymax = Math.max(rdPoint1[1], rdPoint2[1]);

    // Round to 2 decimal places for cleaner display
    xmin = Math.round(xmin * 100) / 100;
    ymin = Math.round(ymin * 100) / 100;
    xmax = Math.round(xmax * 100) / 100;
    ymax = Math.round(ymax * 100) / 100;

    // Store for download function
    currentBboxCoords = { xmin, ymin, xmax, ymax };

    // Update the display
    document.getElementById('xmin').textContent = xmin;
    document.getElementById('ymin').textContent = ymin;
    document.getElementById('xmax').textContent = xmax;
    document.getElementById('ymax').textContent = ymax;

    // Show the coordinates box
    document.getElementById('coordinates').style.display = 'block';

    // Log to console (useful for testing your API)
    console.log('Bounding Box (RD New):');
    console.log(`xmin: ${xmin}, ymin: ${ymin}, xmax: ${xmax}, ymax: ${ymax}`);
    console.log(`API format: bbox=${xmin},${ymin},${xmax},${ymax}`);
}

// Function: Clear the bounding box
function clearBoundingBox() {
    // Remove rectangle from map
    if (currentRectangle) {
        map.removeLayer(currentRectangle);
        currentRectangle = null;
    }

    // Remove temporary marker if exists
    if (tempMarker) {
        map.removeLayer(tempMarker);
        tempMarker = null;
    }

    // Reset state
    firstPoint = null;
    secondPoint = null;
    isDrawing = false;

    // Update UI
    document.getElementById('coordinates').style.display = 'none';
    document.getElementById('clear-btn').disabled = true;
    document.getElementById('draw-btn').disabled = false;
    document.getElementById('draw-btn').textContent = 'Draw Bounding Box';
    document.getElementById('map-canvas').style.cursor = '';

    // Clear bbox from download panel
    document.getElementById('bbox-display').value = '';
    currentBboxCoords = null;

    // Stop listening for clicks
    map.off('click', onMapClick);
}


// ===== DOWNLOAD FUNCTIONALITY =====

// Function: Toggle download panel open/closed
function toggleDownloadPanel() {
    let panel = document.getElementById('download-panel-content');
    panel.classList.toggle('open');
}

// Function: Use the drawn bounding box for download
function useBboxForDownload() {
    if (!currentBboxCoords) {
        alert('Please draw a bounding box first!');
        return;
    }

    // Display the bbox coordinates in the input field
    let bboxText = `${currentBboxCoords.xmin}, ${currentBboxCoords.ymin}, ${currentBboxCoords.xmax}, ${currentBboxCoords.ymax}`;
    document.getElementById('bbox-display').value = bboxText;
}

// Function: Get current visible map bounds as bbox
function getVisibleBounds() {
    // Get the current map view bounds
    let bounds = map.getBounds();
    let sw = bounds.getSouthWest(); // Southwest corner
    let ne = bounds.getNorthEast(); // Northeast corner

    // Convert to RD coordinates
    let rdSW = proj4('EPSG:4326', 'EPSG:28992', [sw.lng, sw.lat]);
    let rdNE = proj4('EPSG:4326', 'EPSG:28992', [ne.lng, ne.lat]);

    return {
        xmin: Math.round(rdSW[0] * 100) / 100,
        ymin: Math.round(rdSW[1] * 100) / 100,
        xmax: Math.round(rdNE[0] * 100) / 100,
        ymax: Math.round(rdNE[1] * 100) / 100
    };
}

// Function: Download GeoJSON with filters
async function downloadGeoJSON() {
    // Get filter values
    let gemeente = document.getElementById('gemeente-input').value.trim();
    let postcode = document.getElementById('postcode-input').value.trim();
    let bboxInput = document.getElementById('bbox-display').value.trim();

    // Determine which bbox to use
    let bbox;
    if (bboxInput) {
        // Use the drawn bounding box
        bbox = currentBboxCoords;
    } else {
        // Use visible map area as default
        bbox = getVisibleBounds();
        console.log('No filters specified, using visible map area');
    }

    // Build API URL
    let apiUrl = `$http://127.0.0.1:8000/collections/panden/bbox?minx=${bbox.xmin}&miny=${bbox.ymin}&maxx=${bbox.xmax}&maxy=${bbox.ymax}`;

    // Add gemeente filter if provided
    if (gemeente) {
        apiUrl += `&gemeente=${encodeURIComponent(gemeente)}`;
    }

    // Add postcode filter if provided
    if (postcode) {
        apiUrl += `&postcode=${encodeURIComponent(postcode)}`;
    }

    console.log('Downloading from:', apiUrl);

    try {
        // Fetch data from API
        const response = await fetch(apiUrl);

        if (!response.ok) {
            throw new Error(`API error: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();

        // Convert to GeoJSON string
        const geojsonString = JSON.stringify(data, null, 2);

        // Create download link
        const blob = new Blob([geojsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'bag_data.geojson';

        // Trigger download
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        console.log('Download complete!');
    } catch (error) {
        console.error('Download failed:', error);
        alert(`Download failed: ${error.message}\n\nMake sure your API is running on $http://127.0.0.1:8000/collections/panden/items`);
    }
}