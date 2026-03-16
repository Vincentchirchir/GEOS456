# route_utils.py
import arcpy
import os


def create_route_with_measure_system(
    input_line_fc,
    output_gdb,
    start_measure=0,
    route_id_field="Route_ID",
    route_id_value="ROUTE_01",
):
    desc = arcpy.Describe(input_line_fc)
    catalog_path = desc.catalogPath

    base_name = arcpy.ValidateTableName(
        os.path.splitext(os.path.basename(catalog_path))[0], output_gdb
    )

    line_copy_fc = os.path.join(output_gdb, base_name + "_copy")
    arcpy.management.CopyFeatures(input_line_fc, line_copy_fc)

    field_names = [f.name for f in arcpy.ListFields(line_copy_fc)]
    if route_id_field not in field_names:
        arcpy.management.AddField(line_copy_fc, route_id_field, "TEXT", field_length=50)

    arcpy.management.CalculateField(
        line_copy_fc, route_id_field, f"'{route_id_value}'", "PYTHON3"
    )

    route_diss = os.path.join(output_gdb, base_name + "_dissolve")
    arcpy.management.Dissolve(line_copy_fc, route_diss, route_id_field)

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

    route_fc = os.path.join(output_gdb, base_name + "_route")
    arcpy.lr.CreateRoutes(
        route_diss, route_id_field, route_fc, "TWO_FIELDS", "FromM", "ToM"
    )

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
    output_gdb,
    base_name,
    route_id_field,
    route_id_value,
    start_measure=None,
    end_measure=None,
):
    if end_measure is None:
        return route_fc

    segment_table = os.path.join(output_gdb, f"{base_name}_segment_event")
    if arcpy.Exists(segment_table):
        arcpy.management.Delete(segment_table)

    arcpy.management.CreateTable(output_gdb, f"{base_name}_segment_event")

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
    ) as cur:
        cur.insertRow([route_id_value, float(start_measure), float(end_measure)])

    segment_layer = f"{base_name}_segment_lyr"
    arcpy.lr.MakeRouteEventLayer(
        in_routes=route_fc,
        route_id_field=route_id_field,
        in_table=segment_table,
        in_event_properties=f"{route_id_field} LINE FMEAS TMEAS",
        out_layer=segment_layer,
    )

    segment_fc = os.path.join(output_gdb, f"{base_name}_segment_fc")
    if arcpy.Exists(segment_fc):
        arcpy.management.Delete(segment_fc)

    arcpy.management.CopyFeatures(segment_layer, segment_fc)
    return segment_fc


# stationing_utils.py
import arcpy
import os

from route_utils import create_route_with_measure_system, create_stationing_source_line


def remove_duplicate_station_measures(
    station_points, station_table, measure_field="MEAS"
):
    seen_measures = set()
    duplicate_station_ids = []

    with arcpy.da.SearchCursor(station_table, ["StationID", measure_field]) as cursor:
        for station_id, meas in cursor:
            key = round(float(meas), 6) if meas is not None else None

            if key in seen_measures:
                duplicate_station_ids.append(station_id)
            else:
                seen_measures.add(key)

    if not duplicate_station_ids:
        return

    duplicate_station_ids_set = set(duplicate_station_ids)

    with arcpy.da.UpdateCursor(station_table, ["StationID"]) as cursor:
        for row in cursor:
            if row[0] in duplicate_station_ids_set:
                cursor.deleteRow()

    with arcpy.da.UpdateCursor(station_points, ["StationID"]) as cursor:
        for row in cursor:
            if row[0] in duplicate_station_ids_set:
                cursor.deleteRow()


def join_station_chainage_to_points(station_points, station_table):
    point_fields = [f.name for f in arcpy.ListFields(station_points)]

    fields_to_delete = []
    for fld in ["Chainage", "MEAS", "FMEAS", "TMEAS"]:
        if fld in point_fields:
            fields_to_delete.append(fld)

    if fields_to_delete:
        arcpy.management.DeleteField(station_points, fields_to_delete)

    arcpy.management.JoinField(
        in_data=station_points,
        in_field="StationID",
        join_table=station_table,
        join_field="StationID",
        fields=["MEAS", "Chainage"],
    )


