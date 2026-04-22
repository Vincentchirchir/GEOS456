import arcpy
import os


def create_route_with_measure_system(
    input_line_fc,
    out_gdb,
    start_measure=0,
    route_id_field="ROUTE_ID",
    route_id_value="ROUTE_01",
):
    """
    Creates an M-enabled route feature class from a line feature class.

    Copies the input line, dissolves it into a single feature, then runs
    Create Routes using FromM and ToM fields derived from the line's shape
    length and the specified start measure.

    Parameters
    ----------
    input_line_fc : str
        Path to the input line feature class.
    out_gdb : str
        Path to the output geodatabase.
    start_measure : float, optional
        Starting measure value. Defaults to 0.
    route_id_field : str, optional
        Name of the route identifier field. Defaults to "ROUTE_ID".
    route_id_value : str, optional
        Value written into the route identifier field. Defaults to "ROUTE_01".

    Returns
    -------
    dict
        route_fc       -- path to the output route feature class
        route_id_field -- name of the route ID field
        route_id_value -- value in the route ID field
        base_name      -- validated base name derived from the input
    """
    desc = arcpy.Describe(input_line_fc)
    catalog_path = desc.catalogPath

    base_name = arcpy.ValidateTableName(
        os.path.splitext(os.path.basename(catalog_path))[0], out_gdb
    )

    # Work on a copy so the original feature class is never modified
    line_copy_fc = os.path.join(out_gdb, base_name + "_copy")
    arcpy.management.CopyFeatures(input_line_fc, line_copy_fc)

    # Add the route ID field and fill it with the specified value
    field_names = [f.name for f in arcpy.ListFields(line_copy_fc)]
    if route_id_field not in field_names:
        arcpy.management.AddField(line_copy_fc, route_id_field, "TEXT", field_length=50)

    arcpy.management.CalculateField(
        in_table=line_copy_fc,
        field=route_id_field,
        expression=f"'{route_id_value}'",
        expression_type="PYTHON3",
    )

    # Dissolve in case the line is split into multiple segments
    route_diss = os.path.join(out_gdb, base_name + "_dissolve")
    arcpy.management.Dissolve(line_copy_fc, route_diss, route_id_field)

    # FromM and ToM are required by Create Routes when using two fields for measures
    diss_fields = [f.name for f in arcpy.ListFields(route_diss)]
    if "FromM" not in diss_fields:
        arcpy.management.AddField(route_diss, "FromM", "DOUBLE")
    if "ToM" not in diss_fields:
        arcpy.management.AddField(route_diss, "ToM", "DOUBLE")

    arcpy.management.CalculateField(
        route_diss, "FromM", str(float(start_measure)), "PYTHON3"
    )

    code_block = """
def calc_to_m(shape_length, start_m):
    return float(shape_length) + float(start_m)
"""
    arcpy.management.CalculateField(
        route_diss,
        "ToM",
        f"calc_to_m(!shape.length!, {float(start_measure)})",
        "PYTHON3",
        code_block,
    )

    route_fc = os.path.join(out_gdb, base_name + "_Route")
    arcpy.lr.CreateRoutes(
        route_diss, route_id_field, route_fc, "TWO_FIELDS", "FromM", "ToM"
    )

    # Delete intermediates — only the route output is needed
    if arcpy.Exists(line_copy_fc):
        arcpy.management.Delete(line_copy_fc)
    if arcpy.Exists(route_diss):
        arcpy.management.Delete(route_diss)

    return {
        "route_fc": route_fc,
        "route_id_field": route_id_field,
        "route_id_value": route_id_value,
        "base_name": base_name,
    }


def create_stationing_source_line(
    route_fc,
    out_gdb,
    base_name,
    route_id_field,
    route_id_value,
    start_measure=None,
    end_measure=None,
):
    """
    Returns the line that stationing will be generated on.

    If end_measure is provided, clips the route to the given measure range
    using Make Route Event Layer and returns the clipped feature class.
    If end_measure is None, the full route is returned as-is.

    Parameters
    ----------
    route_fc : str
        Path to the M-enabled route feature class.
    out_gdb : str
        Path to the output geodatabase.
    base_name : str
        Base name used for naming intermediate and output feature classes.
    route_id_field : str
        Name of the route identifier field.
    route_id_value : str
        Value in the route identifier field.
    start_measure : float, optional
        Start of the measure range to clip to.
    end_measure : float, optional
        End of the measure range to clip to. If None, the full route is used.

    Returns
    -------
    str
        Path to the line feature class to station along.
    """
    if end_measure is None:  # no end measure — use the full route
        return route_fc

    segment_table = os.path.join(out_gdb, f"{base_name}_segment_event")
    if arcpy.Exists(segment_table):
        arcpy.management.Delete(segment_table)
    arcpy.management.CreateTable(out_gdb, f"{base_name}_segment_event")

    seg_fields = [f.name for f in arcpy.ListFields(segment_table)]
    if route_id_field not in seg_fields:
        arcpy.management.AddField(
            segment_table, route_id_field, "TEXT", field_length=50
        )
    if "FMEAS" not in seg_fields:
        arcpy.management.AddField(segment_table, "FMEAS", "DOUBLE")
    if "TMEAS" not in seg_fields:
        arcpy.management.AddField(segment_table, "TMEAS", "DOUBLE")

    with arcpy.da.InsertCursor(
        segment_table, [route_id_field, "FMEAS", "TMEAS"]
    ) as cursor:
        cursor.insertRow([route_id_value, float(start_measure), float(end_measure)])

    segment_layer = f"{base_name}_segment_layer"
    arcpy.lr.MakeRouteEventLayer(
        in_routes=route_fc,
        route_id_field=route_id_field,
        in_table=segment_table,
        in_event_properties=f"{route_id_field} LINE FMEAS TMEAS",
        out_layer=segment_layer,
    )

    # segment_table has served its purpose — delete it now so it does not
    # appear as a stale intermediate in the output GDB.
    arcpy.management.Delete(segment_table)

    segment_fc = os.path.join(out_gdb, f"{base_name}_segment_fc")
    if arcpy.Exists(segment_fc):
        arcpy.management.Delete(segment_fc)

    arcpy.management.CopyFeatures(segment_layer, segment_fc)
    return segment_fc
