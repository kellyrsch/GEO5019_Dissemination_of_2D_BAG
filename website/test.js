//-- Cleaned up and adapted code written mostly by Claude.ai

// ===== CONFIGURATION =====
const API_BASE_URL = 'https://godzilla.bk.tudelft.nl/2dbagparquet/api';
const PND_PMTILES_URL = 'data/bag.pmtiles'; //should be pnd.pmtiles (bag just for testing)
const NL_PMTILES_URL = 'data/bag.pmtiles'; //should be nl.pmtiles

// ===== MAP SETUP (WEB MERCATOR / EPSG:3857) =====

const map = L.map('map-canvas', {
    center: [52.010, 4.36744],  // Delft
    zoom: 13,
    zoomControl: true
});

map.attributionControl.setPrefix('');

// ===== PROTOMAPS BASEMAP (WHITE STYLE) =====

const protomapsBasemap = protomapsL.leafletLayer({
    url: NL_PMTILES_URL,
    // For a white/light basemap style
    theme: 'greyscale'
});
protomapsBasemap.addTo(map);

// ===== PMTILES BUILDINGS LAYER =====

let protocol = new pmtiles.Protocol();
L.setProtocol(protocol);

const buildingsLayer = protomapsL.leafletLayer({
    url: PND_PMTILES_URL,
    paint_rules: [
        {
            dataLayer: 'naam',  // MUST match layer name in your PMTiles
            symbolizer: new protomapsL.PolygonSymbolizer({
                fill: '#60a5fa',
                opacity: 0.4,
                stroke: '#1e3a8a',
                width: 1
            })
        }
    ]
});

// Don't add by default - let user turn it on
// buildingsLayer.addTo(map);

// ===== BUILDING CLICK INTERACTION =====

// Add click handler to query PMTiles features
map.on('click', async function(e) {
    const latlng = e.latlng;
    const zoom = map.getZoom();

    try {
        // Query PMTiles at click point
        // Note: This requires accessing PMTiles data directly
        // For now, show coordinates
        console.log('Clicked building at:', latlng);

        // TODO: Implement proper PMTiles feature query
        // This would require:
        // 1. Getting the tile that contains this point
        // 2. Querying features in that tile
        // 3. Finding which feature was clicked

        L.popup()
            .setLatLng(latlng)
            .setContent(`
                <div style="font-size: 0.875rem;">
                    <strong>Building clicked</strong><br>
                    Lat: ${latlng.lat.toFixed(5)}<br>
                    Lng: ${latlng.lng.toFixed(5)}<br>
                    <br>
                    <em>Feature query coming soon...</em>
                </div>
            `)
            .openOn(map);

    } catch (error) {
        console.error('Error querying building:', error);
    }
});

// ===== LAYER CONTROL =====

const baseLayers = {
    'Protomaps Light': protomapsBasemap
};

const overlays = {
    'Buildings (PMTiles)': buildingsLayer
};

L.control.layers(baseLayers, overlays).addTo(map);

// ===== GEOCODER =====

L.Control.geocoder({
    defaultMarkGeocode: false
}).on('markgeocode', function(e) {
    const bbox = e.geocode.bbox;
    const polygon = L.polygon([
        bbox.getSouthEast(),
        bbox.getNorthEast(),
        bbox.getNorthWest(),
        bbox.getSouthWest()
    ]).addTo(map);

    map.fitBounds(polygon.getBounds());
    setTimeout(() => map.removeLayer(polygon), 2500);
}).addTo(map);

// Prevent clicks on control panels from triggering map clicks
L.DomEvent.disableClickPropagation(document.querySelector('.control-panel'));
L.DomEvent.disableClickPropagation(document.querySelector('.download-panel'));

// ===== BOUNDING BOX DRAWING =====

let isDrawing = false;
let firstPoint = null;
let secondPoint = null;
let currentRectangle = null;
let tempMarker = null;
let currentBboxCoords = null;

function togglePanel() {
    document.getElementById('panel-content').classList.toggle('open');
}

function startDrawing() {
    clearBoundingBox();
    isDrawing = true;

    document.getElementById('draw-btn').disabled = true;
    document.getElementById('draw-btn').textContent = 'Click first corner...';
    document.getElementById('map-canvas').style.cursor = 'crosshair';

    map.on('click', onMapClick);
}

