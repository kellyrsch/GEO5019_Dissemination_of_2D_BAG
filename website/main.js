var map = L.map('map').setView([51.505, -0.09], 13);

//L.tileLayer('https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0/standaard/EPSG:28992/{z}/{x}/{y}.png', {
//    maxZoom: 19,
//    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
//}).addTo(map);

// BRT - (Base Registry Topography) BaseMap PDOK:
let options = { maxZoom: 14, attribution: 'Map data: <a href="http://www.pdok.nl">BRT Achtergrondkaart</a>' }
let basemap_pdok = new L.tileLayer('https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0/standaard/EPSG:28992/{z}/{x}/{y}.png', options);

basemap_pdok.getAttribution = function () {
  return 'BRT Achtergrondkaart <a href="http://www.kadaster.nl">Kadaster</a>.';
}
basemap_pdok.addTo(map);