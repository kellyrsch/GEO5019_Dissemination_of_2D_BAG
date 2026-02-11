import duckdb as db
import time
from GML_to_WKT import gml_to_wkt
from duckdb.sqltypes import VARCHAR, BLOB

def xml_to_db(XML_PATH, TABLE):
    con.sql(f"""
    INSERT INTO {TABLE} (identificatie, status, oorspronkelijkBouwjaar, documentdatum, geom)
    WITH docs AS (
      SELECT xml
      FROM read_xml_objects('{XML_PATH}', maximum_file_size = 32000000)
    ),
    panden_xml AS (
      SELECT unnest(xml_extract_elements(xml, '//Objecten:Pand')) AS pand_xml
      FROM docs
    ),
    extracted AS (
      SELECT
        xml_extract_text(pand_xml, '//Objecten:identificatie')[1] AS identificatie,
        xml_extract_text(pand_xml, '//Objecten:status')[1] AS status,
        TRY_CAST(xml_extract_text(pand_xml, '//Objecten:oorspronkelijkBouwjaar')[1] AS INTEGER) AS oorspronkelijkBouwjaar,
        TRY_CAST(xml_extract_text(pand_xml, '//Objecten:documentdatum')[1] AS DATE) AS documentdatum,
        CAST(
          xml_extract_elements(
            pand_xml,
            '(//Objecten:geometrie/gml:Polygon | //Objecten:geometrie/Objecten:multivlak/gml:MultiSurface)[1]'
          )[1] AS VARCHAR
        ) AS geom_text
      FROM panden_xml
      WHERE xml_extract_text(pand_xml, '//Historie:eindGeldigheid')[1] IS NULL
    )
    SELECT
      identificatie,
      status,
      oorspronkelijkBouwjaar,
      documentdatum,
      ST_GeomFromWkb(gml_to_wkt(geom_text)) AS geom
    FROM extracted
    WHERE geom_text IS NOT NULL AND geom_text <> ''
    """)

if __name__ == "__main__":
    con = db.connect('bag.db')
    con.install_extension("spatial")
    con.load_extension("spatial")
    con.execute("INSTALL webbed FROM community")
    con.load_extension("webbed")
    con.create_function("gml_to_wkt", gml_to_wkt, [VARCHAR], BLOB)

    TABLE = "panden"

    tic = time.time()

    con.sql(f"DROP TABLE IF EXISTS {TABLE};")
    con.sql(f"""
    CREATE TABLE {TABLE} (
      identificatie TEXT,
      status TEXT,
      oorspronkelijkBouwjaar INTEGER,
      documentdatum DATE,
      geom GEOMETRY
    );
    """)

    for i in range(1,2):
        XML_PATH = f'data\9999PND08122025-{i:06d}.xml'
        if i%100 == 0:
            print(i)
            print("time:", (time.time() - tic), "s")
        xml_to_db(XML_PATH, TABLE)

    tac = time.time()

    print(con.sql(f"SELECT * FROM {TABLE} LIMIT 5;").show())

    print("time:", (tac - tic), "s")

    con.close()