function onMapClick(e) {
    if (!isDrawing) return;

    if (firstPoint === null) {
        firstPoint = e.latlng;

        tempMarker = L.circleMarker(firstPoint, {
            radius: 5,
            color: '#2563eb',
            fillColor: '#2563eb',
            fillOpacity: 0.5
        }).addTo(map);

        document.getElementById('draw-btn').textContent = 'Click second corner...';
    } else {
        secondPoint = e.latlng;

        if (tempMarker) {
            map.removeLayer(tempMarker);
            tempMarker = null;
        }

        drawRectangle(firstPoint, secondPoint);
        displayCoordinates(firstPoint, secondPoint);

        isDrawing = false;
        document.getElementById('map-canvas').style.cursor = '';
        document.getElementById('draw-btn').disabled = false;
        document.getElementById('draw-btn').textContent = 'Draw Bounding Box';
        document.getElementById('clear-btn').disabled = false;

        map.off('click', onMapClick);
    }
}

function drawRectangle(point1, point2) {
    const bounds = [[point1.lat, point1.lng], [point2.lat, point2.lng]];

    currentRectangle = L.rectangle(bounds, {
        color: '#2563eb',
        weight: 3,
        fillColor: '#2563eb',
        fillOpacity: 0.1
    }).addTo(map);
}

function displayCoordinates(point1, point2) {
    // Convert WGS84 to RD for API
    const rdPoint1 = proj4('EPSG:4326', 'EPSG:28992', [point1.lng, point1.lat]);
    const rdPoint2 = proj4('EPSG:4326', 'EPSG:28992', [point2.lng, point2.lat]);

    let xmin = Math.min(rdPoint1[0], rdPoint2[0]);
    let xmax = Math.max(rdPoint1[0], rdPoint2[0]);
    let ymin = Math.min(rdPoint1[1], rdPoint2[1]);
    let ymax = Math.max(rdPoint1[1], rdPoint2[1]);

    xmin = Math.round(xmin * 100) / 100;
    ymin = Math.round(ymin * 100) / 100;
    xmax = Math.round(xmax * 100) / 100;
    ymax = Math.round(ymax * 100) / 100;

    currentBboxCoords = { xmin, ymin, xmax, ymax };

    document.getElementById('xmin').textContent = xmin;
    document.getElementById('ymin').textContent = ymin;
    document.getElementById('xmax').textContent = xmax;
    document.getElementById('ymax').textContent = ymax;
    document.getElementById('coordinates').style.display = 'block';

    console.log('Bounding Box (RD):', currentBboxCoords);
}

function clearBoundingBox() {
    if (currentRectangle) {
        map.removeLayer(currentRectangle);
        currentRectangle = null;
    }

    if (tempMarker) {
        map.removeLayer(tempMarker);
        tempMarker = null;
    }

    firstPoint = null;
    secondPoint = null;
    isDrawing = false;

    document.getElementById('coordinates').style.display = 'none';
    document.getElementById('clear-btn').disabled = true;
    document.getElementById('draw-btn').disabled = false;
    document.getElementById('draw-btn').textContent = 'Draw Bounding Box';
    document.getElementById('map-canvas').style.cursor = '';
    document.getElementById('bbox-display').value = '';

    currentBboxCoords = null;
    map.off('click', onMapClick);
}

// ===== DOWNLOAD FUNCTIONALITY =====

function toggleDownloadPanel() {
    document.getElementById('download-panel-content').classList.toggle('open');
}

function useBboxForDownload() {
    if (!currentBboxCoords) {
        alert('Please draw a bounding box first!');
        return;
    }

    const bboxText = `${currentBboxCoords.xmin}, ${currentBboxCoords.ymin}, ${currentBboxCoords.xmax}, ${currentBboxCoords.ymax}`;
    document.getElementById('bbox-display').value = bboxText;
}

