import arcpy
import os
import sys
import importlib

import route_tools_v3
import stationing_tools_v3
import events_tools_v3
import map_tools_v3
import layout_elements_v3
import layout_tools_v3  # layout_tools
import band_tools

tool_folder = os.path.dirname(__file__)
if tool_folder not in sys.path:
    sys.path.append(tool_folder)

from route_tools_v3 import (
    create_route_with_measure_system,
    create_stationing_source_line,
)
from stationing_tools_v3 import (
    remove_duplicate_station_measure,
    join_station_chainage_to_points,
    create_route_stationing,
)
from events_tools_v3 import (
    create_intersections_and_overlaps,
    locate_intersections_and_overlaps,
    chainage_code_block,
    add_chainage_to_event_tables,
    make_event_layers_from_tables,
)
from map_tools_v3 import add_output_to_current_map
from layout_tools_v3 import generate_alignment_layout
from layout_tools_v3 import (
    generate_alignment_layout,
)
from leader_tools_v3 import draw_stationing_leaders_for_points, leaders_to_map_series
from band_tools import (
    build_band_records,
    get_route_measure_range,
    build_layout_band_positions,
    prepare_layout_band_records,
    clear_point_band_labels,
    draw_point_band_labels,
    clear_line_band_labels,
    draw_line_band_labels,
    assign_point_label_sides,
)

importlib.reload(route_tools_v3)
importlib.reload(stationing_tools_v3)
importlib.reload(events_tools_v3)
importlib.reload(map_tools_v3)
importlib.reload(layout_tools_v3)
importlib.reload(layout_elements_v3)


def _iter_refresh_candidate_maps(aprx, primary_map):
    # Refresh Leaders should prefer the map used by the layouts map frame, but
    # fall back to the active map and other project maps because the outputs are
    # currently added to aprx.activeMap during generation.
    seen = set()

    for map_obj in [primary_map, aprx.activeMap, *aprx.listMaps()]:
        if not map_obj:
            continue

        map_id = getattr(map_obj, "URI", None) or getattr(map_obj, "name", None)
        if map_id in seen:
            continue

        seen.add(map_id)
        yield map_obj


def _is_refresh_point_event_layer(lyr):
    try:
        if not lyr.isFeatureLayer or getattr(lyr, "isBroken", False):
            return False

        desc = arcpy.Describe(lyr)
        if desc.shapeType not in ["Point", "Multipoint"]:
            return False

        data_source = getattr(lyr, "dataSource", None)
        field_target = data_source if data_source else lyr
        field_names = {field.name for field in arcpy.ListFields(field_target)}

        data_source_name = (
            os.path.splitext(os.path.basename(data_source))[0].lower()
            if data_source
            else ""
        )
        layer_name = getattr(lyr, "name", "").lower()
        desc_name = getattr(desc, "basename", "").lower()
        name_blob = " ".join(
            part for part in [data_source_name, layer_name, desc_name] if part
        )

        # Accept any point layer that has Chainage
        # Reject known non-event layers
        if "station" in name_blob:
            return False

        # Must be point type
        if desc.shapeType not in ["Point", "Multipoint"]:
            return False

        # Must have Chainage (still useful)
        if "Chainage" not in field_names:
            return False

        # Must be intersection/event
        if "intersect" in name_blob or "event" in name_blob:
            return True

        return False

    except Exception:
        return False


def _iter_layers(layers):
    for lyr in layers:
        yield lyr
        if lyr.isGroupLayer:
            for sublyr in _iter_layers(lyr.listLayers()):
                yield sublyr


