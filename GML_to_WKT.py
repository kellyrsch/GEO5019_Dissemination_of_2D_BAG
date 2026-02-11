from osgeo import ogr

def gml_to_wkt(gml: str) -> str:
    # Fast rejects (avoid calling into GDAL for empty/NULL-ish values)
    if not gml:
        return ""

    geom = ogr.CreateGeometryFromGML(gml)
    if geom is None:          # avoid exception path
        return ""

    # Flatten is cheap, but you can skip it when already 2D.
    # Note: OGR doesn't have "Is3D()" universally, but GetCoordinateDimension works.
    if geom.GetCoordinateDimension() > 2:
        geom.FlattenTo2D()

    return geom.ExportToWkb()