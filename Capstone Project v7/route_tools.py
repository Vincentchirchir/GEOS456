import arcpy
import os
from types import SimpleNamespace


# This function prepares a route for route creation
def create_route_with_measure_system(
    input_line_fc,
    out_gdb,
    start_measure=0,
    route_id_field="ROUTE_ID",
    route_id_value="ROUTE_01",
):
    desc = arcpy.Describe(input_line_fc)
    catalog_path = desc.catalogPath

    base_name = arcpy.ValidateTableName(
        os.path.splitext(os.path.basename(catalog_path))[0], out_gdb
    )

    # Here we are creating a copy of the original line so that the script can work on the copy feature and not interefe with the original feature. But later we will delete and will not be there in the final gdb
    line_copy_fc = os.path.join(out_gdb, base_name + "_copy")
    arcpy.management.CopyFeatures(input_line_fc, line_copy_fc)

    # Add field value that contains values that uniquely identify each route.
    field_names = [f.name for f in arcpy.ListFields(line_copy_fc)]
    if route_id_field not in field_names:
        arcpy.management.AddField(line_copy_fc, route_id_field, "TEXT", field_length=50)

    # calculate field so that the route will have the same route attributes. In this case the attribute has been set to ROUTE_01. So the the column will have ROUTE_01 from start to end
    arcpy.management.CalculateField(
        in_table=line_copy_fc,
        field=route_id_field,
        expression=f"'{route_id_value}'",
        expression_type="PYTHON3",
    )

    # dissolving the line into one line incase if it is broken (This one applies only to one line. If you have a multiple lines and you want to treat them separately, then dissolve will not be used)
    route_diss = os.path.join(out_gdb, base_name + "_dissolve")
    arcpy.management.Dissolve(line_copy_fc, route_diss, route_id_field)

    # The script will have the option of chossing start and end for which you want to create route or intervals. So here we are adding field for From measure and To measure
    # This way we will be able to calculate the two fields
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

    # Here we are starting with the first part of linear referencing which is CREATE ROUTE.
    # The output of this tool will be a feature class written to gdb, and M Domains have been created
    route_output = os.path.join(out_gdb, base_name + "_route")
    arcpy.lr.CreateRoutes(
        route_diss, route_id_field, route_output, "TWO_FIELDS", "FromM", "ToM"
    )

    # Here we are deleting the line copy feature we had created earlier and the dissolved line
    # We are deleting because the route has been created which is the same and we still have the original copy of the line feature
    if arcpy.Exists(line_copy_fc):
        arcpy.management.Delete(line_copy_fc)
    if arcpy.Exists(route_diss):
        arcpy.management.Delete(route_diss)

    return SimpleNamespace(
        route=route_output,
        id_field=route_id_field,
        id_value=route_id_value,
        base=base_name,
    )


# The following function prepares for lines that station will be generated on
# Coz ecause sometimes you do not want to generate stations on the entire route exactly as-is.
# You may want trimming based on start_measure or trimming based on end_measure
def create_stationing_source_line(
    route_fc,
    out_gdb,
    base_name,
    route_id_field,
    route_id_value,
    start_measure=None,
    end_measure=None,
):
    if (
        end_measure is None
    ):  # Here we are telling the script if the user does not provide the end measure, just produce the intervals from the specified start to the end of the line coz there is not end specified
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

    segment_fc = os.path.join(out_gdb, f"{base_name}_segment_fc")
    if arcpy.Exists(segment_fc):
        arcpy.management.Delete(segment_fc)

    arcpy.management.CopyFeatures(segment_layer, segment_fc)
    return segment_fc