def _discover_refresh_point_event_features(aprx, primary_map):
    discovered = []
    seen_sources = set()
    searched_maps = []

    for map_obj in _iter_refresh_candidate_maps(aprx, primary_map):
        searched_maps.append(map_obj.name)

        try:
            layers = map_obj.listLayers()
        except Exception:
            continue

        for lyr in _iter_layers(layers):
            try:
                arcpy.AddMessage(f"Checking layer: {lyr.name}")

                if not lyr.isFeatureLayer:
                    arcpy.AddMessage("  - skipped: not a feature layer")
                    continue

                desc = arcpy.Describe(lyr)
                arcpy.AddMessage(f"  - shapeType: {desc.shapeType}")

                data_source = getattr(lyr, "dataSource", None)
                arcpy.AddMessage(f"  - data source: {data_source}")

                field_target = data_source if data_source else lyr
                field_names = [field.name for field in arcpy.ListFields(field_target)]
                arcpy.AddMessage(f"  - fields: {field_names}")

                if not _is_refresh_point_event_layer(lyr):
                    arcpy.AddMessage("  - skipped by _is_refresh_point_event_layer")
                    continue

                if not data_source or data_source in seen_sources:
                    arcpy.AddMessage("  - skipped: no data source or already seen")
                    continue

                seen_sources.add(data_source)
                discovered.append(data_source)
                arcpy.AddMessage("  - accepted")

            except Exception as e:
                arcpy.AddMessage(f"  - error reading layer: {e}")
                continue

    return discovered, searched_maps


class Toolbox(object):
    def __init__(self):
        self.label = "Stationing and Linear Referencing Tools"
        self.alias = "stationingtools"
        self.tools = [GenerateStationing, RefreshLeaders]


class RefreshLeaders(object):
    def __init__(self):
        self.label = "Refresh Leaders"
        self.description = "Refresh leader graphics for the current map series page"
        self.canRunInBackground = False

    def getParameterInfo(self):
        return []

    def isLicensed(self):
        return True

    def execute(self, parameters, messages):
        import arcpy
        from leader_tools_v3 import leaders_to_map_series

        aprx = arcpy.mp.ArcGISProject("CURRENT")

        # Find layout with enabled map series
        target_layout = None
        for lyt in aprx.listLayouts():
            try:
                if lyt.mapSeries and lyt.mapSeries.enabled:
                    target_layout = lyt
                    break
            except:
                continue

        if not target_layout:
            arcpy.AddError("No layout with an enabled map series found.")
            return

        # Find the correct map frame dynamically
        map_frames = target_layout.listElements("MAPFRAME_ELEMENT")
        if not map_frames:
            arcpy.AddError("No map frames found in the layout.")
            return

        # First try to find one whose name suggests it is the main map
        preferred_frames = [mf for mf in map_frames if "main" in mf.name.lower()]

        if preferred_frames:
            map_frame = preferred_frames[0]
        else:
            # Fallback: use the largest map frame, not the mini map
            map_frame = max(
                map_frames, key=lambda mf: mf.elementWidth * mf.elementHeight
            )

        arcpy.AddMessage(f"Using map frame: {map_frame.name}")

        map_obj = map_frame.map
        map_series = target_layout.mapSeries

        current_page = map_series.currentPageNumber
        arcpy.AddMessage(f"Refreshing leaders for page {current_page}")

        # Search the layout map first, then fall back to the active map and any
        # other project maps. This makes refresh robust even when generation
        # added outputs to a different map than the layout currently references.
        unique_point_event_features, searched_maps = (
            _discover_refresh_point_event_features(aprx, map_obj)
        )

        if not unique_point_event_features:
            arcpy.AddError(
                "No point event layers found. Maps searched: "
                + ", ".join(searched_maps)
            )
            return

        arcpy.AddMessage("Detected point event layers:")
        for fc in unique_point_event_features:
            arcpy.AddMessage(f" - {fc}")

        leaders_to_map_series(
            layout_name=target_layout.name,
            map_frame=map_frame.name,
            point_event_features=unique_point_event_features,
        )


