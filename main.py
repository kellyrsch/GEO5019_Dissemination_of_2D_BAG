import duckdb as db
from duckdb.sqltypes import VARCHAR, INTEGER

def poslist_to_wkt(poslist: str, srs_dimension: int = 3) -> str:
    coords = [float(v) for v in poslist.strip().split()]
    if len(coords) % srs_dimension != 0:
        raise ValueError("posList length is not divisible by srsDimension")

    points = []
    for i in range(0, len(coords), srs_dimension):
        x = coords[i]
        y = coords[i + 1]
        points.append((x, y))

    if points[0] != points[-1]:
        points.append(points[0])

    coord_text = ", ".join(f"{x} {y}" for x, y in points)
    return f"POLYGON(({coord_text}))"

con = db.connect('bag.db')
con.create_function("poslist_to_wkt", poslist_to_wkt, [VARCHAR, INTEGER], VARCHAR)
con.install_extension("spatial")
con.load_extension("spatial")
con.execute("INSTALL webbed FROM community")
con.load_extension("webbed")

XML_PATH = 'data\*.xml'
TABLE = "panden"

con.sql(f"DROP TABLE IF EXISTS {TABLE};")
con.sql(f"""
CREATE TABLE {TABLE} (
  identificatie TEXT,
  oorspronkelijkBouwjaar INTEGER,
  geometry_xml TEXT
);
""")

con.execute(f"DROP TABLE IF EXISTS {TABLE};")
con.execute(f"""
CREATE TABLE {TABLE} (
  identificatie TEXT,
  oorspronkelijkBouwjaar INTEGER,
  geom GEOMETRY
);
""")

# Insert rows
con.execute(f"""
INSERT INTO {TABLE}
WITH docs AS (
  SELECT xml
  FROM read_xml_objects(?)
),
panden AS (
  SELECT
    unnest(xml_extract_elements(docs.xml, '//Objecten:Pand')) AS pand_xml
  FROM docs
)
SELECT
  xml_extract_text(pand_xml, '//Objecten:identificatie')[1] AS identificatie,
  TRY_CAST(xml_extract_text(pand_xml, '//Objecten:oorspronkelijkBouwjaar')[1] AS INTEGER) AS oorspronkelijkBouwjaar,
  CAST(ST_GeomFromText(poslist_to_wkt(xml_extract_text(pand_xml, '//Objecten:geometrie/gml:Polygon/gml:exterior/gml:LinearRing/gml:posList')[1], 3)) AS GEOMETRY) AS geom
FROM panden
WHERE xml_extract_text(pand_xml, '//Objecten:identificatie')[1] IS NOT NULL;
""", [XML_PATH])

print(con.execute(f"SELECT * FROM {TABLE} LIMIT 5;").fetchdf())

con.close()