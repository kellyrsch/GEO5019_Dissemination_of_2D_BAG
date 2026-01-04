### Right now, this is a copy of my hw01 api setup script that we are editing as a start for the hw03 API

import json
from fastapi import FastAPI, Query
import duckdb

app = FastAPI()

### Connect to the DuckDB (backend that was set up earlier in this assignment)
db = duckdb.connect("bag.db", read_only=True)
db.execute("INSTALL spatial")
db.execute("LOAD spatial")



### Test if the API is working, with a simple message on the root page
@app.get("/")
def read_root():
    return {"message": "the API is running!"}



### Collections Endpoint
@app.get("/collections")
def read_collections(
        limit: int = Query(50, ge=1, le=1000), # always show at least 1 and no more than 1000
        offset: int = Query(0, ge=0) # ensure that offset is always positive
):

    ## Count how many municipalities there are
    total_count_municipalities = db.execute("""
        SELECT COUNT(DISTINCT municipality)
        FROM buildings_join;
    """).fetchone()
    total_count = total_count_municipalities[0]

    ## Get info about the municipalities per municipality
    db_result = db.execute("""
        SELECT municipality, m_code, COUNT(*) AS building_count
        FROM buildings_join 
        WHERE municipality IS NOT NULL
        GROUP BY municipality, m_code
        ORDER BY municipality
        LIMIT ? OFFSET ?;
    """, [limit, offset]).fetchall()

    ## First make an array with the municipality info
    collection = []
    for row in db_result:
        municipality = row[0]
        building_count = row[2]

        municipality_feature = {
            "id": municipality,
            "title": f"Buildings in {municipality}",
            "description": f"Building footprints for {municipality} municipality",
            "itemType": "feature",
            "building_count": building_count,
            "links": [
                {
                    "href": f"/collections/{municipality}/items",
                    "rel": "items",
                    "type": "application/geo+json",
                    "title": f"Buildings in {municipality}"
                }
            ]
        }
        collection.append(municipality_feature)

    ## Add metadata about limit and offset etc. and navigation links when applicable
    collections = {
        "collections": collection,
        "total_feature_count": total_count,
        "current_limit": limit,
        "current_offset": offset,
        "nr_of_returned_features": len(collection),
        "links": []
    }

    ## When applicable, add links to the previous and next page (pagination)
    # Link to next page
    if offset + limit < total_count:
        collections["links"].append({
            "href": f"/collections?limit={limit}&offset={offset+limit}",
            "rel": "next",
            "type": "application/geo+json",
            "title": f"Next page of municipalities"
        })

    # Link to previous page
    if offset > 0:
        prev_offset = max(0, offset - limit) # ensure that offset is always positive
        collections["links"].append({
            "href": f"/collections?limit={limit}&offset={prev_offset}",
            "rel": "previous",
            "type": "application/geo+json",
            "title": f"Previous page of municipalities"
        })

    return collections



### Municipality-based Endpoints - items
@app.get("/collections/{municipality}/items")
def read_municipality_items(
        municipality: str,
        limit: int = Query(50, ge=1, le=1000), # always show at least 1 and no more than 1000
        offset: int = Query(0, ge=0) # ensure that offset is always positive
):

    ## Count how many buildings in this municipality
    total_count_b_in_m = db.execute("""
        SELECT COUNT(*)
        FROM buildings_join
        WHERE municipality = ?;
    """, [municipality]).fetchone()
    total_count = total_count_b_in_m[0]

    ## Get the buildings in this municipality
    db_result = db.execute("""
        SELECT id, municipality, ST_AsGeoJSON(geom) AS geom
        FROM buildings_join 
        WHERE municipality = ?
        LIMIT ? OFFSET ?;
    """, [municipality, limit, offset]).fetchall()

    ## First build Features array per building
    features = []
    for row in db_result:
        id = row[0]
        municipality = row[1]
        geom = row[2]

        feature = {
            "type": "Feature",
            "geometry": json.loads(geom),
            "properties": {
                "id": id,
                "municipality_name": municipality
            }
        }
        features.append(feature)

    ## Build a FeatureCollection from the buildings (Features) in the municipality and add metadata
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
            "href": f"/collections/{municipality}/items?limit={limit}&offset={offset+limit}",
            "rel": "next",
            "type": "application/geo+json",
            "title": f"Next page of buildings (features) in {municipality} municipality"
        })

    # Link to previous page
    if offset > 0:
        prev_offset = max(0, offset - limit) # ensure that offset is always positive
        feature_collection["links"].append({
            "href": f"/collections/{municipality}/items?limit={limit}&offset={prev_offset}",
            "rel": "previous",
            "type": "application/geo+json",
            "title": f"Previous page of buildings (features) in {municipality} municipality"
        })

    return feature_collection


### Municipality-based Endpoints - building_id
@app.get("/collections/{municipality}/items/{building_id}")
def read_building_id(
        municipality: str,
        building_id: str
):

    ## Get the information about specific building
    db_result = db.execute("""
        SELECT id, municipality, ST_AsGeoJSON(geom) AS geom
        FROM buildings_join 
        WHERE municipality = ? 
        AND id = ?;
    """, [municipality, building_id]).fetchone()

    id, municipality, geom = db_result

    building = {
        "type": "Feature",
        "geometry": json.loads(geom),
        "properties": {
            "id": id,
            "municipality_name": municipality
        }
    }

    return building



### Spatial Query Endpoints
@app.get("/buildings/bbox")
def read_bbox(
        minx: float = Query(default=78600.0), # for default bbox values I took the assignment bbox
        miny: float = Query(default=445000.0),
        maxx: float = Query(default=85800.0),
        maxy: float = Query(default=450000.0),
        limit: int = Query(50, ge=1, le=1000), # always show at least 1 and no more than 1000
        offset: int = Query(0, ge=0) # ensure that offset is always positive
):

    ## Count how many buildings in the bbox
    total_count_b_in_bbox = db.execute("""
        SELECT COUNT(*)
        FROM buildings_join
        WHERE ST_Intersects(geom, ST_MakeEnvelope(?,?,?,?));
    """, [minx, miny, maxx, maxy]).fetchone()
    total_count = total_count_b_in_bbox[0]

    ## Get the buildings in this bbox
    db_result = db.execute("""
        SELECT id, municipality, ST_AsGeoJSON(geom) AS geom
        FROM buildings_join 
        WHERE ST_Intersects(geom, ST_MakeEnvelope(?,?,?,?))
        LIMIT ? OFFSET ?;
    """, [minx, miny, maxx, maxy, limit, offset]).fetchall()

    ## First build Features array per building
    features = []
    for row in db_result:
        id = row[0]
        municipality = row[1]
        geom = row[2]

        feature = {
            "type": "Feature",
            "geometry": json.loads(geom),
            "properties": {
                "id": id,
                "municipality_name": municipality
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
            "href": f"/buildings/bbox?minx={minx}&miny={miny}&maxx={maxx}&maxy={maxy}&limit={limit}&offset={offset+limit}",
            "rel": "next",
            "type": "application/geo+json",
            "title": f"Next page of buildings (features) in the specified bounding box"
        })

    # Link to previous page
    if offset > 0:
        prev_offset = max(0, offset - limit) # ensure that offset is always positive
        feature_collection["links"].append({
            "href": f"/buildings/bbox?minx={minx}&miny={miny}&maxx={maxx}&maxy={maxy}&limit={limit}&offset={prev_offset}",
            "rel": "previous",
            "type": "application/geo+json",
            "title": f"Previous page of buildings (features) in the specified bounding box"
        })

    return feature_collection