import os
import time
import duckdb as db
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

from GML_to_WKT import gml_to_wkt
from duckdb.sqltypes import VARCHAR, BLOB


SQL_TO_PARQUET = r"""
COPY (
  WITH docs AS (
    SELECT xml
    FROM read_xml_objects($xml_path, maximum_file_size = 32000000)
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
      xml_extract_text(pand_xml, '//Objecten:geconstateerd')[1] AS geconstateerd,
      xml_extract_text(pand_xml, '//Objecten:documentnummer')[1] AS documentnummer,
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
    geconstateerd,
    documentnummer,
    documentdatum,
    ST_GeomFromWkb(gml_to_wkt(geom_text)) AS geom
  FROM extracted
  WHERE geom_text IS NOT NULL AND geom_text <> ''
)
TO $out_parquet (FORMAT 'parquet');
"""


def _process_one_xml(xml_path: str, out_parquet: str, use_webbed: bool = True) -> str:
    """
    Worker: XML -> Parquet shard.
    Returns the parquet path (for merging).
    """
    con = db.connect(database=":memory:")

    con.install_extension("spatial")
    con.load_extension("spatial")

    if use_webbed:
        con.execute("INSTALL webbed FROM community")
        con.load_extension("webbed")

    con.create_function("gml_to_wkt", gml_to_wkt, [VARCHAR], BLOB)

    con.execute(SQL_TO_PARQUET, {"xml_path": xml_path, "out_parquet": out_parquet})

    con.close()
    return out_parquet


def parallel_xmls_to_single_parquet(
    xml_paths,
    final_parquet_path: str,
    tmp_dir: str = "tmp_parquet_shards",
    workers: int | None = None,
    use_webbed: bool = True,
):
    """
    Parallelize per XML file into shard parquets, then merge into one parquet.
    """
    tmp_dir_path = Path(tmp_dir)
    tmp_dir_path.mkdir(parents=True, exist_ok=True)

    # Decide worker count (good default: CPU count)
    if workers is None:
        workers = max(1, os.cpu_count() or 1)

    shard_paths = []

    with ProcessPoolExecutor(max_workers=workers) as ex:
        futures = []
        for idx, xml_path in enumerate(xml_paths):
            shard_path = tmp_dir_path / f"shard_{idx:06d}.parquet"
            futures.append(ex.submit(_process_one_xml, str(xml_path), str(shard_path), use_webbed))

        for f in as_completed(futures):
            shard_paths.append(f.result())

    # Merge shards -> one final parquet
    con = db.connect(database=":memory:")
    con.install_extension("spatial")
    con.load_extension("spatial")
    con.execute(
        '''COPY (SELECT * FROM read_parquet($files) ORDER BY
         ST_Hilbert(geom, ST_Extent(ST_MakeEnvelope(0, 280000, 310000, 640000))))
         TO $out (FORMAT 'parquet', COMPRESSION 'zstd');''',
        {"files": shard_paths, "out": final_parquet_path},
    )
    con.close()


if __name__ == "__main__":
    tic = time.time()

    # Build your XML list (example: 1 file; extend to your range)
    xml_paths = []
    for i in range(1, 2391):
        # Use Path to avoid backslash escape issues
        xml_paths.append(Path(f"data") / f"9999PND08122025-{i:06d}.xml")

    parallel_xmls_to_single_parquet(
        xml_paths=xml_paths,
        final_parquet_path="panden.parquet",
        tmp_dir="tmp_panden_shards",
        workers=None,          # defaults to CPU count
        use_webbed=True,       # set to False if you don't need it
    )

    print("time:", (time.time() - tic), "s")