def create_route_and_stationing(
    input_line_fc,
    output_gdb,
    station_interval,
    tolerance,
    start_measure=0,
    end_measure=None,
    route_id_field="Route_ID",
    route_id_value="ROUTE_01",
):
    route_info = create_route_with_measure_system(
        input_line_fc=input_line_fc,
        output_gdb=output_gdb,
        start_measure=start_measure,
        route_id_field=route_id_field,
        route_id_value=route_id_value,
    )

    route_fc = route_info["route_fc"]
    base_name = route_info["base_name"]

    station_source_fc = create_stationing_source_line(
        route_fc=route_fc,
        output_gdb=output_gdb,
        base_name=base_name,
        route_id_field=route_id_field,
        route_id_value=route_id_value,
        start_measure=start_measure,
        end_measure=end_measure,
    )

    station_points = os.path.join(output_gdb, base_name + "_station_points")
    if arcpy.Exists(station_points):
        arcpy.management.Delete(station_points)

    arcpy.management.GeneratePointsAlongLines(
        station_source_fc,
        station_points,
        "DISTANCE",
        Distance=station_interval,
        Include_End_Points="END_POINTS",
    )

    if "StationID" not in [f.name for f in arcpy.ListFields(station_points)]:
        arcpy.management.AddField(station_points, "StationID", "LONG")

    arcpy.management.CalculateField(
        station_points, "StationID", "!OBJECTID!", "PYTHON3"
    )

    station_table = os.path.join(output_gdb, base_name + "_station_events")
    if arcpy.Exists(station_table):
        arcpy.management.Delete(station_table)

    arcpy.lr.LocateFeaturesAlongRoutes(
        in_features=station_points,
        in_routes=route_fc,
        route_id_field=route_id_field,
        out_table=station_table,
        out_event_properties=f"{route_id_field} POINT MEAS",
        radius_or_tolerance=tolerance,
        distance_field="DISTANCE",
    )

    table_fields = [f.name for f in arcpy.ListFields(station_table)]
    if "Chainage" not in table_fields:
        arcpy.management.AddField(station_table, "Chainage", "TEXT", field_length=20)

    calculate_field_code = r"""
def chain(val):
    val = int(round(float(val)))
    km = val // 1000
    remainder = val % 1000
    return f"{km}+{remainder:03d}"
"""

    arcpy.management.CalculateField(
        station_table, "Chainage", "chain(!MEAS!)", "PYTHON3", calculate_field_code
    )

    remove_duplicate_station_measures(
        station_points=station_points, station_table=station_table, measure_field="MEAS"
    )

    return {
        "route_fc": route_fc,
        "station_source_fc": station_source_fc,
        "station_points": station_points,
        "station_table": station_table,
        "route_id_field": route_id_field,
    }


# event_utils.py
import arcpy
import os


def create_intersections_and_overlaps(route_fc, output_gdb, analysis_layers):
    point_intersections = []
    line_overlaps = []

    route_name = os.path.splitext(os.path.basename(route_fc))[0]

    for lyr in analysis_layers:
        try:
            desc = arcpy.Describe(lyr)
            layer_name = arcpy.ValidateTableName(desc.baseName, output_gdb)
            shape_type = desc.shapeType

            if layer_name.lower() == route_name.lower():
                continue

            point_out = os.path.join(output_gdb, f"{layer_name}_point")
            arcpy.analysis.Intersect([route_fc, lyr], point_out, output_type="POINT")

            if int(arcpy.management.GetCount(point_out)[0]) > 0:
                point_intersections.append(point_out)
            else:
                arcpy.management.Delete(point_out)

            if shape_type in ["Polyline", "Polygon"]:
                overlap_out = os.path.join(output_gdb, f"{layer_name}_overlap")
                arcpy.analysis.Intersect(
                    [route_fc, lyr], overlap_out, output_type="LINE"
                )

                if int(arcpy.management.GetCount(overlap_out)[0]) > 0:
                    line_overlaps.append(overlap_out)
                else:
                    arcpy.management.Delete(overlap_out)

        except Exception as e:
            arcpy.AddWarning(f"Skipped layer {lyr}: {e}")

    return {
        "point_intersections": point_intersections,
        "line_overlaps": line_overlaps,
    }


