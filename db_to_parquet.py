import duckdb as db
import time

con = db.connect("bag.db")

con.load_extension('spatial')

con.sql('''COPY 
    (SELECT * FROM panden ORDER BY
    ST_Hilbert(geom, ST_Extent(ST_MakeEnvelope(0, 280000, 310000, 640000))))
    TO 'bag.parquet' (FORMAT 'parquet', COMPRESSION 'zstd');''')

minx = 250000
miny = 590000
maxx = 260000
maxy = 600000

tic = time.time()
total = con.sql(f"""
    SELECT COUNT(*) 
    FROM 'bag.parquet'
    WHERE ST_Within(geom, ST_Extent(ST_MakeEnvelope({minx}, {miny}, {maxx}, {maxy})))
""").fetchone()[0]
tac = time.time()
print(total, "- time:", (tac - tic) * 1000, "ms")

con.close()