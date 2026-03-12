import arcpy
import os

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

    # Add FromM and ToM fields so route can start at custom measure
    diss_fields = [f.name for f in arcpy.ListFields(route_diss)]

    if "FromM" not in diss_fields:
        arcpy.management.AddField(route_diss, "FromM", "DOUBLE")

    if "ToM" not in diss_fields:
        arcpy.management.AddField(route_diss, "ToM", "DOUBLE")

    arcpy.management.CalculateField(
        route_diss,
        "FromM",
        str(float(start_measure)),
        "PYTHON3"
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
        code_block
    )

    # Final route output
    route_fc = os.path.join(output_gdb, base_name + "_route")
    arcpy.lr.CreateRoutes(
        route_diss,
        route_id_field,
        route_fc,
        "TWO_FIELDS",
        "FromM",
        "ToM"
    )

    # Decide which line to use for generating station points
    station_source_fc = route_fc
    segment_table = None
    segment_fc = None

    if end_measure is not None:
        segment_table = os.path.join(output_gdb, base_name + "_segment_event")
        if arcpy.Exists(segment_table):
            arcpy.management.Delete(segment_table)

        arcpy.management.CreateTable(output_gdb, base_name + "_segment_event")

        seg_fields = [f.name for f in arcpy.ListFields(segment_table)]
        if route_id_field not in seg_fields:
            arcpy.management.AddField(segment_table, route_id_field, "TEXT", field_length=50)
        if "FMEAS" not in seg_fields:
            arcpy.management.AddField(segment_table, "FMEAS", "DOUBLE")
        if "TMEAS" not in seg_fields:
            arcpy.management.AddField(segment_table, "TMEAS", "DOUBLE")

        with arcpy.da.InsertCursor(segment_table, [route_id_field, "FMEAS", "TMEAS"]) as cur:
            cur.insertRow([route_id_value, float(start_measure), float(end_measure)])

        segment_layer = base_name + "_segment_lyr"
        arcpy.lr.MakeRouteEventLayer(
            in_routes=route_fc,
            route_id_field=route_id_field,
            in_table=segment_table,
            in_event_properties=f"{route_id_field} LINE FMEAS TMEAS",
            out_layer=segment_layer,
        )

        segment_fc = os.path.join(output_gdb, base_name + "_segment_fc")
        if arcpy.Exists(segment_fc):
            arcpy.management.Delete(segment_fc)

        arcpy.management.CopyFeatures(segment_layer, segment_fc)
        station_source_fc = segment_fc

    # Final station points output
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
        station_points,
        "StationID",
        "!OBJECTID!",
        "PYTHON3"
    )

    # Final station event table output
    station_table = os.path.join(output_gdb, base_name + "_station_events")
    if arcpy.Exists(station_table):
        arcpy.management.Delete(station_table)

    # Always locate points on the FULL route
    arcpy.lr.LocateFeaturesAlongRoutes(
        in_features=station_points,
        in_routes=route_fc,
        route_id_field=route_id_field,
        out_table=station_table,
        out_event_properties=f"{route_id_field} POINT MEAS",
        radius_or_tolerance=tolerance,
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

    remove_duplicate_station_measures(
    station_points=station_points,
    station_table=station_table,
    measure_field="MEAS"
)

    # Delete temporary datasets
    if arcpy.Exists(line_copy_fc):
        arcpy.management.Delete(line_copy_fc)

    if arcpy.Exists(route_diss):
        arcpy.management.Delete(route_diss)

    if segment_table and arcpy.Exists(segment_table):
        arcpy.management.Delete(segment_table)

    return {
        "route_fc": route_fc,
        "station_source_fc": station_source_fc,
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
    route_fc, 
    route_id_field, 
    output_gdb, 
    tolerance,
    point_intersections, 
    line_overlaps
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
            radius_or_tolerance=tolerance,
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
        fields=["MEAS", "Chainage"]
    )

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
        route_diss,
        "FromM",
        str(float(start_measure)),
        "PYTHON3"
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
        code_block
    )

    route_fc = os.path.join(output_gdb, base_name + "_route")
    arcpy.lr.CreateRoutes(
        route_diss,
        route_id_field,
        route_fc,
        "TWO_FIELDS",
        "FromM",
        "ToM"
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
    """
    Returns the line feature class on which points should be generated.
    If no end_measure is provided, use the full route.
    If end_measure is provided, create a route event segment and return that segment.
    """

    # No range limitation: use full route
    if end_measure is None:
        return route_fc

    segment_table = os.path.join(output_gdb, f"{base_name}_segment_event")
    if arcpy.Exists(segment_table):
        arcpy.management.Delete(segment_table)

    arcpy.management.CreateTable(output_gdb, f"{base_name}_segment_event")

    seg_fields = [f.name for f in arcpy.ListFields(segment_table)]
    if route_id_field not in seg_fields:
        arcpy.management.AddField(segment_table, route_id_field, "TEXT", field_length=50)
    if "FMEAS" not in seg_fields:
        arcpy.management.AddField(segment_table, "FMEAS", "DOUBLE")
    if "TMEAS" not in seg_fields:
        arcpy.management.AddField(segment_table, "TMEAS", "DOUBLE")

    with arcpy.da.InsertCursor(segment_table, [route_id_field, "FMEAS", "TMEAS"]) as cur:
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

def remove_duplicate_station_measures(station_points, station_table, measure_field="MEAS"):

    #Find duplicate StationIDs in station_table based on MEAS ---
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

    #Delete duplicate rows from station_table ---
    with arcpy.da.UpdateCursor(station_table, ["StationID"]) as cursor:
        for row in cursor:
            if row[0] in duplicate_station_ids_set:
                cursor.deleteRow()

    #Delete duplicate points from station_points ---
    with arcpy.da.UpdateCursor(station_points, ["StationID"]) as cursor:
        for row in cursor:
            if row[0] in duplicate_station_ids_set:
                cursor.deleteRow()

class Toolbox(object):
    def __init__(self):
        self.label = "Generate Stationing Tool"
        self.alias = "stationingtool"
        self.tools = [GenerateStationing]


class GenerateStationing(object):
    def __init__(self):
        self.label = "Generating Stationing"
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
        try:
            output_gdb.value = arcpy.mp.ArcGISProject("CURRENT").defaultGeodatabase
        except:
            pass

        station_interval = arcpy.Parameter(
            displayName="Station Interval",
            name="station_interval",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="Input",
        )
        station_interval.value = "100 Meters"

        tolerance = arcpy.Parameter(
            displayName="Search Tolerance",
            name="tolerance",
            datatype="GPLinearUnit",
            parameterType="Optional",
            direction="Input",
        )

        tolerance.value = "1 Meters"

        analysis_layers = arcpy.Parameter(
            displayName="Overlapping and Intersecting Features",
            name="analysis_layers",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input",
            #multiValue=True,
        )

        start_measure = arcpy.Parameter(
            displayName="Start Measure",
            name="start_measure",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        start_measure.value = 0

        end_measure = arcpy.Parameter(
            displayName="End Measure",
            name="end_measure",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )

        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            active_map = aprx.activeMap

            if active_map:
                polyline_layers = []
                for lyr in active_map.listLayers():
                    if lyr.isFeatureLayer:
                        try:
                            if lyr.isBroken:
                                continue
                            desc = arcpy.Describe(lyr.dataSource)
                            if desc.shapeType == "Polyline":
                                polyline_layers.append(lyr.name)
                        except:
                            pass
            if polyline_layers:            
                input_line.filter.list = polyline_layers
        except:
            pass

        #Desriptions to tools that shows when you hover the parameter
        input_line.description = "Select the main polyline feature to station."
        output_gdb.description = "Choose the output file geodatabase."
        station_interval.description = "Distance between station points. Example: 100 Meters."
        start_measure.description = "Optional route start measure. Example: 2100 means station 2+100."
        end_measure.description = "Optional route end measure. Leave blank to process to the end."
        tolerance.description = "Tolerance for locating features along the route."
        analysis_layers.description = "Optional layers to analyze for intersections and overlaps."

        return [input_line, 
                output_gdb, 
                station_interval, 
                start_measure, 
                end_measure, 
                tolerance, 
                analysis_layers
                ]
    
    def updateMessages(self, parameters):
        input_line = parameters[0]
        output_gdb = parameters[1]
        station_interval = parameters[2]
        start_measure = parameters[3]
        end_measure = parameters[4]
        tolerance = parameters[5]
        analysis_layers = parameters[6]

        # Validate tolerance
        if tolerance.value:
            try:
                tol = float(tolerance.valueAsText.split()[0])

                if tol <= 0:
                    tolerance.setErrorMessage(
                        "Tolerance must be greater than zero."
                    )
                elif tol > 100:
                    tolerance.setWarningMessage(
                        "Large tolerance may snap unrelated features to the route."
                    )
            except:
                tolerance.setErrorMessage(
                    "Invalid tolerance value. Example: 1 Meters."
                )

        # Warn if no active map exists
        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            if aprx.activeMap is None:
                input_line.setWarningMessage(
                    "No active map detected. You may need to browse to input layers manually."
                )
        except:
            input_line.setWarningMessage(
                "Could not access the current ArcGIS Pro project. Browse to inputs manually if needed."
            )

        # Validate input route feature
        if input_line.value:
            try:
                desc = arcpy.Describe(input_line.valueAsText)

                if not hasattr(desc, "shapeType"):
                    input_line.setErrorMessage("Input must be a valid feature layer.")
                elif desc.shapeType != "Polyline":
                    input_line.setErrorMessage(
                        "Input Linear Feature must be a polyline feature class or layer."
                    )
            except Exception as e:
                input_line.setErrorMessage(f"Invalid input feature: {e}")

        # Validate output workspace is a geodatabase
        if output_gdb.value:
            try:
                out_path = output_gdb.valueAsText
                desc = arcpy.Describe(out_path)

                workspace_type = getattr(desc, "workspaceType", None)
                extension = os.path.splitext(out_path)[1].lower()

                if workspace_type != "LocalDatabase" and extension != ".gdb":
                    output_gdb.setErrorMessage(
                        "Output workspace must be a file geodatabase (.gdb)."
                    )
            except Exception as e:
                output_gdb.setErrorMessage(f"Invalid output workspace: {e}")

        # Validate station interval
        if station_interval.value:
            try:
                interval_text = station_interval.valueAsText
                parts = interval_text.split()

                if len(parts) < 2:
                    station_interval.setErrorMessage(
                        "Station Interval must include a number and unit, for example: 100 Meters."
                    )
                else:
                    numeric_value = float(parts[0])

                    if numeric_value <= 0:
                        station_interval.setErrorMessage(
                            "Station Interval must be greater than zero."
                        )
                    elif numeric_value < 0.01:
                        station_interval.setWarningMessage(
                            "Station Interval is extremely small. This may create too many points."
                        )
                    elif numeric_value < 1:
                        station_interval.setWarningMessage(
                            "Station Interval is very small. Confirm this is intentional."
                        )
            except Exception:
                station_interval.setErrorMessage(
                    "Invalid Station Interval. Example valid input: 100 Meters."
                )

        # Warn if end measure is provided but start measure is empty
        if start_measure.value is None and end_measure.value is not None:
            start_measure.setWarningMessage(
                "Start Measure is empty. The tool will assume 0."
            )

        # Validate start measure
        if start_measure.value is not None:
            try:
                sm = float(start_measure.value)

                if sm < 0:
                    start_measure.setWarningMessage(
                        "Start Measure is negative. Confirm this is intentional."
                    )
            except Exception:
                start_measure.setErrorMessage("Start Measure must be numeric.")

        # Validate end measure
        if end_measure.value is not None:
            try:
                float(end_measure.value)
            except Exception:
                end_measure.setErrorMessage("End Measure must be numeric.")

        # Validate relationship between start and end measure
        if start_measure.value is not None and end_measure.value is not None:
            try:
                sm = float(start_measure.value)
                em = float(end_measure.value)

                if em <= sm:
                    end_measure.setErrorMessage(
                        "End Measure must be greater than Start Measure."
                    )
                elif (em - sm) < 1:
                    end_measure.setWarningMessage(
                        "The selected measure range is very short."
                    )
            except Exception:
                pass

        # Validate analysis layers
        if analysis_layers.value:
            try:
                layer_list = analysis_layers.valueAsText.split(";")

                for lyr in layer_list:
                    lyr = lyr.strip().strip("'").strip('"')
                    if not lyr:
                        continue

                    try:
                        desc = arcpy.Describe(lyr)

                        if not hasattr(desc, "shapeType"):
                            analysis_layers.setErrorMessage(
                                f"Analysis layer '{lyr}' is not a valid feature layer."
                            )
                            return

                        if input_line.value:
                            try:
                                in_desc = arcpy.Describe(input_line.valueAsText)
                                lyr_desc = arcpy.Describe(lyr)

                                if hasattr(in_desc, "catalogPath") and hasattr(lyr_desc, "catalogPath"):
                                    if os.path.normpath(in_desc.catalogPath) == os.path.normpath(lyr_desc.catalogPath):
                                        analysis_layers.setWarningMessage(
                                            "Input route layer is also included in analysis layers. It will be skipped during processing."
                                        )
                            except:
                                pass

                    except Exception as e:
                        analysis_layers.setErrorMessage(
                            f"Analysis layer '{lyr}' is invalid or broken: {e}"
                        )
                        return

            except Exception as e:
                analysis_layers.setErrorMessage(f"Invalid analysis layers: {e}")
        
    def execute(self, parameters, messages):
        arcpy.env.overwriteOutput = True

        input_line_fc = parameters[0].valueAsText
        output_gdb = parameters[1].valueAsText
        station_interval = parameters[2].valueAsText

        start_measure=0
        if parameters [3].value is not None:
            start_measure=float(parameters[3].value)

        end_measure=None
        if parameters[4].value is not None:
            end_measure=float(parameters[4].value)
            
        analysis_layers_text = parameters[5].valueAsText

        tolerance = "1 Meters"
        if len(parameters) > 6 and parameters[6].valueAsText:
            tolerance = parameters[6].valueAsText

        analysis_layers = []
        if analysis_layers_text:
            analysis_layers = analysis_layers_text.split(";")

        messages.addMessage("Creating route and stationing...")

        outputs = create_route_and_stationing(
            input_line_fc=input_line_fc,
            output_gdb=output_gdb,
            station_interval=station_interval,
            start_measure=start_measure,
            end_measure=end_measure,
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
                tolerance=tolerance,
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
