import arcpy
import os

from route_tools import create_route_with_measure_system, create_stationing_source_line

# The reason why I addeed this function, is that when you run the tool, it includes the end point after every last interval. Such that you will have duplicate last rows of every route you excute.
# The end point is important and we dont want to tell the system not to include the end point always
# For example you have line with 73 metres and you want interval of 10 metres, so instaed of system ending at 70 coz the 3 above 70 is less than 10, the end point will include that 3 and there will be 73 after 70


def remove_duplicate_station_measure(
    station_points,
    station_table,
    measure_field="MEAS",
):
    seen_measures = set()  # keeps track of measures already encountered.
    duplicate_station_ids = []  # this will store the StationIDs that should be removed

    # The search cursor readss through the station table and gets the Station ID, MEAS
    with arcpy.da.SearchCursor(station_table, ["StationID", measure_field]) as Scursor:
        for station_id, meas in Scursor:
            key = (
                round(float(meas), 6) if meas is not None else None
            )  # converts the measure value to float and 6 decimal places

            # the following if statement keeps track of measure.
            # Such that if the measure was already seen befor, its StationID is marked as duplicate
            # if not, it is added to the set of seen measures
            # so in short it keeps the first occurrence of a measure and marks later repeats for deletion
            if key in seen_measures:
                duplicate_station_ids.append(station_id)
            else:
                seen_measures.add(key)
    if not duplicate_station_ids:
        return

    duplicate_station_ids_set = set(
        duplicate_station_ids
    )  # This Converts the list to a set for faster lookup during deletion.

    # the following update cursor deletes duplicate rows from the station table.
    with arcpy.da.UpdateCursor(station_table, ["StationID"]) as Ucursor:
        for row in Ucursor:
            if row[0] in duplicate_station_ids_set:
                Ucursor.deleteRow()

    # This cursor deletes matching duplicate rows from the station points feature class.
    with arcpy.da.UpdateCursor(station_points, ["StationID"]) as Ucursor:
        for row in Ucursor:
            if row[0] in duplicate_station_ids_set:
                Ucursor.deleteRow()


# The following function makes sure the sation points gets the chainage information from the station table
def join_station_chainage_to_points(
    station_points,
    station_table,
):
    point_fields = [
        f.name for f in arcpy.ListFields(station_points)
    ]  # Here the code is getting all fields in the station point feature

    # Now, the for loop statement belowc hecks if those speified fields alraedy exist in the feature
    # So that if theyexists, they are ddeleted to avoid conflicts
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


def create_route_stationing(
    input_line_fc,
    output_gdb,
    station_interval,
    tolerance,
    start_measure=0,
    end_measure=None,
    route_id_field="Route_ID",
    route_id_value="ROUTE_01",
):
    # the following script calls another function from route.p that had prepared the input line with M values
    # Then returns a dictionary - route_info
    route_info = create_route_with_measure_system(
        input_line_fc=input_line_fc,
        out_gdb=output_gdb,
        start_measure=start_measure,
        route_id_field=route_id_field,
        route_id_value=route_id_value,
    )
    # Now we are extracting main route and the base name from the above code
    route_fc = route_info["route_fc"]
    base_name = route_info["base_name"]

    # The following script creates a line that station points will be generted on
    # It reuses the function from route.py
    station_source_fc = create_stationing_source_line(
        route_fc=route_fc,
        out_gdb=output_gdb,
        base_name=base_name,
        route_id_field=route_id_field,
        route_id_value=route_id_value,
        start_measure=start_measure,
        end_measure=end_measure,
    )

    station_points = os.path.join(output_gdb, base_name + "_station_points")
    if arcpy.Exists(station_points):
        arcpy.management.Delete(station_points)

    # The following code is where the acttual station points are created
    # It generates points along the station interval and also include the end points
    arcpy.management.GeneratePointsAlongLines(
        station_source_fc,
        station_points,
        "DISTANCE",
        Distance=station_interval,
        Include_End_Points="END_POINTS",
    )

    # Now the following code is adding a new field called StationID and calculates it.
    # That field is important for joing the tables to feature class.
    # Coz if you rely on fields from input features, they may not have appropriate fields to perform joins
    if "StationID" not in [f.name for f in arcpy.ListFields(station_points)]:
        arcpy.management.AddField(station_points, "StationID", "LONG")

    arcpy.management.CalculateField(
        station_points, "StationID", "!OBJECTID!", "PYTHON3"
    )

    # we are now creating the output path for the station event tables and delete any old version
    # station event tables come from converting the points we generated above into route_refenced events
    # station_table = os.path.join("output_gdb", base_name + "_station_events")
    station_table = rf"in_memory\{base_name}_station_events"
    if arcpy.Exists(station_table):
        arcpy.management.Delete(station_table)

    # The following code is another step of linear referencing which for each point in station points for example, it finds where it lies along the route and writes record in station table
    # The output table will now contain measure values like MEAS and now they become measured events on the route
    arcpy.lr.LocateFeaturesAlongRoutes(
        in_features=station_points,
        in_routes=route_fc,
        route_id_field=route_id_field,
        out_table=station_table,
        out_event_properties=f"{route_id_field} POINT MEAS",  # This part is important because it means event table will store route ID, point event type and one measure field called MEAS
        radius_or_tolerance=tolerance,
        distance_field="DISTANCE",
    )

    # Now that we have located points along the route, we want to add chainage field to the output table above so that we can calculate and use it for labelling
    table_fields = [f.name for f in arcpy.ListFields(station_table)]
    if "Chainage" not in table_fields:
        arcpy.management.AddField(station_table, "Chainage", "TEXT", field_length=20)

    # Lets now format the chainage field we added above
    # The code stores as string and passed into CalculateField
    # It formatted so that if MEAS was 1250, it converts to 1+250

    calculate_field_code = r"""
def chain(val):
    val = int(round(float(val)))
    km = val // 1000
    remainder = val % 1000
    return f"{km}+{remainder:03d}"
"""
    # Lets now runs the chain() function on every MEAS value and writes the result into the Chainage field.
    arcpy.management.CalculateField(
        station_table, "Chainage", "chain(!MEAS!)", "PYTHON3", calculate_field_code
    )
    # Now lets clean the table by removing the duplicates.
    # We are using the remove duplicates function we created earlier in this script. (The first function in this script)
    remove_duplicate_station_measure(
        station_points=station_points, station_table=station_table, measure_field="MEAS"
    )

    return {
        "route_fc": route_fc,
        "station_source_fc": station_source_fc,
        "station_points": station_points,
        "station_table": station_table,
        "route_id_field": route_id_field,
    }
