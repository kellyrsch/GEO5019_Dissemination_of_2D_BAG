import duckdb as db

con = db.connect("bag.db")

con.load_extension('spatial')
con.sql("SELECT * FROM panden LIMIT 5").show()

con.sql(f"DROP TABLE IF EXISTS fields;")
con.sql('''CREATE TABLE fields AS 
    (SELECT * from panden);
    COPY fields TO 'bag.parquet' (FORMAT 'parquet', COMPRESSION 'zstd');''')

minx = 250000
miny = 590000
maxx = 260000
maxy = 600000

polygon = f"POLYGON(({minx} {miny},{maxx} {miny},{maxx} {maxy},{minx} {maxy},{minx} {miny}))"
total = con.sql(f"""
    SELECT COUNT(*) 
    FROM 'bag.parquet'
    WHERE ST_Within(geom, ST_GeomFromText('{polygon}'))
""").fetchone()[0]
print(total)

con.close()