def locate_intersections_and_overlaps(
    route_fc, route_id_field, output_gdb, tolerance, point_intersections, line_overlaps
):
    point_event_tables = []
    line_event_tables = []

    for point_fc in point_intersections:
        point_name = arcpy.ValidateTableName(
            os.path.splitext(os.path.basename(point_fc))[0], output_gdb
        )
        out_table = os.path.join(output_gdb, f"{point_name}_event")

        arcpy.lr.LocateFeaturesAlongRoutes(
            in_features=point_fc,
            in_routes=route_fc,
            route_id_field=route_id_field,
            out_table=out_table,
            out_event_properties=f"{route_id_field} POINT MEAS",
            radius_or_tolerance=tolerance,
            distance_field="DISTANCE",
        )

        if int(arcpy.management.GetCount(out_table)[0]) > 0:
            point_event_tables.append(out_table)
        else:
            arcpy.management.Delete(out_table)

    for overlap_fc in line_overlaps:
        overlap_name = arcpy.ValidateTableName(
            os.path.splitext(os.path.basename(overlap_fc))[0], output_gdb
        )
        out_table = os.path.join(output_gdb, f"{overlap_name}_event")

        arcpy.lr.LocateFeaturesAlongRoutes(
            in_features=overlap_fc,
            in_routes=route_fc,
            route_id_field=route_id_field,
            out_table=out_table,
            out_event_properties=f"{route_id_field} LINE FMEAS TMEAS",
            radius_or_tolerance=tolerance,
            distance_field="DISTANCE",
        )

        if int(arcpy.management.GetCount(out_table)[0]) > 0:
            line_event_tables.append(out_table)
        else:
            arcpy.management.Delete(out_table)

    return {
        "point_event_tables": point_event_tables,
        "line_event_tables": line_event_tables,
    }


def chainage_code_block():
    return r"""
def chain(val):
    val = int(round(float(val)))
    km = val // 1000
    remainder = val % 1000
    return f"{km}+{remainder:03d}"
"""


def add_chainage_to_event_tables(point_event_tables, line_event_tables):
    code_block = chainage_code_block()

    for table in point_event_tables:
        existing_fields = [f.name for f in arcpy.ListFields(table)]

        if "Chainage" not in existing_fields:
            arcpy.management.AddField(table, "Chainage", "TEXT", field_length=20)

        arcpy.management.CalculateField(
            table, "Chainage", "chain(!MEAS!)", "PYTHON3", code_block
        )

    for table in line_event_tables:
        existing_fields = [f.name for f in arcpy.ListFields(table)]

        if "FromCh" not in existing_fields:
            arcpy.management.AddField(table, "FromCh", "TEXT", field_length=20)

        if "ToCh" not in existing_fields:
            arcpy.management.AddField(table, "ToCh", "TEXT", field_length=20)

        if "ChainageRange" not in existing_fields:
            arcpy.management.AddField(table, "ChainageRange", "TEXT", field_length=30)

        arcpy.management.CalculateField(
            table, "FromCh", "chain(!FMEAS!)", "PYTHON3", code_block
        )

        arcpy.management.CalculateField(
            table, "ToCh", "chain(!TMEAS!)", "PYTHON3", code_block
        )

        arcpy.management.CalculateField(
            table, "ChainageRange", "!FromCh! + ' - ' + !ToCh!", "PYTHON3"
        )


def make_event_layers_from_tables(
    route_fc, route_id_field, output_gdb, point_event_tables, line_event_tables
):
    point_event_features = []
    line_event_features = []

    for table in point_event_tables:
        base_name = arcpy.ValidateTableName(
            os.path.splitext(os.path.basename(table))[0], output_gdb
        )

        out_layer = f"{base_name}_lyr"
        out_fc = os.path.join(output_gdb, f"{base_name}_fc")

        arcpy.lr.MakeRouteEventLayer(
            in_routes=route_fc,
            route_id_field=route_id_field,
            in_table=table,
            in_event_properties=f"{route_id_field} POINT MEAS",
            out_layer=out_layer,
        )

        arcpy.management.CopyFeatures(out_layer, out_fc)
        point_event_features.append(out_fc)

    for table in line_event_tables:
        base_name = arcpy.ValidateTableName(
            os.path.splitext(os.path.basename(table))[0], output_gdb
        )

        out_layer = f"{base_name}_lyr"
        out_fc = os.path.join(output_gdb, f"{base_name}_fc")

        arcpy.lr.MakeRouteEventLayer(
            in_routes=route_fc,
            route_id_field=route_id_field,
            in_table=table,
            in_event_properties=f"{route_id_field} LINE FMEAS TMEAS",
            out_layer=out_layer,
        )

        arcpy.management.CopyFeatures(out_layer, out_fc)
        line_event_features.append(out_fc)

    return {
        "point_event_features": point_event_features,
        "line_event_features": line_event_features,
    }