class GenerateStationing(object):
    def __init__(self):
        self.label = "Generating Stationings"
        self.description = "Creates a route and station points from any linear feature."

    def getParameterInfo(self):
        input_line = arcpy.Parameter(
            displayName="Input Linear Feature",
            name="input_line",  # THIS IS INTERNAL PYTHON NAME
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
            displayName="Seach Tolerance",
            name="tolerance",
            datatype="GPLinearUnit",
            parameterType="Optional",
            direction="Input",
        )
        tolerance.value = "1 Meter"

        analysis_layers = arcpy.Parameter(
            displayName="Overlapping or Intersecting Features",
            name="analysis_layers",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input",
        )
        analysis_layers.multiValue = True

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

        create_layout = arcpy.Parameter(
            displayName="Create Layout",
            name="create_layout",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        create_layout.value = False

        layout_name = arcpy.Parameter(
            displayName="Layout Name",
            name="layout_name",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        layout_size = arcpy.Parameter(
            displayName="Page Size",
            name="layout_size",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        layout_size.filter.type = "ValueList"
        layout_size.filter.list = [
            "Letter (11x8.5)",
            "Legal (14x8.5)",
            "Tabloid (17x11)",
            "ANSI C (22x17)",
            "ANSI D (34x22)",
            "ANSI E (44x34)",
        ]
        layout_size.value = "Tabloid (17x11)"

        main_map_name = arcpy.Parameter(
            displayName="Main Map",
            name="main_map_name",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        mini_map_name = arcpy.Parameter(
            displayName="Mini Map",
            name="mini_map_name",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            maps = aprx.listMaps()
            map_names = [m.name for m in maps]

            main_map_name.filter.type = "ValueList"
            main_map_name.filter.list = map_names

            mini_map_name.filter.type = "ValueList"
            mini_map_name.filter.list = map_names

            if aprx.activeMap:
                main_map_name.value = aprx.activeMap.name
                mini_map_name.value = aprx.activeMap.name
        except:
            pass

        create_map_series = arcpy.Parameter(
            displayName="Create Map Series",
            name="create_map_series",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        create_map_series.value = False

        map_series_scale = arcpy.Parameter(
            displayName="Map Series Scale",
            name="map_series_scale",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input",
        )
        map_series_scale.value = 500

        map_series_orientation = arcpy.Parameter(
            displayName="Page Orientation",
            name="map_series_orientation",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        map_series_orientation.filter.type = "ValueList"
        map_series_orientation.filter.list = ["Horizontal", "Vertical"]
        map_series_orientation.value = "Horizontal"

        map_series_overlap = arcpy.Parameter(
            displayName="Overlap (%)",
            name="map_series_overlap",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input",
        )
        map_series_overlap.value = 15

        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            active_map = aprx.activeMap
            polyline_layers = []

            if active_map:
                for layer in active_map.listLayers():
                    if layer.isFeatureLayer:
                        try:
                            if layer.isBroken:
                                continue
                            desc = arcpy.Describe(layer.dataSource)
                            if desc.shapeType == "Polyline":
                                polyline_layers.append(layer.name)
                        except:
                            pass
            if polyline_layers:
                input_line.filter.list = polyline_layers
        except:
            pass

        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            maps = aprx.listMaps()
            map_names = [m.name for m in maps]

            main_map_name.filter.type = "ValueList"
            main_map_name.filter.list = map_names

            mini_map_name.filter.type = "ValueList"
            mini_map_name.filter.list = map_names
        except:
            pass

        # Desriptions to tools that shows when you hover the parameter
        input_line.description = "Select the main polyline feature to station."
        output_gdb.description = "Choose the output file geodatabase."
        station_interval.description = (
            "Distance between station points. Example: 100 Meters."
        )
        start_measure.description = (
            "Optional route start measure. Example: 2100 means station 2+100."
        )
        end_measure.description = (
            "Optional route end measure. Leave blank to process to the end."
        )
        tolerance.description = "Tolerance for locating features along the route."
        analysis_layers.description = (
            "Optional layers to analyze for intersections and overlaps."
        )
        create_layout.description = "Optional. Check to create an alignment layout."
        layout_name.description = "Name of the layout to create."
        layout_size.description = "Page size for the new layout."
        main_map_name.description = "Map to use in the main map frame."
        mini_map_name.description = "Map to use in the mini map frame."
        create_map_series.description = (
            "Optional. Check to create strip-map based map series."
        )
        map_series_scale.description = "Scale for strip map index and map series pages."
        map_series_orientation.description = "Orientation for strip map index pages."
        map_series_overlap.description = "Overlap percentage between strip map pages."

        return [
            input_line,  # 0
            output_gdb,  # 1
            station_interval,  # 2
            start_measure,  # 3
            end_measure,  # 4
            tolerance,  # 5
            analysis_layers,  # 6
            create_layout,  # 7
            layout_name,  # 8
            layout_size,  # 9
            main_map_name,  # 10
            mini_map_name,  # 11
            create_map_series,  # 12
            map_series_scale,  # 13
            map_series_orientation,  # 14
            map_series_overlap,  # 15
        ]

    def updateParameters(self, parameters):
        create_layout = parameters[7]
        layout_name = parameters[8]
        create_map_series = parameters[12]
        layout_param_indexes = [8, 9, 10, 11]
        map_series_param_indexes = [13, 14, 15]

        if create_layout.value:
            for i in layout_param_indexes:
                parameters[i].enabled = True
            parameters[12].enabled = True
        else:
            for i in layout_param_indexes:
                parameters[i].enabled = False
            parameters[12].enabled = False
            for i in map_series_param_indexes:
                parameters[i].enabled = False

        if create_layout.value and create_map_series.value:
            for i in map_series_param_indexes:
                parameters[i].enabled = True
        else:
            for i in map_series_param_indexes:
                parameters[i].enabled = False

        # Enable / disable map series parameters
        if create_layout.value and create_map_series.value:
            for i in map_series_param_indexes:
                parameters[i].enabled = True
        else:
            for i in map_series_param_indexes:
                parameters[i].enabled = False

        # Auto-fill layout name from input line
        input_line = parameters[0]
        if input_line.value and not layout_name.altered:
            try:
                desc = arcpy.Describe(input_line.valueAsText)
                base_name = os.path.splitext(os.path.basename(desc.catalogPath))[0]
                layout_name.value = f"{base_name}_Alignment_Sheet"
            except:
                pass

        return

    def updateMessages(self, parameters):
        input_line = parameters[0]
        output_gdb = parameters[1]
        station_interval = parameters[2]
        start_measure = parameters[3]
        end_measure = parameters[4]
        tolerance = parameters[5]
        analysis_layers = parameters[6]

        # Layout Validtion
        create_layout = parameters[7]
        layout_name = parameters[8]
        layout_size = parameters[9]
        main_map_name = parameters[10]
        mini_map_name = parameters[11]
        create_map_series = parameters[12]
        map_series_scale = parameters[13]
        map_series_orientation = parameters[14]
        map_series_overlap = parameters[15]

        # Validate layout inputs
        if create_layout.value:
            if not layout_name.value:
                layout_name.setErrorMessage(
                    "Layout Name is required when Create Layout is checked."
                )

            if not layout_size.value:
                layout_size.setErrorMessage(
                    "Page Size is required when Create Layout is checked."
                )

            if not main_map_name.value:
                main_map_name.setErrorMessage(
                    "Main Map is required when Create Layout is checked."
                )

            if not mini_map_name.value:
                mini_map_name.setErrorMessage(
                    "Mini Map is required when Create Layout is checked."
                )

        # Validate map series inputs
        if create_layout.value and create_map_series.value:
            if map_series_scale.value is None:
                map_series_scale.setErrorMessage(
                    "Map Series Scale is required when Create Map Series is checked."
                )

            if not map_series_orientation.value:
                map_series_orientation.setErrorMessage(
                    "Page Orientation is required when Create Map Series is checked."
                )

            if map_series_overlap.value is None:
                map_series_overlap.setErrorMessage(
                    "Overlap (%) is required when Create Map Series is checked."
                )

        if map_series_scale.value is not None:
            try:
                ms_scale = int(map_series_scale.value)
                if ms_scale <= 0:
                    map_series_scale.setErrorMessage(
                        "Map Series Scale must be greater than zero."
                    )
            except:
                map_series_scale.setErrorMessage(
                    "Map Series Scale must be a whole number."
                )

        if map_series_overlap.value is not None:
            try:
                overlap = int(map_series_overlap.value)
                if overlap < 0 or overlap > 99:
                    map_series_overlap.setErrorMessage(
                        "Overlap must be between 0 and 99."
                    )
            except:
                map_series_overlap.setErrorMessage("Overlap must be a whole number.")

        # validate tolerance
        if tolerance.value:
            try:
                tol = float(tolerance.valueAsText.split()[0])

                if tol <= 0:
                    tolerance.setErrorMessage("Tolerance must be greate than zero")
                elif tol > 100:
                    tolerance.setWarningMessage(
                        "Large tolerance may snap unrelated features to the route"
                    )
            except:
                tolerance.setErrorMessage("Invalid tolerance value. Example: 1 Meters")
        # warn if there is no active map
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
                        "Input Linear Feature must be a polyline feature"
                    )
            except Exception as e:
                input_line.setErrorMessage(f"Invalid input feature: {e}")

        # validating output workspace as geodatabse
        if output_gdb.value:
            try:
                out_path = output_gdb.valueAsText
                desc = arcpy.Describe(out_path)

                workspace_type = getattr(desc, "workspaceType", None)
                extension = os.path.splitext(out_path)[1].lower()

                if workspace_type != "LocalDatabase" and extension != ".gdb":
                    output_gdb.setErrorMessage(
                        "Output workspace must be a file geodatabase"
                    )
            except Exception as e:
                output_gdb.setErrorMessage(f"Invalid output workspace: {e}")

        # Validate station interval
        if station_interval.value:
            try:
                interval_text = station_interval.valueAsText
                interval_parts = interval_text.split()

                if len(interval_parts) < 2:
                    station_interval.setErrorMessage(
                        "Station Interval must include a number and unit, for example: 100 Meters."
                    )
                else:
                    numeric_value = float(interval_parts[0])

                    if numeric_value <= 0:
                        station_interval.setErrorMessage(
                            "Station Interval must be greater than zero"
                        )
                    elif numeric_value < 0.01:
                        station_interval.setWarningMessage(
                            "Station Interval is extremely small. This may create too many points"
                        )
                    elif numeric_value < 1:
                        station_interval.setWarningMessage(
                            "Station Interval is very small. Confirm this is intentional"
                        )
            except Exception:
                station_interval.setErrorMessage(
                    "Invalid Station Interval. Example of a valid input: 10 Meters."
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
                start_measure.setErrorMessage("Start Measure must be numeric")
        # validate end measure
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
                        "End Measure must be greater than Start Measure"
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

                for layer in layer_list:
                    layer = layer.strip().strip("'").strip('"')
                    if not layer:
                        continue

                    try:
                        desc = arcpy.Describe(layer)

                        if not hasattr(desc, "shapeType"):
                            analysis_layers.setErrorMessage(
                                f"Intersecting or Overlapping '{layer}' feature is not a valid feature layer."
                            )
                            return

                        if input_line.value:
                            try:
                                in_desc = arcpy.Describe(input_line.valueAsText)
                                layer_desc = arcpy.Describe(layer)

                                if hasattr(in_desc, "catalogPath") and hasattr(
                                    layer_desc, "catalogPath"
                                ):
                                    if os.path.normpath(
                                        in_desc.catalogPath
                                    ) == os.path.normpath(layer_desc.catalogPath):
                                        analysis_layers.setErrorMessage(
                                            "Input route layer is also included in intersecting and overlapping features"
                                        )
                            except:
                                pass
                    except Exception as e:
                        analysis_layers.setErrorMessage(
                            f"Intersecting or Overlapping '{layer}' feature is invalid or broken: {e}"
                        )
                        return
            except Exception as e:
                analysis_layers.setErrorMessage(
                    f"Invalid Intersecting and Overlapping: {e}"
                )

    # Excute functions
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

        tolerance = "1 Meter"
        if parameters[5].valueAsText:
            tolerance = parameters[5].valueAsText

        analysis_layers = []
        if parameters[6].valueAsText:
            analysis_layers = parameters[6].valueAsText.split(";")

        create_layout = bool(parameters[7].value)
        layout_name = parameters[8].valueAsText
        layout_size = parameters[9].valueAsText
        main_map_name = parameters[10].valueAsText
        mini_map_name = parameters[11].valueAsText

        create_map_series = bool(parameters[12].value)
        map_series_scale = parameters[13].value
        map_series_orientation = parameters[14].valueAsText
        map_series_overlap = parameters[15].value

        messages.addMessage("Creating route and stationing...")

        outputs = create_route_stationing(
            input_line_fc=input_line_fc,
            output_gdb=output_gdb,
            station_interval=station_interval,
            tolerance=tolerance,
            start_measure=start_measure,
            end_measure=end_measure,
        )

        messages.addMessage(f"Route Created: {outputs['route_fc']}")
        messages.addMessage(f"Station Points created: {outputs['station_points']}")
        messages.addMessage(f"Station Event Table Created: {outputs['station_table']}")

        join_station_chainage_to_points(
            station_points=outputs["station_points"],
            station_table=outputs["station_table"],
        )
        messages.addMessage("Chainage joined to station points.")

        event_feature_outputs = None
        band_records = []

        if analysis_layers:
            messages.addMessage("Creating intersections and overlaps...")

            crossing_outputs = create_intersections_and_overlaps(
                route_fc=outputs["route_fc"],
                output_gdb=output_gdb,
                analysis_layers=analysis_layers,
            )
            messages.addMessage(
                "Raw point intersections: "
                + str(crossing_outputs.get("point_intersections", []))
            )

            event_outputs = locate_intersections_and_overlaps(
                route_fc=outputs["route_fc"],
                route_id_field=outputs["route_id_field"],
                tolerance=tolerance,
                out_gdb=output_gdb,
                point_intersections=crossing_outputs["point_intersections"],
                line_overlaps=crossing_outputs["line_overlaps"],
            )
            messages.addMessage(
                "Point event tables: "
                + str(event_outputs.get("point_event_tables", []))
            )
            messages.addMessage(
                f"Raw line overlaps: {crossing_outputs['line_overlaps']}"
            )
            messages.addMessage(
                f"Line event tables: {event_outputs['line_event_tables']}"
            )

            add_chainage_to_event_tables(
                point_event_tables=event_outputs["point_event_tables"],
                line_event_tables=event_outputs["line_event_tables"],
            )

            band_records = build_band_records(
                point_event_tables=event_outputs["point_event_tables"],
                line_event_tables=event_outputs["line_event_tables"],
            )

            messages.addMessage("Band records created:")
            for rec in band_records:
                messages.addMessage(str(rec))

            messages.addMessage("LINE records only:")
            for rec in band_records:
                if rec["type"] == "LINE":
                    messages.addMessage(str(rec))

            event_feature_outputs = make_event_layers_from_tables(
                route_fc=outputs["route_fc"],
                route_id_field=outputs["route_id_field"],
                output_gdb=output_gdb,
                point_event_tables=event_outputs["point_event_tables"],
                line_event_tables=event_outputs["line_event_tables"],
                point_intersections=crossing_outputs["point_intersections"],
            )
            messages.addMessage(
                "Point event features: "
                + str(event_feature_outputs.get("point_event_features", []))
            )

        else:
            messages.addMessage("No intersecting or overlapping features provided.")

        add_output_to_current_map(event_feature_outputs)
        add_output_to_current_map(outputs)

        layout_result = None

        if create_layout:
            messages.addMessage("Generating layout...")

            try:
                layout_result = generate_alignment_layout(
                    layout_name=layout_name,
                    layout_size=layout_size,
                    main_map_name=main_map_name,
                    mini_map_name=mini_map_name,
                    input_line_fc=input_line_fc,
                    output_gdb=output_gdb,
                    create_map_series=create_map_series,
                    map_series_scale=map_series_scale,
                    map_series_orientation=map_series_orientation,
                    map_series_overlap=map_series_overlap,
                )
                messages.addMessage(f"Layout created: {layout_result['layout_name']}")
            except Exception as e:
                messages.addErrorMessage(f"Layout generation failed: {e}")
                raise

        if create_layout and layout_result:
            try:
                route_fc = outputs["route_fc"]

                messages.addMessage(f"route_fc before layout: {route_fc}")
                messages.addMessage(f"type(route_fc): {type(route_fc)}")

                if not arcpy.Exists(route_fc):
                    raise ValueError(
                        f"Invalid route_fc passed to layout logic: {route_fc}"
                    )

                messages.addMessage("Preparing layout band records...")
                band_info = prepare_layout_band_records(
                    route_fc=route_fc,
                    band_records=band_records,
                    band_left=1.0,
                    band_width=10.0,
                    point_row_y=7.5,
                    line_row_y=7.1,
                )

                messages.addMessage(
                    f"Route measure range: {band_info['route_start']} to {band_info['route_end']}"
                )
                messages.addMessage(
                    f"Band records available for layout positioning: {len(band_info['row_ready_records'])}"
                )

                for line in band_info["debug_lines"]:
                    messages.addMessage(line)

                layout = layout_result["layout"]

                row_ready_records = band_info["row_ready_records"]

                point_records = [
                    rec for rec in row_ready_records if rec["type"] == "POINT"
                ]
                point_records = assign_point_label_sides(
                    point_records,
                    top_y=7.5,
                    bottom_y=7.0,
                )
                line_records = [
                    rec for rec in row_ready_records if rec["type"] == "LINE"
                ]
                line_records= assign_point_label_sides(
                    line_records,
                    top_y=7.5,
                    bottom_y=7.5,
                )

                deleted_points = clear_point_band_labels(layout)
                deleted_lines = clear_line_band_labels(layout)

                messages.addMessage(f"Deleted {deleted_points} old point band labels.")
                messages.addMessage(f"Deleted {deleted_lines} old line band labels.")

                created_point_labels = draw_point_band_labels(
                    layout=layout,
                    point_records=point_records,
                    label_y=7.5,
                    text_height=0.12,
                    font_name="Tahoma",
                    label_mode="source_name",
                )

                created_line_labels = draw_line_band_labels(
                    layout=layout,
                    line_records=line_records,
                    label_y=7.1,
                    text_height=0.12,
                    font_name="Tahoma",
                    label_mode="source_name",
                )

                messages.addMessage(
                    f"Created {len(created_point_labels)} point band labels."
                )
                messages.addMessage(
                    f"Created {len(created_line_labels)} line band labels."
                )

                try:
                    messages.addMessage("Opening layout view...")
                    layout.openView()
                except Exception as e:
                    messages.addWarningMessage(
                        f"Layout created, but the view could not be opened automatically: {e}"
                    )

            except Exception as e:
                messages.addErrorMessage(f"Post-layout processing failed: {e}")
                raise

        # if create_layout and layout_result:
        #     map_frame = layout_result["main_map_frame"]

        #     page_start_meas, page_end_meas = get_route_measures_in_current_extent(
        #         outputs["route_fc"],
        #         map_frame,
        #     )

        #     messages.addMessage(f"Page start meas: {page_start_meas}")
        #     messages.addMessage(f"Page end meas: {page_end_meas}")
