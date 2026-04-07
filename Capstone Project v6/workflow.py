import arcpy
from types import SimpleNamespace

from stationing_tools import create_route_stationing, join_station_chainage_to_points
from events_tools import (
    create_intersections_and_overlaps,
    locate_intersections_and_overlaps,
    add_chainage_to_event_tables,
    make_event_layers_from_tables,
)
from map_tools import add_output_to_current_map


def merge_feature_outputs(feature_classes, output_fc):
    """Return one feature class for web-tool output, merging when needed."""
    valid_fcs = [fc for fc in feature_classes if fc and arcpy.Exists(fc)]
    if not valid_fcs:
        return None

    if len(valid_fcs) == 1:
        return valid_fcs[0]

    if arcpy.Exists(output_fc):
        arcpy.management.Delete(output_fc)

    arcpy.management.Merge(valid_fcs, output_fc)
    return output_fc


def run_stationing_workflow(
    input_line_fc,
    station_interval,
    tolerance,
    start_measure,
    end_measure,
    analysis_layers,
    messages,
):
    scratch = arcpy.env.scratchGDB

    result = create_route_stationing(
        input_line_fc=input_line_fc,
        output_gdb=scratch,
        station_interval=station_interval,
        tolerance=tolerance,
        start_measure=start_measure,
        end_measure=end_measure,
    )

    messages.addMessage("Route created successfully.")

    join_station_chainage_to_points(
        station_points=result.stations,
        station_table=result.table,
    )
    messages.addMessage("Station points generated.")
    messages.addMessage("Chainage joined to station points.")

    point_features = []
    line_features = []

    if analysis_layers:
        messages.addMessage("Creating intersections and overlaps...")

        crossing = create_intersections_and_overlaps(
            route_fc=result.route,
            output_gdb=scratch,
            analysis_layers=analysis_layers,
        )

        events = locate_intersections_and_overlaps(
            route_fc=result.route,
            route_id_field=result.id_field,
            tolerance=tolerance,
            out_gdb=scratch,
            point_intersections=crossing.pts,
            line_overlaps=crossing.lines,
        )

        add_chainage_to_event_tables(
            point_event_tables=events.pts,
            line_event_tables=events.lines,
        )

        event_features = make_event_layers_from_tables(
            route_fc=result.route,
            route_id_field=result.id_field,
            output_gdb=scratch,
            point_event_tables=events.pts,
            line_event_tables=events.lines,
        )

        point_features = event_features.pts
        line_features = event_features.lines

        messages.addMessage("Intersections and overlaps processed.")

    else:
        messages.addMessage("No intersecting or overlapping features provided.")

    merged_intersections = merge_feature_outputs(
        point_features,
        f"{scratch}\\all_intersections",
    )
    merged_overlaps = merge_feature_outputs(
        line_features,
        f"{scratch}\\all_overlaps",
    )

    result_ns = SimpleNamespace(
        route=result.route,
        stations=result.stations,
        segment=result.source,
        intersections=point_features,
        overlaps=line_features,
        intersection_output=merged_intersections,
        overlap_output=merged_overlaps,
    )

    add_output_to_current_map(result_ns)

    messages.addMessage("Processing complete.")

    return result_ns
