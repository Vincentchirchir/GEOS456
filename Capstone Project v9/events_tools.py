import arcpy, os

LEADER_ANCHOR_ID_FIELD = "LeaderAnchorID"
POINT_EVENT_JOIN_FIELDS = ("Chainage", "MEAS", "DISTANCE")


def _ensure_leader_anchor_ids(point_fc):
    # Store a stable ID on the raw Intersect output so we can later join the
    # chainage results back onto the exact same point geometry.
    existing_fields = [f.name for f in arcpy.ListFields(point_fc)]

    if LEADER_ANCHOR_ID_FIELD not in existing_fields:
        arcpy.management.AddField(point_fc, LEADER_ANCHOR_ID_FIELD, "LONG")

    with arcpy.da.UpdateCursor(point_fc, ["OID@", LEADER_ANCHOR_ID_FIELD]) as cursor:
        for row in cursor:
            row[1] = row[0]
            cursor.updateRow(row)


def _explode_multipoint_intersections(point_fc):
    # Intersect can return one multipoint feature for multiple crossings.
    # LocateFeaturesAlongRoutes only stores one MEAS per input feature, so
    # split the geometry before locating measures to keep entry/exit points unique.
    desc = arcpy.Describe(point_fc)
    if desc.shapeType != "Multipoint":
        return point_fc

    single_fc = rf"{point_fc}_singlepart"

    if arcpy.Exists(single_fc):
        arcpy.management.Delete(single_fc)

    arcpy.management.MultipartToSinglepart(point_fc, single_fc)
    arcpy.management.Delete(point_fc)
    arcpy.management.CopyFeatures(single_fc, point_fc)
    arcpy.management.Delete(single_fc)

    return point_fc


def _build_point_intersection_lookup(point_intersections, output_gdb):
    lookup = {}

    for point_fc in point_intersections or []:
        point_name = arcpy.ValidateTableName(
            os.path.splitext(os.path.basename(point_fc))[0], output_gdb
        )
        lookup[point_name.lower()] = point_fc

    return lookup


def _copy_raw_intersections_with_chainage(point_fc, event_table, out_fc):
    # Copy the original point geometry first, then join the route-measure fields.
    # This keeps the leader anchor on the real crossing while still exposing
    # Chainage/MEAS values for labels and QA.
    if arcpy.Exists(out_fc):
        arcpy.management.Delete(out_fc)

    arcpy.management.CopyFeatures(point_fc, out_fc)

    available_fields = {field.name for field in arcpy.ListFields(event_table)}
    join_fields = [
        field_name
        for field_name in POINT_EVENT_JOIN_FIELDS
        if field_name in available_fields
    ]

    if join_fields:
        arcpy.management.JoinField(
            in_data=out_fc,
            in_field=LEADER_ANCHOR_ID_FIELD,
            join_table=event_table,
            join_field=LEADER_ANCHOR_ID_FIELD,
            fields=join_fields,
        )


