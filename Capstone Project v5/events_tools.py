import arcpy, os

# The following function is checking other features against the main route and create point intersection and line overlap
# Point intersection is where the route meets another feature.
# Overlaps is where the route shares the same path with another line or passes through a polygon
def create_intersections_and_overlaps(
    route_fc,
    output_gdb,
    analysis_layers,
):
    point_intersections = (
        []
    )  # it will store features created as points or which intersected the route
    line_overlaps = []  # will store features that overlap the route

    route_name = os.path.splitext(os.path.basename(route_fc))[
        0
    ]  # extracting the route name

    # loop through the features provided that user thinks they are intersecting or overlapping
    for layer in analysis_layers:
        try:  # try is used for error handling so that if one layer which was provided fails, the whole tool does not crash
            desc = arcpy.Describe(layer)
            layer_name = arcpy.ValidateTableName(desc.basename, output_gdb)
            shape_type = desc.shapeType

            if (
                layer_name.lower() == route_name.lower()
            ):  # Here, the code is checking if layer being checked has same name with route and skips
                continue  # skips coz intersecting a route with itself would not make sense

            # creaing intersect now
            point_out = rf"in_memory\{layer_name}_intersect"
            arcpy.analysis.Intersect([route_fc, layer], point_out, output_type="POINT")

            # check whether the output above has features
            # if count>0, keep output, if =0, delete the empty feature class
            # So that the gdb is not filled by empty feature
            if int(arcpy.management.GetCount(point_out)[0]) > 0:
                point_intersections.append(point_out)
            else:
                arcpy.management.Delete(point_out)

            # create overlap for polyline or polygon
            if shape_type in ["Polyline", "Polygon"]:
                overlap_out = os.path.join(output_gdb, f"{layer_name}_overlap")
                arcpy.analysis.Intersect(
                    [route_fc, layer], overlap_out, output_type="LINE"
                )

                if int(arcpy.management.GetCount(overlap_out)[0]) > 0:
                    line_overlaps.append(overlap_out)
                else:
                    arcpy.management.Delete(overlap_out)

        except Exception as e:
            arcpy.AddWarning(
                f"Skipped layer {layer}: {e}"
            )  # if something went wrong for specific layer, ArcGIS shows warning message

    return {
        "point_intersections": point_intersections,
        "line_overlaps": line_overlaps,
    }


# the following function takes the raw intersection/overlap geometries and converts them into route event tables with measures
# So the above function was asking, where do features intersect and overlap
# And this next function answers where those intersections/overlaps occur along the route
# And also what chainage or measure they have
def locate_intersections_and_overlaps(
    route_fc,
    route_id_field,
    out_gdb,
    tolerance,
    point_intersections,
    line_overlaps,
):
    point_event_tables = []
    line_event_tables = []

    for point_fc in point_intersections:
        point_name = arcpy.ValidateTableName(
            os.path.splitext(os.path.basename(point_fc))[0], out_gdb
        )
        out_table = rf"in_memory\{point_name}_event"

        # this is the key step. It takes each point feature and finds where it lies along the route
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
            os.path.splitext(os.path.basename(overlap_fc))[0], out_gdb
        )

        # Fixed: use overlap_name (not point_name) so the table name is derived
        # from the current overlap feature, not the last point intersection.
        out_table = os.path.join(out_gdb, f"{overlap_name}_event")

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


# label formatting. It converts those raw numbers into chainage such as 1+200
def chainage_code_block():
    return r"""
def chain(val):
    val = int(round(float(val))) #this does 3 things, converts value to float, rounds it, and converts it to interger
    km = val // 1000 #this gets the thousand part 1230//1000=1, 3500//1000=3
    remainder = val % 1000#takes the leftover after removing thousand. When we removed thousand above we ramain with 230, amd 500
    return f"{km}+{remainder:03d}"#formats the results as chainage text. 1230 now becomes 1+230. :03d means the remainder is always shown with 3 digits. That is why 5 becomes 005, 50 becomes 050, 500 remains 500
"""


# this function add chainage labels to both point event tables and line event tables
def add_chainage_to_event_tables(point_event_tables, line_event_tables):
    code_block = (
        chainage_code_block()
    )  # calls function above and stores the returned python code in code_block

    # looping through every point event tables. Remember this event tables were already created from point intersections
    for table in point_event_tables:
        existing_fields = [f.name for f in arcpy.ListFields(table)]

        # Add chainage field if missing
        if "Chainage" not in existing_fields:
            arcpy.management.AddField(table, "Chainage", "TEXT", field_length=20)

        # calculate the field we added above. That is chainage
        arcpy.management.CalculateField(
            table,
            "Chainage",
            "chain(!MEAS!)",
            "PYTHON3",
            code_block,  # This calculates Chainage from MEAS
        )

        # the following for loop, loops through the line event tables.
        # This are the ones created from from overlaps.
        # This are the one with To and Fro Measures instead of single measure like points
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


# The foloowing function is a step where event tables above becomes features classes again
# Coz at first we had raw intersection/overlap geometries
# Then event tables with MEAS, FMEAS, TMEAS
# Then we added field and calculated the fields including chainage  to those tables
# Now we use those tables plus the route to create a feature class from those tables
def make_event_layers_from_tables(
    route_fc,
    route_id_field,
    output_gdb,
    point_event_tables,
    line_event_tables,
):
    point_event_features = []
    line_event_features = []

    for table in point_event_tables:
        base_name = arcpy.ValidateTableName(
            os.path.splitext(os.path.basename(table))[0], output_gdb
        )

        out_layer = f"{base_name}_layer"
        out_fc = os.path.join(output_gdb, f"{base_name}_intersect")

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

        out_layer = f"{base_name}_layer"
        # out_fc = os.path.join(output_gdb, f"{base_name}_overlap")
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