function getVisibleBounds() {
    const bounds = map.getBounds();
    const sw = bounds.getSouthWest();
    const ne = bounds.getNorthEast();

    const rdSW = proj4('EPSG:4326', 'EPSG:28992', [sw.lng, sw.lat]);
    const rdNE = proj4('EPSG:4326', 'EPSG:28992', [ne.lng, ne.lat]);

    return {
        xmin: Math.round(rdSW[0] * 100) / 100,
        ymin: Math.round(rdSW[1] * 100) / 100,
        xmax: Math.round(rdNE[0] * 100) / 100,
        ymax: Math.round(rdNE[1] * 100) / 100
    };
}

async function downloadPandenGeoJSON() {
    const gemeente = document.getElementById('gemeente-input').value.trim();
    const postcode = document.getElementById('postcode-input').value.trim();
    const bboxInput = document.getElementById('bbox-display').value.trim();

    let baseUrl = `{API_BASE_URL}/collections/panden/items?`;
    let hasFilters = false;

    if (gemeente) {
        baseUrl += `woonplaats=${encodeURIComponent(gemeente)}`;
        hasFilters = true;
    }

    if (postcode) {
        baseUrl += (hasFilters ? '&' : '') + `postcode_4=${encodeURIComponent(postcode)}`;
        hasFilters = true;
    }

    if (currentBboxCoords) {
        baseUrl += (hasFilters ? '&' : '') + `minx=${currentBboxCoords.xmin}&miny=${currentBboxCoords.ymin}&maxx=${currentBboxCoords.xmax}&maxy=${currentBboxCoords.ymax}`;
        hasFilters = true;
    }

    if (!hasFilters) {
        const bbox = getVisibleBounds();
        baseUrl += `minx=${bbox.xmin}&miny=${bbox.ymin}&maxx=${bbox.xmax}&maxy=${bbox.ymax}`;
    }

    console.log('Starting download from:', baseUrl);

    try {
        const allFeatures = await fetchAllPages(baseUrl);
        console.log(`Downloaded ${allFeatures.length} features`);

        const geojson = {
            type: "FeatureCollection",
            features: allFeatures
        };

        const geojsonString = JSON.stringify(geojson, null, 2);
        const blob = new Blob([geojsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'bag_panden.geojson';

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        alert(`Successfully downloaded ${allFeatures.length} panden!`);
    } catch (error) {
        console.error('Download failed:', error);
        alert(`Download failed: ${error.message}`);
    }
}

async function downloadVboGeoJSON() {
    const pandId = document.getElementById('pand-id-input').value.trim();

    if (!pandId) {
        alert('Please enter a Pand ID');
        return;
    }

    const baseUrl = `{API_BASE_URL}/collections/verblijfsobjecten/items?pandRef=${encodeURIComponent(pandId)}`;

    try {
        const allFeatures = await fetchAllPages(baseUrl);

        if (allFeatures.length === 0) {
            alert(`No verblijfsobjecten found for Pand ID: ${pandId}`);
            return;
        }

        const geojson = {
            type: "FeatureCollection",
            features: allFeatures
        };

        const geojsonString = JSON.stringify(geojson, null, 2);
        const blob = new Blob([geojsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `bag_vbo_${pandId}.geojson`;

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        alert(`Successfully downloaded ${allFeatures.length} verblijfsobjecten!`);
    } catch (error) {
        console.error('Download failed:', error);
        alert(`Download failed: ${error.message}`);
    }
}

async function fetchAllPages(baseUrl) {
    let allFeatures = [];
    let offset = 0;
    let limit = 500;
    let totalCount = null;

    while (true) {
        const pageUrl = `${baseUrl}&limit=${limit}&offset=${offset}`;
        console.log(`Fetching: offset=${offset}, limit=${limit}...`);

        try {
            const response = await fetch(pageUrl);

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            const data = await response.json();

            if (totalCount === null && data.total_count !== undefined) {
                totalCount = data.total_count;
                console.log(`Total count: ${totalCount}`);
            }

            if (data.features && data.features.length > 0) {
                allFeatures = allFeatures.concat(data.features);
                console.log(`Got ${data.features.length} features (total: ${allFeatures.length}/${totalCount || '?'})`);

                offset += limit;

                if (totalCount !== null && offset >= totalCount) {
                    break;
                }

                if (data.features.length < limit) {
                    break;
                }
            } else {
                break;
            }
        } catch (error) {
            console.error(`Error at offset ${offset}:`, error);
            throw error;
        }
    }

    return allFeatures;
}