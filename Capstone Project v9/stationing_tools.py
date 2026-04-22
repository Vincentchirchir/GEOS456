import arcpy
import os

from route_tools import (
    create_route_with_measure_system,
    create_stationing_source_line,
)

def remove_duplicate_station_measure(
    station_points,
    station_table,
    measure_field="MEAS",
):
    """
    Removes duplicate station points that share the same measure value.

    GeneratePointsAlongLines always includes the end point, so when the line
    length is not an exact multiple of the interval, the last interval point
    and the end point can land on the same measure. This function keeps the
    first occurrence and deletes the rest from both the station table and the
    station points feature class.

    Parameters
    ----------
    station_points : str
        Path to the station points feature class.
    station_table : str
        Path to the station event table.
    measure_field : str, optional
        Name of the measure field. Defaults to "MEAS".
    """
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

    duplicate_set = set(duplicate_station_ids)

    with arcpy.da.UpdateCursor(station_table, ["StationID"]) as cursor:
        for row in cursor:
            if row[0] in duplicate_set:
                cursor.deleteRow()

    with arcpy.da.UpdateCursor(station_points, ["StationID"]) as cursor:
        for row in cursor:
            if row[0] in duplicate_set:
                cursor.deleteRow()


def join_station_chainage_to_points(
    station_points,
    station_table,
):
    """
    Joins MEAS and Chainage from the station table onto the station points.

    Drops any existing Chainage, MEAS, FMEAS, or TMEAS fields first to avoid
    conflicts with the incoming join fields.

    Parameters
    ----------
    station_points : str
        Path to the station points feature class.
    station_table : str
        Path to the station event table containing MEAS and Chainage.
    """
    point_fields = [f.name for f in arcpy.ListFields(station_points)]

    # Remove stale join fields before re-joining to avoid field name conflicts
    fields_to_delete = [f for f in ["Chainage", "MEAS", "FMEAS", "TMEAS"] if f in point_fields]
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
    """
    Full stationing workflow: creates a route, generates station points, and
    locates them along the route to produce a table with measure and chainage values.

    Parameters
    ----------
    input_line_fc : str
        Path to the input line feature class.
    output_gdb : str
        Path to the output geodatabase.
    station_interval : arcpy.LinearUnit
        Spacing between station points.
    tolerance : float
        Search tolerance for Locate Features Along Routes.
    start_measure : float, optional
        Starting measure value. Defaults to 0.
    end_measure : float, optional
        Ending measure value. If None, stations are generated to the end of the line.
    route_id_field : str, optional
        Name of the route identifier field. Defaults to "Route_ID".
    route_id_value : str, optional
        Value written into the route identifier field. Defaults to "ROUTE_01".

    Returns
    -------
    dict
        route_fc         -- path to the M-enabled route feature class
        station_source_fc -- path to the line used for stationing (clipped or full route)
        station_points   -- path to the station points feature class
        station_table    -- path to the station event table (in_memory)
        route_id_field   -- name of the route ID field
    """
    route_info = create_route_with_measure_system(
        input_line_fc=input_line_fc,
        out_gdb=output_gdb,
        start_measure=start_measure,
        route_id_field=route_id_field,
        route_id_value=route_id_value,
    )
    route_fc = route_info["route_fc"]
    base_name = route_info["base_name"]

    station_source_fc = create_stationing_source_line(
        route_fc=route_fc,
        out_gdb=output_gdb,
        base_name=base_name,
        route_id_field=route_id_field,
        route_id_value=route_id_value,
        start_measure=start_measure,
        end_measure=end_measure,
    )

    station_points = os.path.join(output_gdb, base_name + "_Stations")
    if arcpy.Exists(station_points):
        arcpy.management.Delete(station_points)

    arcpy.management.GeneratePointsAlongLines(
        station_source_fc,
        station_points,
        "DISTANCE",
        Distance=station_interval,
        Include_End_Points="END_POINTS",
    )

    # Delete the clipped segment FC — only created when end_measure was specified,
    # and not needed once station points have been generated.
    if station_source_fc != route_fc and arcpy.Exists(station_source_fc):
        arcpy.management.Delete(station_source_fc)

    # StationID mirrors OBJECTID and is used as a stable join key between
    # the station points and the station table.
    if "StationID" not in [f.name for f in arcpy.ListFields(station_points)]:
        arcpy.management.AddField(station_points, "StationID", "LONG")

    arcpy.management.CalculateField(
        station_points, "StationID", "!OBJECTID!", "PYTHON3"
    )

    station_table = rf"in_memory\{base_name}_station_events"
    if arcpy.Exists(station_table):
        arcpy.management.Delete(station_table)

    # Locate each station point along the route to get its measure value
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

    # Format MEAS as chainage string e.g. 1250 -> "1+250"
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