# map_utils.py
import arcpy


def add_outputs_to_current_map(outputs):
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        active_map = aprx.activeMap

        if not active_map:
            return

        route_layer = active_map.addDataFromPath(outputs["route_fc"])
        station_layer = active_map.addDataFromPath(outputs["station_points"])

        sym = route_layer.symbology
        if sym.renderer.type == "SimpleRenderer":
            sym.renderer.symbol.color = {"RGB": [255, 0, 0, 100]}
            sym.renderer.symbol.width = 4
        route_layer.symbology = sym

        sym = station_layer.symbology
        if sym.renderer.type == "SimpleRenderer":
            sym.renderer.symbol.color = {"RGB": [0, 0, 255, 100]}
            sym.renderer.symbol.size = 6
        station_layer.symbology = sym

        view = aprx.activeView
        if hasattr(view, "camera"):
            extent = arcpy.Describe(outputs["route_fc"]).extent
            view.camera.setExtent(extent)

        station_layer.showLabels = True
        for lbl in station_layer.listLabelClasses():
            lbl.expression = "$feature.Chainage"

    except Exception as e:
        arcpy.AddWarning(f"Could not update map display: {e}")


# Now your .pyt becomes much smaller

# At the top of GenerateStationing.pyt:

import arcpy
import os
import sys

tool_folder = os.path.dirname(__file__)
if tool_folder not in sys.path:
    sys.path.append(tool_folder)

from stationing_utils import (
    create_route_and_stationing,
    join_station_chainage_to_points,
)
from event_utils import (
    create_intersections_and_overlaps,
    locate_intersections_and_overlaps,
    add_chainage_to_event_tables,
    make_event_layers_from_tables,
)
from map_utils import add_outputs_to_current_map

# Then keep:

# Toolbox

# GenerateStationing

# getParameterInfo

# updateMessages

# And simplify execute() to mainly orchestrate.


# Your new execute() logic
def execute(self, parameters, messages):
    arcpy.env.overwriteOutput = True

    input_line_fc = parameters[0].valueAsText
    output_gdb = parameters[1].valueAsText
    station_interval = parameters[2].valueAsText

    start_measure = 0
    if parameters[3].value is not None:
        start_measure = float(parameters[3].value)

    end_measure = None
    if parameters[4].value is not None:
        end_measure = float(parameters[4].value)

    tolerance = "1 Meters"
    if parameters[5].valueAsText:
        tolerance = parameters[5].valueAsText

    analysis_layers = []
    if parameters[6].valueAsText:
        analysis_layers = parameters[6].valueAsText.split(";")

    messages.addMessage("Creating route and stationing...")

    outputs = create_route_and_stationing(
        input_line_fc=input_line_fc,
        output_gdb=output_gdb,
        station_interval=station_interval,
        tolerance=tolerance,
        start_measure=start_measure,
        end_measure=end_measure,
    )

    messages.addMessage(f"Route created: {outputs['route_fc']}")
    messages.addMessage(f"Station points created: {outputs['station_points']}")
    messages.addMessage(f"Station event table created: {outputs['station_table']}")

    join_station_chainage_to_points(
        station_points=outputs["station_points"], station_table=outputs["station_table"]
    )
    messages.addMessage("Chainage joined to station points.")

    if analysis_layers:
        messages.addMessage("Creating intersections and overlaps...")

        crossing_outputs = create_intersections_and_overlaps(
            route_fc=outputs["route_fc"],
            output_gdb=output_gdb,
            analysis_layers=analysis_layers,
        )

        event_outputs = locate_intersections_and_overlaps(
            route_fc=outputs["route_fc"],
            route_id_field=outputs["route_id_field"],
            tolerance=tolerance,
            output_gdb=output_gdb,
            point_intersections=crossing_outputs["point_intersections"],
            line_overlaps=crossing_outputs["line_overlaps"],
        )

        add_chainage_to_event_tables(
            point_event_tables=event_outputs["point_event_tables"],
            line_event_tables=event_outputs["line_event_tables"],
        )

        make_event_layers_from_tables(
            route_fc=outputs["route_fc"],
            route_id_field=outputs["route_id_field"],
            output_gdb=output_gdb,
            point_event_tables=event_outputs["point_event_tables"],
            line_event_tables=event_outputs["line_event_tables"],
        )
    else:
        messages.addMessage(
            "No analysis layers provided. Skipping intersections and overlaps."
        )

    add_outputs_to_current_map(outputs)
