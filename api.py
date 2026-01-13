import json
from fastapi import FastAPI, Query
import duckdb
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (for development)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

### Connect to the DuckDB
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
def read_panden_items(
        minx: float = Query(default=None), # for default bbox values I took the assignment bbox
        miny: float = Query(default=None),
        maxx: float = Query(default=None),
        maxy: float = Query(default=None),
        crs: str = Query(default='EPSG:28992'),
        woonplaats: str = Query(default=None),
        postcode_4: str = Query(default=None),
        limit: int = Query(50, ge=1, le=1000), # always show at least 1 and no more than 1000
        offset: int = Query(0, ge=0) # ensure that offset is always positive
):
    woonplaats = woonplaats.capitalize() if woonplaats else None

    from_list = ["'bag.parquet' AS pnd"]
    if woonplaats:
        from_list.append(f"(SELECT * FROM 'mun.parquet' WHERE naam = '{woonplaats}' OR identificatie = '{woonplaats}') as wpl")
    if postcode_4:
        from_list.append(f"(SELECT * FROM 'postcode.parquet' WHERE postcode = {postcode_4}) as psc")
    from_statement = "FROM " + ", ".join(from_list)

    where_list = []
    if (minx and miny and maxx and maxy):
        where_list.append(f"ST_Intersects(pnd.geom, ST_MakeEnvelope({minx},{miny},{maxx},{maxy}))")
    if woonplaats:
        where_list.append("ST_Intersects(pnd.geom, wpl.geom)")
    if postcode_4:
        where_list.append("ST_Intersects(pnd.geom, psc.geom)")
    where_statement = "WHERE " + " AND ".join(where_list) if len(where_list) > 0 else ""

    geom_crs = "pnd.geom" if crs == 'EPSG:28992' else f"ST_Transform(pnd.geom,'EPSG:28992',{crs})"

    ## Count how many buildings in the bbox
    total_count_b_in_bbox = db.execute(f"""
            SELECT COUNT(pnd.identificatie)
            {from_statement}
            {where_statement};
        """).fetchone()
    total_count = total_count_b_in_bbox[0]

    ## Get the buildings in this bbox
    db_result = db.execute(f"""
            SELECT pnd.identificatie, pnd.status, pnd.oorspronkelijkBouwjaar, pnd.documentdatum, ST_AsGeoJSON({geom_crs}) AS geom
            {from_statement}
            {where_statement}
            LIMIT ? OFFSET ?;
        """, [limit, offset]).fetchall()

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
            "href": f"/panden/items?minx={minx}&miny={miny}&maxx={maxx}&maxy={maxy}&woonplaats={woonplaats}&postcode_4={postcode_4}&crs={crs}&limit={limit}&offset={offset + limit}",
            "rel": "next",
            "type": "application/geo+json",
            "title": f"Next page of panden (features) in the specified bounding box"
        })

    # Link to previous page
    if offset > 0:
        prev_offset = max(0, offset - limit)  # ensure that offset is always positive
        feature_collection["links"].append({
            "href": f"/panden/items?minx={minx}&miny={miny}&maxx={maxx}&maxy={maxy}&woonplaats={woonplaats}&postcode_4={postcode_4}&crs={crs}&limit={limit}&offset={prev_offset}",
            "rel": "previous",
            "type": "application/geo+json",
            "title": f"Previous page of panden (features) in the specified bounding box"
        })

    return feature_collection


### Municipality-based Endpoints - building_id
@app.get("/collections/panden/items/{pandRef}")
def read_pandRef(
        pandRef: str,
        crs: str = Query(default='EPSG:28992')
):
    geom_crs = "geom" if crs == 'EPSG:28992' else f"ST_Transform(geom,'EPSG:28992',{crs})"

    db_result = db.execute(f"""
        SELECT identificatie, status, oorspronkelijkBouwjaar, documentdatum, ST_AsGeoJSON({geom_crs}) AS geom
        FROM 'bag.parquet' 
        WHERE identificatie = ?;
    """, [pandRef]).fetchone()

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

@app.get("/collections/verblijfsobjecten/items")
def read_verblijfsobjecten_items(
        crs: str = Query(default='EPSG:28992'),
        pandRef: str = Query(default=None),
        limit: int = Query(50, ge=1, le=1000), # always show at least 1 and no more than 1000
        offset: int = Query(0, ge=0) # ensure that offset is always positive
):
    geom_crs = "geom" if crs == 'EPSG:28992' else f"ST_Transform(geom,'EPSG:28992',{crs})"

    where_statement = f"WHERE pand = '{pandRef}'" if pandRef else ""

    total_count_b_in_bbox = db.execute(f"""
                SELECT COUNT(*)
                FROM 'vbo.parquet'
                {where_statement};
            """).fetchone()
    total_count = total_count_b_in_bbox[0]

    ## Get the buildings in this bbox
    db_result = db.execute(f"""
             SELECT identificatie, status, gebruiksdoel, documentdatum, oppervlakte, pand, hoofdadres, ST_AsGeoJSON({geom_crs}) AS geom
             FROM 'vbo.parquet'
             {where_statement}
             LIMIT ? OFFSET ?;
         """, [limit, offset]).fetchall()

    ## First build Features array per building
    features = []
    for row in db_result:
        id = row[0]
        status = row[1]
        doel = row[2]
        doc = row[3]
        opp = row[4]
        pand = row[5]
        hoofdadres = row[6]
        geom = row[7]

        feature = {
            "type": "Feature",
            "geometry": json.loads(geom),
            "properties": {
                "id": id,
                "status": status,
                "gebruiksdoel": doel,
                "documentdatum": doc,
                "oppervlakte": opp,
                "pand": pand,
                "hoofdadres": hoofdadres,
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
            "href": f"/verblijfsobjecten/items?crs={crs}&limit={limit}&offset={offset + limit}",
            "rel": "next",
            "type": "application/geo+json",
            "title": f"Next page of verblijfsobjecten"
        })

    # Link to previous page
    if offset > 0:
        prev_offset = max(0, offset - limit)  # ensure that offset is always positive
        feature_collection["links"].append({
            "href": f"/verblijfsobjecten/items?crs={crs}&limit={limit}&offset={prev_offset}",
            "rel": "previous",
            "type": "application/geo+json",
            "title": f"Previous page of verblijfsobjecten (features)"
        })

    return feature_collection

@app.get("/collections/verblijfsobjecten/items/{vboRef}")
def read_vboRef(
        vboRef: str,
        crs: str = Query(default='EPSG:28992')
):
    geom_crs = "geom" if crs == 'EPSG:28992' else f"ST_Transform(geom,'EPSG:28992',{crs})"

    db_result = db.execute(f"""
        SELECT identificatie, status, gebruiksdoel, documentdatum, oppervlakte, pand, hoofdadres, ST_AsGeoJSON({geom_crs}) AS geom
        FROM 'vbo.parquet' 
        WHERE identificatie = ?;
    """, [vboRef]).fetchone()

    identificatie, status, doel, doc, opp, pand, hoofdadres, geom = db_result

    vbo = {
    "type": "Feature",
            "geometry": json.loads(geom),
            "properties": {
                "id": id,
                "status": status,
                "gebruiksdoel": doel,
                "documentdatum": doc,
                "oppervlakte": opp,
                "pand": pand,
                "hoofdadres": hoofdadres,
            }
    }

    return vbo