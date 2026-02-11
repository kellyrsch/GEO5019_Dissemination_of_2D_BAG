import duckdb as db
import time
from GML_to_WKT import gml_to_wkt
from duckdb.sqltypes import VARCHAR, BLOB

if __name__ == "__main__":
    con = db.connect()
    con.install_extension("spatial")
    con.load_extension("spatial")
    con.execute("INSTALL webbed FROM community")
    con.load_extension("webbed")
    con.create_function("gml_to_wkt", gml_to_wkt, [VARCHAR], BLOB)

    XML_PATH = 'MUN\9999WPL08122025-000001.xml'

    tic = time.time()

    con.sql(f"""
        COPY (
        WITH docs AS (
          SELECT xml FROM read_xml_objects('{XML_PATH}', maximum_file_size = 100000000)
        ),
        muns_xml AS (
          SELECT unnest(xml_extract_elements(xml, '//Objecten:Woonplaats')) AS mun_xml
          FROM docs
        ),
        extracted AS (
          SELECT
            xml_extract_text(mun_xml, '//Objecten:identificatie')[1] AS identificatie,
            xml_extract_text(mun_xml, '//Objecten:naam')[1] AS naam,
            xml_extract_text(mun_xml, '//Objecten:status')[1] AS status,
            TRY_CAST(xml_extract_text(mun_xml, '//Objecten:documentdatum')[1] AS DATE) AS documentdatum,
            CAST(
              xml_extract_elements(
                mun_xml,
                '(//Objecten:geometrie/Objecten:vlak/gml:Polygon | //Objecten:geometrie/Objecten:multivlak/gml:MultiSurface)[1]'
              )[1] AS VARCHAR
            ) AS geom_text
          FROM muns_xml
          WHERE xml_extract_text(mun_xml, '//Historie:eindGeldigheid')[1] IS NULL
        )
        SELECT
          identificatie,
          naam,
          status,
          documentdatum,
          ST_GeomFromWkb(gml_to_wkt(geom_text)) AS geom
        FROM extracted
        WHERE geom_text IS NOT NULL AND geom_text <> ''
        ) TO 'wpl.parquet' (FORMAT 'parquet', COMPRESSION 'zstd')
        """)

    tac = time.time()

    print("time:", (tac - tic), "s")

    con.close()