def create_intersections_and_overlaps(
    route_fc,
    output_gdb,
    analysis_layers,
):
    """
    Intersects each analysis layer against the route to find crossings and overlaps.

    Point intersections are where the route meets another feature.
    Line overlaps are where the route shares a path with a polyline or passes
    through a polygon.

    Layers that produce no results are deleted immediately to keep the GDB clean.
    Layers that fail are skipped with a warning so one bad layer doesn't stop the tool.

    Parameters
    ----------
    route_fc : str
        Path to the M-enabled route feature class.
    output_gdb : str
        Path to the output geodatabase.
    analysis_layers : list of str
        Paths to the feature classes to check against the route.

    Returns
    -------
    dict
        point_intersections -- list of in_memory point feature class paths
        line_overlaps       -- list of output GDB line feature class paths
    """
    point_intersections = []
    line_overlaps = []
    route_name = os.path.splitext(os.path.basename(route_fc))[0]

    for layer in analysis_layers:
        try:
            desc = arcpy.Describe(layer)
            layer_name = arcpy.ValidateTableName(desc.basename, output_gdb)
            shape_type = desc.shapeType

            if layer_name.lower() == route_name.lower():
                continue  # skip — intersecting the route with itself makes no sense

            point_out = rf"in_memory\{layer_name}_intersect"
            arcpy.analysis.Intersect([route_fc, layer], point_out, output_type="POINT")

            if int(arcpy.management.GetCount(point_out)[0]) > 0:
                point_out = _explode_multipoint_intersections(point_out)
                _ensure_leader_anchor_ids(point_out)
                point_intersections.append(point_out)
            else:
                arcpy.management.Delete(point_out)

            if shape_type in ["Polyline", "Polygon"]:
                overlap_out = os.path.join(output_gdb, f"{layer_name}_Overlaps")
                arcpy.analysis.Intersect(
                    [route_fc, layer], overlap_out, output_type="LINE"
                )

                if int(arcpy.management.GetCount(overlap_out)[0]) > 0:
                    line_overlaps.append(overlap_out)
                else:
                    arcpy.management.Delete(overlap_out)

        except Exception as e:
            arcpy.AddWarning(f"Skipped layer {layer}: {e}")

    return {
        "point_intersections": point_intersections,
        "line_overlaps": line_overlaps,
    }


