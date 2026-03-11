import arcpy
import os

def create_route_and_stationing(
    input_line_fc,
    output_gdb,
    station_interval,
    route_id_field="Route_ID",
    route_id_value="ROUTE_01",
):
    desc = arcpy.Describe(input_line_fc)
    catalog_path = desc.catalogPath

    base_name = arcpy.ValidateTableName(
        os.path.splitext(os.path.basename(catalog_path))[0], output_gdb
    )

    # Temporary copy
    line_copy_fc = os.path.join(output_gdb, base_name + "_copy")
    arcpy.management.CopyFeatures(input_line_fc, line_copy_fc)

    # Add route ID field if missing
    field_names = [f.name for f in arcpy.ListFields(line_copy_fc)]
    if route_id_field not in field_names:
        arcpy.management.AddField(line_copy_fc, route_id_field, "TEXT", field_length=50)

    # Assign one route ID to all features
    arcpy.management.CalculateField(
        line_copy_fc, route_id_field, f"'{route_id_value}'", "PYTHON3"
    )

    # Temporary dissolve
    route_diss = os.path.join(output_gdb, base_name + "_dissolve")
    arcpy.management.Dissolve(line_copy_fc, route_diss, route_id_field)

    # Final route output
    route_fc = os.path.join(output_gdb, base_name + "_route")
    arcpy.lr.CreateRoutes(route_diss, route_id_field, route_fc, "LENGTH")

    # Final station points output
    station_points = os.path.join(output_gdb, base_name + "_station_points")
    arcpy.management.GeneratePointsAlongLines(
        route_fc,
        station_points,
        "DISTANCE",
        Distance=station_interval,
        Include_End_Points="END_POINTS",
    )

    if "StationID" not in [f.name for f in arcpy.ListFields(station_points)]:
        arcpy.management.AddField(station_points, "StationID", "LONG")

    arcpy.management.CalculateField(
        station_points,
        "StationID",
        "!OBJECTID!",
        "PYTHON3"
    )

    # Final station event table output
    station_table = os.path.join(output_gdb, base_name + "_station_events")
    arcpy.lr.LocateFeaturesAlongRoutes(
        in_features=station_points,
        in_routes=route_fc,
        route_id_field=route_id_field,
        out_table=station_table,
        out_event_properties=f"{route_id_field} POINT MEAS",
        radius_or_tolerance="1 Meters",
        distance_field="DISTANCE",
    )

    # Add Chainage field
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

    # Delete temporary datasets
    if arcpy.Exists(line_copy_fc):
        arcpy.management.Delete(line_copy_fc)

    if arcpy.Exists(route_diss):
        arcpy.management.Delete(route_diss)

    return {
        "route_fc": route_fc,
        "station_points": station_points,
        "station_table": station_table,
        "route_id_field": route_id_field,
    }


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

            # Point intersection output
            point_out = os.path.join(output_gdb, f"{layer_name}_point")
            arcpy.analysis.Intersect([route_fc, lyr], point_out, output_type="POINT")

            if int(arcpy.management.GetCount(point_out)[0]) > 0:
                point_intersections.append(point_out)
            else:
                arcpy.management.Delete(point_out)

            # Overlap output for line and polygon layers
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

    return {"point_intersections": point_intersections, "line_overlaps": line_overlaps}


def locate_intersections_and_overlaps(
    route_fc, route_id_field, output_gdb, point_intersections, line_overlaps
):
    point_event_tables = []
    line_event_tables = []

    # Point events
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
            radius_or_tolerance="1 Meters",
            distance_field="DISTANCE",
        )

        if int(arcpy.management.GetCount(out_table)[0]) > 0:
            point_event_tables.append(out_table)
        else:
            arcpy.management.Delete(out_table)

    # Line events
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
            radius_or_tolerance="1 Meters",
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

    # Point event tables
    for table in point_event_tables:
        existing_fields = [f.name for f in arcpy.ListFields(table)]

        if "Chainage" not in existing_fields:
            arcpy.management.AddField(table, "Chainage", "TEXT", field_length=20)

        arcpy.management.CalculateField(
            table, "Chainage", "chain(!MEAS!)", "PYTHON3", code_block
        )

    # Line event tables
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

    # Point event layers
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

    # Line event layers
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

def join_station_chainage_to_points(station_points, station_table):

    point_fields = [f.name for f in arcpy.ListFields(station_points)]
    if "Chainage" in point_fields:
        arcpy.management.DeleteField(station_points, "Chainage")
 
    arcpy.management.JoinField(
        in_data=station_points,
        in_field="StationID",
        join_table=station_table,
        join_field="StationID",
        fields=["Chainage"]
    )

