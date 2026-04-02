import arcpy
import os
import sys
import importlib
import route_tools, stationing_tools, events_tools, map_tools

tool_folder = os.path.dirname(__file__)
if tool_folder not in sys.path:
    sys.path.append(tool_folder)

from route_tools import create_route_with_measure_system, create_stationing_source_line
from stationing_tools import (
    remove_duplicate_station_measure,
    join_station_chainage_to_points,
    create_route_stationing,
)
from events_tools import (
    create_intersections_and_overlaps,
    locate_intersections_and_overlaps,
    chainage_code_block,
    add_chainage_to_event_tables,
    make_event_layers_from_tables,
)
from map_tools import add_output_to_current_map



importlib.reload(route_tools)
importlib.reload(stationing_tools)
importlib.reload(events_tools)
importlib.reload(map_tools)

class Toolbox(object):
    def __init__(self):
        self.label = "Stationing and Linear Referencing Tools"
        self.alias = "stationingtools"
        self.tools = [GenerateStationing]


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
            parameterType="Optional",
            direction="Input",
        )

        # setting default gdb — only available in desktop, silently skipped on server
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

        # Filter to polyline layers in active map — only available in desktop, silently skipped on server
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

        # Desriptions to tools that shows when you hover the parameter
        input_line.description = "Select the main polyline feature to station."
        output_gdb.description = "Choose the output file geodatabase. Leave blank to write to the server scratch geodatabase (recommended for web tool use)."
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

        # --- Enterprise-compatible output parameters ---
        # Declaring these as Derived outputs lets web tool clients receive the
        # result feature classes after the job completes on the server.
        out_route_fc = arcpy.Parameter(
            displayName="Output Route Feature Class",
            name="out_route_fc",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output",
        )

        out_station_points = arcpy.Parameter(
            displayName="Output Station Points",
            name="out_station_points",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output",
        )

        return [
            input_line,       # 0
            output_gdb,       # 1
            station_interval, # 2
            start_measure,    # 3
            end_measure,      # 4
            tolerance,        # 5
            analysis_layers,  # 6
            out_route_fc,     # 7  (Derived output — Enterprise web tool)
            out_station_points,  # 8  (Derived output — Enterprise web tool)
        ]



    def updateMessages(self, parameters):
        input_line = parameters[0]
        output_gdb = parameters[1]
        station_interval = parameters[2]
        start_measure = parameters[3]
        end_measure = parameters[4]
        tolerance = parameters[5]
        analysis_layers = parameters[6]

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

        # Active map check — only warn if we can confirm we are in a desktop
        # session with no active map. On server this block is silently skipped.
        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            if aprx.activeMap is None:
                input_line.setWarningMessage(
                    "No active map detected. You may need to browse to input layers manually."
                )
        except:
            # Running on ArcGIS Server or outside a Pro session — no warning needed.
            pass

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
        # When blank the tool falls back to arcpy.env.scratchGDB at runtime,
        # so an empty value is valid (web tool clients will leave this blank).
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
        output_gdb = parameters[1].valueAsText or arcpy.env.scratchGDB
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
                out_gdb=output_gdb,
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
            messages.addMessage("No intersecting or overlapping features provided.")

        # --- Set Derived output parameter values for Enterprise web tool clients ---
        parameters[7].value = outputs["route_fc"]
        parameters[8].value = outputs["station_points"]

        # Add outputs to map when running in ArcGIS Pro desktop — silently
        # skipped on ArcGIS Server where arcpy.mp is not available.
        add_output_to_current_map(outputs)