def locate_intersections_and_overlaps(
    route_fc,
    route_id_field,
    out_gdb,
    tolerance,
    point_intersections,
    line_overlaps,
):
    """
    Locates intersection and overlap geometries along the route to produce event tables.

    Converts raw point and line geometries into route-referenced event tables that
    store measure values (MEAS for points, FMEAS/TMEAS for lines). Empty tables
    are discarded.

    Parameters
    ----------
    route_fc : str
        Path to the M-enabled route feature class.
    route_id_field : str
        Name of the route identifier field.
    out_gdb : str
        Path to the output geodatabase.
    tolerance : float
        Search tolerance for Locate Features Along Routes.
    point_intersections : list of str
        Point feature class paths from create_intersections_and_overlaps.
    line_overlaps : list of str
        Line feature class paths from create_intersections_and_overlaps.

    Returns
    -------
    dict
        point_event_tables -- list of in_memory event table paths
        line_event_tables  -- list of output GDB event table paths
    """
    point_event_tables = []
    line_event_tables = []

    for point_fc in point_intersections:
        point_name = arcpy.ValidateTableName(
            os.path.splitext(os.path.basename(point_fc))[0], out_gdb
        )
        out_table = rf"in_memory\{point_name}_event"

        arcpy.lr.LocateFeaturesAlongRoutes(
            in_features=point_fc,
            in_routes=route_fc,
            route_id_field=route_id_field,
            out_table=out_table,
            out_event_properties=f"{route_id_field} POINT MEAS",
            radius_or_tolerance=tolerance,
            route_locations="FIRST",
            distance_field="DISTANCE",
            in_fields="FIELDS",
        )

        if int(arcpy.management.GetCount(out_table)[0]) > 0:
            point_event_tables.append(out_table)
        else:
            arcpy.management.Delete(out_table)

    for overlap_fc in line_overlaps:
        overlap_name = arcpy.ValidateTableName(
            os.path.splitext(os.path.basename(overlap_fc))[0], out_gdb
        )

        # Strip "_Overlaps" suffix so the output table gets a clean name
        base_overlap_name = (
            overlap_name[: -len("_Overlaps")]
            if overlap_name.lower().endswith("_overlaps")
            else overlap_name
        )
        out_table = os.path.join(out_gdb, f"{base_overlap_name}_OverlapsTable")

        arcpy.lr.LocateFeaturesAlongRoutes(
            in_features=overlap_fc,
            in_routes=route_fc,
            route_id_field=route_id_field,
            out_table=out_table,
            out_event_properties=f"{route_id_field} LINE FMEAS TMEAS",
            radius_or_tolerance=tolerance,
            distance_field="DISTANCE",
            in_fields="FIELDS",
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
    """
    Returns the Python code block used by CalculateField to format a measure
    value as a chainage string e.g. 1230 -> "1+230".
    """
    return r"""
def chain(val):
    val = int(round(float(val)))
    km = val // 1000
    remainder = val % 1000
    return f"{km}+{remainder:03d}"
"""


def add_chainage_to_event_tables(point_event_tables, line_event_tables):
    """
    Adds formatted chainage fields to point and line event tables.

    Point tables get a single Chainage field calculated from MEAS.
    Line tables get FromCh, ToCh, and ChainageRange calculated from FMEAS and TMEAS.

    Parameters
    ----------
    point_event_tables : list of str
        Event table paths for point intersections.
    line_event_tables : list of str
        Event table paths for line overlaps.
    """
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
    route_fc,
    route_id_field,
    output_gdb,
    point_event_tables,
    line_event_tables,
    point_intersections=None,
):
    """
    Converts event tables back into feature classes using the route geometry.

    For point intersections, uses the original raw geometry (with leader anchor
    positions) where available, falling back to Make Route Event Layer otherwise.
    For line overlaps, creates features in_memory from the overlap event tables.

    Parameters
    ----------
    route_fc : str
        Path to the M-enabled route feature class.
    route_id_field : str
        Name of the route identifier field.
    output_gdb : str
        Path to the output geodatabase.
    point_event_tables : list of str
        Event table paths for point intersections.
    line_event_tables : list of str
        Event table paths for line overlaps.
    point_intersections : list of str, optional
        Original raw intersection point feature classes. Used to preserve exact
        crossing geometry for leader anchors.

    Returns
    -------
    dict
        point_event_features -- list of output point feature class paths
        line_event_features  -- list of in_memory line feature class paths
    """
    point_event_features = []
    line_event_features = []
    point_intersection_lookup = _build_point_intersection_lookup(
        point_intersections, output_gdb
    )

    for table in point_event_tables:
        base_name = arcpy.ValidateTableName(
            os.path.splitext(os.path.basename(table))[0], output_gdb
        )

        # Strip event-table suffixes so the output FC gets a clean name.
        # Event tables are named '{layer}_intersect_event'; without stripping,
        # the output FC would be '{layer}_intersect_event_Intersections'.
        # Longest suffix is checked first so '_intersect_event' matches before
        # the shorter '_event' fallback.
        clean_name = base_name
        for suffix in ("_intersect_event", "_event"):
            if clean_name.lower().endswith(suffix.lower()):
                clean_name = clean_name[: -len(suffix)]
                break

        out_layer = f"{base_name}_layer"
        out_fc = os.path.join(output_gdb, f"{clean_name}_Intersections")
        point_name = (
            base_name[:-6] if base_name.lower().endswith("_event") else base_name
        )
        source_point_fc = point_intersection_lookup.get(point_name.lower())

        if source_point_fc and arcpy.Exists(source_point_fc):
            _copy_raw_intersections_with_chainage(source_point_fc, table, out_fc)
        else:
            arcpy.lr.MakeRouteEventLayer(
                in_routes=route_fc,
                route_id_field=route_id_field,
                in_table=table,
                in_event_properties=f"{route_id_field} POINT MEAS",
                out_layer=out_layer,
            )

            if arcpy.Exists(out_fc):
                arcpy.management.Delete(out_fc)

            arcpy.management.CopyFeatures(out_layer, out_fc)

        if arcpy.Exists(out_fc):
            desc = arcpy.Describe(out_fc)
            if desc.shapeType == "Multipoint":
                single_fc = os.path.join(output_gdb, f"{clean_name}_single")

                if arcpy.Exists(single_fc):
                    arcpy.management.Delete(single_fc)

                arcpy.management.MultipartToSinglepart(out_fc, single_fc)
                out_fc = single_fc

        point_event_features.append(out_fc)

    for table in line_event_tables:
        base_name = arcpy.ValidateTableName(
            os.path.splitext(os.path.basename(table))[0], output_gdb
        )

        out_layer = f"{base_name}_layer"
        out_fc = rf"in_memory\{base_name}_overlap"

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