class Toolbox(object):
    def __init__(self):
        self.label = "Generate Stationing Tool"
        self.alias = "stationingtool"
        self.tools = [GenerateStationing]


class GenerateStationing(object):
    def __init__(self):
        self.label = "Generate Stationing"
        self.description = "Creates a route and station points from any linear feature."

    def getParameterInfo(self):
        input_line = arcpy.Parameter(
            displayName="Input Linear Feature",
            name="input_line",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        output_gdb = arcpy.Parameter(
            displayName="Output Geodatabase",
            name="output_gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input",
        )

        # setting default gdb
        output_gdb.value = arcpy.mp.ArcGISProject("CURRENT").defaultGeodatabase

        station_interval = arcpy.Parameter(
            displayName="Station Interval",
            name="station_interval",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="Input",
        )
        station_interval.value = "100 Meters"

        analysis_layers = arcpy.Parameter(
            displayName="Overlapping and Intersecting Features",
            name="analysis_layers",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input",
            multiValue=True,
        )

        aprx = arcpy.mp.ArcGISProject("CURRENT")
        active_map = aprx.activeMap

        if active_map:
            polyline_layers = []
            for lyr in active_map.listLayers():
                if lyr.isFeatureLayer:
                    try:
                        desc = arcpy.Describe(lyr.dataSource)
                        if desc.shapeType == "Polyline":
                            polyline_layers.append(lyr.name)
                    except:
                        pass
            input_line.filter.list = polyline_layers

        return [input_line, output_gdb, station_interval, analysis_layers]
    
    def execute(self, parameters, messages):
        arcpy.env.overwriteOutput = True
        input_line_fc = parameters[0].valueAsText
        output_gdb = parameters[1].valueAsText
        station_interval = parameters[2].valueAsText
        analysis_layers_text = parameters[3].valueAsText

        analysis_layers = []
        if analysis_layers_text:
            analysis_layers = analysis_layers_text.split(";")

        messages.addMessage("Creating route and stationing...")

        outputs = create_route_and_stationing(
            input_line_fc=input_line_fc,
            output_gdb=output_gdb,
            station_interval=station_interval,
        )

        messages.addMessage(f"Route created: {outputs['route_fc']}")
        messages.addMessage(f"Station points created: {outputs['station_points']}")
        messages.addMessage(f"Station event table created: {outputs['station_table']}")

        # Join chainage to station points first
        join_station_chainage_to_points(
            station_points=outputs["station_points"],
            station_table=outputs["station_table"]
        )
        messages.addMessage("Chainage joined to station points.")

        # Only do crossings/overlaps if optional layers were provided
        if analysis_layers:
            messages.addMessage("Creating intersections and overlaps...")

            crossing_outputs = create_intersections_and_overlaps(
                route_fc=outputs["route_fc"],
                output_gdb=output_gdb,
                analysis_layers=analysis_layers,
            )

            messages.addMessage(
                f"Point intersections created: {len(crossing_outputs['point_intersections'])}"
            )
            messages.addMessage(
                f"Line overlaps created: {len(crossing_outputs['line_overlaps'])}"
            )

            messages.addMessage("Locating intersections and overlaps along route...")

            event_outputs = locate_intersections_and_overlaps(
                route_fc=outputs["route_fc"],
                route_id_field=outputs["route_id_field"],
                output_gdb=output_gdb,
                point_intersections=crossing_outputs["point_intersections"],
                line_overlaps=crossing_outputs["line_overlaps"],
            )

            messages.addMessage(
                f"Point event tables created: {len(event_outputs['point_event_tables'])}"
            )
            messages.addMessage(
                f"Line event tables created: {len(event_outputs['line_event_tables'])}"
            )

            messages.addMessage("Calculating chainage for event tables...")

            add_chainage_to_event_tables(
                point_event_tables=event_outputs["point_event_tables"],
                line_event_tables=event_outputs["line_event_tables"],
            )

            messages.addMessage("Chainage fields added to event tables.")

            messages.addMessage("Creating event feature layers...")

            event_feature_outputs = make_event_layers_from_tables(
                route_fc=outputs["route_fc"],
                route_id_field=outputs["route_id_field"],
                output_gdb=output_gdb,
                point_event_tables=event_outputs["point_event_tables"],
                line_event_tables=event_outputs["line_event_tables"],
            )

            messages.addMessage(
                f"Point event features created: {len(event_feature_outputs['point_event_features'])}"
            )
            messages.addMessage(
                f"Line event features created: {len(event_feature_outputs['line_event_features'])}"
            )

        else:
            messages.addMessage("No analysis layers provided. Skipping intersections and overlaps.")
