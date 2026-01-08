### Right now, this is a copy of my hw01 api setup script that we are editing as a start for the hw03 API

import json
from fastapi import FastAPI, Query
import duckdb

app = FastAPI()

### Connect to the DuckDB (backend that was set up earlier in this assignment)
db = duckdb.connect()
db.execute("INSTALL spatial")
db.execute("LOAD spatial")



### Test if the API is working, with a simple message on the root page
@app.get("/")
def read_root():
    return {"message": "the API is running!"}



### Collections Endpoint
@app.get("/collections")
def read_collections():
    collection = []

    total_count_panden = db.execute("""
               SELECT COUNT(*)
               FROM 'bag.parquet'""").fetchone()

    panden = {
        "id": 'panden',
        "title": f"panden in the Netherlands",
        "description": f"pand footprints for the Netherlands",
        "itemType": "feature",
        "pand_count": total_count_panden,
        "links": [
            {
                "href": f"/collections/panden/items",
                "rel": "items",
                "type": "application/geo+json",
                "title": f"panden in the Netherlands"
            }
        ]
    }
    collection.append(panden)

    total_count_vbo = db.execute("""
               SELECT COUNT(*)
               FROM 'vbo.parquet'""").fetchone()

    vbo = {
        "id": 'verblijfsobjecten',
        "title": f"verblijfsobjecten in the Netherlands",
        "description": f"pand footprints for the Netherlands",
        "itemType": "feature",
        "pand_count": total_count_vbo,
        "links": [
            {
                "href": f"/collections/verblijfsobjecten/items",
                "rel": "items",
                "type": "application/geo+json",
                "title": f"panden in the Netherlands"
            }
        ]
    }
    collection.append(vbo)

    ## Add metadata about limit and offset etc. and navigation links when applicable
    collections = {
        "collections": collection,
        "total_feature_count": 7,
        "links": []
    }

    return collections

@app.get("/collections/panden/items")
def read_municipality_items(
        minx: float = Query(default=78600.0), # for default bbox values I took the assignment bbox
        miny: float = Query(default=445000.0),
        maxx: float = Query(default=85800.0),
        maxy: float = Query(default=450000.0),
        crs: str = Query(default='EPSG:28992'),
        limit: int = Query(50, ge=1, le=1000), # always show at least 1 and no more than 1000
        offset: int = Query(0, ge=0) # ensure that offset is always positive
):
    ## Count how many buildings in the bbox
    total_count_b_in_bbox = db.execute("""
            SELECT COUNT(*)
            FROM 'bag.parquet'
            WHERE ST_Intersects(geom, ST_MakeEnvelope(?,?,?,?));
        """, [minx, miny, maxx, maxy]).fetchone()
    total_count = total_count_b_in_bbox[0]

    ## Get the buildings in this bbox
    if crs == 'EPSG:28992':
        db_result = db.execute("""
                SELECT identificatie, status, oorspronkelijkBouwjaar, documentdatum, ST_AsGeoJSON(geom) AS geom
                FROM 'bag.parquet'
                WHERE ST_Intersects(geom, ST_MakeEnvelope(?,?,?,?))
                LIMIT ? OFFSET ?;
            """, [minx, miny, maxx, maxy, limit, offset]).fetchall()
    else:
        db_result = db.execute("""
                SELECT identificatie, status, oorspronkelijkBouwjaar, documentdatum, ST_AsGeoJSON(ST_Transform(geom,'EPSG:28992',?)) AS geom
                FROM 'bag.parquet'
                WHERE ST_Intersects(geom, ST_MakeEnvelope(?,?,?,?))
                LIMIT ? OFFSET ?;
            """, [crs, minx, miny, maxx, maxy, limit, offset]).fetchall()

    ## First build Features array per building
    features = []
    for row in db_result:
        id = row[0]
        status = row[1]
        year = row[2]
        doc = row[3]
        geom = row[4]

        feature = {
            "type": "Feature",
            "geometry": json.loads(geom),
            "properties": {
                "id": id,
                "status": status,
                "oorspronkelijkBouwjaar": year,
                "documentdatum": doc
            }
        }
        features.append(feature)

    ## Build a FeatureCollection from the buildings (Features) in the bbox and add metadata
    feature_collection = {
        "type": "FeatureCollection",
        "features": features,
        "total_feature_count": total_count,
        "current_limit": limit,
        "current_offset": offset,
        "nr_of_returned_features": len(features),
        "links": []
    }

    ## When applicable, add links to the previous and next page (pagination)
    # Link to next page
    if offset + limit < total_count:
        feature_collection["links"].append({
            "href": f"/panden/bbox?minx={minx}&miny={miny}&maxx={maxx}&maxy={maxy}&crs={crs}&limit={limit}&offset={offset + limit}",
            "rel": "next",
            "type": "application/geo+json",
            "title": f"Next page of panden (features) in the specified bounding box"
        })

    # Link to previous page
    if offset > 0:
        prev_offset = max(0, offset - limit)  # ensure that offset is always positive
        feature_collection["links"].append({
            "href": f"/panden/bbox?minx={minx}&miny={miny}&maxx={maxx}&maxy={maxy}&crs={crs}&limit={limit}&offset={prev_offset}",
            "rel": "previous",
            "type": "application/geo+json",
            "title": f"Previous page of panden (features) in the specified bounding box"
        })

    return feature_collection


### Municipality-based Endpoints - building_id
@app.get("/collections/panden/items/{pandRef}")
def read_building_id(
        pandRef: str,
        crs: str = Query(default='EPSG:28992')
):

    if crs == 'EPSG:28992':
        db_result = db.execute("""
            SELECT identificatie, status, oorspronkelijkBouwjaar, documentdatum, ST_AsGeoJSON(geom) AS geom
            FROM 'bag.parquet' 
            WHERE identificatie = ?;
        """, [pandRef]).fetchone()
    else:
        db_result = db.execute("""
            SELECT identificatie, status, oorspronkelijkBouwjaar, documentdatum, ST_AsGeoJSON(ST_Transform(geom,'EPSG:28992',?)) AS geom
            FROM 'bag.parquet' 
            WHERE identificatie = ?;
        """, [crs,pandRef]).fetchone()

    identificatie, status, oorspronkelijkBouwjaar, documentdatum, geom = db_result

    building = {
    "type": "Feature",
        "geometry": json.loads(geom),
        "properties": {
            "id": identificatie,
            "status": status,
            "oorspronkelijkBouwjaar": oorspronkelijkBouwjaar,
            "documentdatum": documentdatum
        }
    }

    return building