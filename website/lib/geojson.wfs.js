// the function tryParseJSON was adapted from this Stack Overflow question:
// http://stackoverflow.com/questions/3710204/how-to-check-if-a-string-is-a-valid-json-string-in-javascript-without-using-try
function tryParseJSON(jsonString) {
  try {
    var o = JSON.parse(jsonString);

    // Handle non-exception-throwing cases:
    // Neither JSON.parse(false) or JSON.parse(1234) throw errors, hence the type-checking,
    // but... JSON.parse(null) returns 'null', and typeof null === "object", 
    // so we must check for that, too.
    if (o && typeof o === "object" && o !== null) {
      return o;
    }
  } catch (e) { }

  return false;
};


function popUp(f, l) {
  var out = [];
  if (f.properties) {

    for (key in f.properties) {
      out.push("<dt>" + key + "</dt><dd>" + f.properties[key] + "</dd>");
    }
    l.bindPopup("<dl>" + out.join("") + "</dl>");
  }
}


function GeojsonFromWFS(url, params, styleParams) {
  let geojson = L.geoJSON(null, {
    style: styleParams,
    onEachFeature: popUp
  });

  // Make available a function that can refresh
  // the contents (Note: *brute-force*, fetch again all content)
  geojson.refreshData = function () {

    GetFeatureWFS(url, params, function (validJson) {
      console.log("executing GetFeatureWFS")
      // clear all markers
      geojson.clearLayers();
      // add the points we got from the WFS
      geojson.addData(validJson);
      // log how many results we added
      console.log(geojson.getLayers().length);
    });
  }

  // Initialize the layer on construction
  geojson.refreshData()

  return geojson;
}


function GetFeatureWFS(url, params, callback_handleJson) {

  var xhr = new XMLHttpRequest();
  xhr.onload = function () {
    if (xhr.status === 200) {

      var validJson = tryParseJSON(xhr.responseText);
      if (validJson) {
        callback_handleJson(validJson);
      } else {
        console.log('Response is not valid json. Response is: ');
        console.log(xhr.responseText);
        // handleError(url + params + ' gives output: ' + xhr.responseText);
      }

    } else {
      console.log('Request failed.  Returned status of ' + xhr.status + ' ' + xhr.statusText);
      // handleError(url + params + ' gives error: ' + xhr.status + ' ' + xhr.statusText);
    }
  };
  xhr.onerror = function () {
    console.log('Request failed.  Returned status of ' + xhr.status + ' ' + xhr.statusText);
    // handleError(url + params + ' gives error: ' + xhr.status + ' ' + xhr.statusText);
  };
  xhr.open('GET', encodeURI(url + params));
  xhr.setRequestHeader('Accept', 'application/json');
  xhr.send();


}


function insertPoint(url_wfs, typeName, namespace_prefix, namespace_uri, featProperties, geomPropertyName, lng, lat, layerToUpdate) {

	var postData =
		'<wfs:Transaction'
		+ '  service="WFS"'
		+ '  version="1.0.0"'
		+ '  xmlns:' + namespace_prefix + '="' + namespace_uri + '"'
		+ '  xmlns:wfs="http://www.opengis.net/wfs"'
		+ '  xmlns:gml="http://www.opengis.net/gml"'
		+ '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
		+ '  xsi:schemaLocation="http://www.opengis.net/wfs  http://schemas.opengis.net/wfs/1.1.0/WFS-transaction.xsd '
		+ '  ' + namespace_uri + '">'
		+ '  <wfs:Insert>'
		+ '    <' + typeName + '>'
		+ '      <' + featProperties[0].name + '>' + featProperties[0].value + '</' + featProperties[0].name + '>'
		+ '      <' + featProperties[1].name + '>' + featProperties[1].value + '</' + featProperties[1].name + '>'
		+ '      <' + geomPropertyName + '>'
		+ '        <gml:Point srsDimension="2" srsName="EPSG:4326">'
		+ '          <gml:coordinates decimal="." cs="," ts=" ">' + lng + ',' + lat + '</gml:coordinates>'
		+ '        </gml:Point>'
		+ '      </' + geomPropertyName + '>'
		+ '    </' + typeName + '>'
		+ '  </wfs:Insert>'
		+ '</wfs:Transaction>';

	var xhr = new XMLHttpRequest();
	xhr.open("POST", url_wfs, true);
	xhr.setRequestHeader("Content-Type", "text/xml");
	xhr.onreadystatechange = function () {
		if (xhr.readyState == 4 && xhr.status == 200) {

			// even if the status code is 200, an error could have occured
			var xml = xhr.responseXML;
			if (xml.documentElement.nodeName != 'ServiceExceptionReport') {

				var fid = xml.documentElement.getElementsByTagName("ogc:FeatureId")[0].getAttribute("fid");

				console.log('point feature ' + fid + ' inserted successfully');

				// close the (still) open popup by simulating a click 
				document.querySelector(".leaflet-popup-close-button").click();

				// refresh the layer 
				layerToUpdate.refreshData()

			}
			else if (xml.documentElement.nodeName === 'ServiceExceptionReport') {
				console.log('error in WFS insert of feature');
				var xmlText = new XMLSerializer().serializeToString(xml);
				console.log(xmlText);
			}
			else {
				console.log('unknown error in WFS insert of feature');
				console.log(xml);
			}
		}
		else if (xhr.readyState == 4) {
			console.log('unknown error in WFS insert of feature');
		}
	}
	console.log(postData);
	xhr.send(postData);
}