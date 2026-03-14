import arcpy, os, sys

tool_folder = os.path.dirname(__file__)
if tool_folder not in sys.path:
    sys.path.append(tool_folder)

from route_tools import create_route_with_measure_system, create_stationing_source_line
from stationing_tools import (
    remove_duplicate_station_measures,
    join_station_chainage_to_points,
    create_route_and_stationing,
)
from events_tools import (
    create_intersections_and_overlaps,
    locate_intersections_and_overlaps,
    chainage_code_block,
    add_chainage_to_event_tables,
    make_event_layers_from_tables,
)
from map_tools import add_outputs_to_current_map


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
            direction="input",
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

        return [
            input_line,
            output_gdb,
            station_interval,
            start_measure,
            end_measure,
            tolerance,
            analysis_layers,
        ]

    def updateMessages(self, parameters):
        input_line = parameters[0]
        output_gdb = parameters[1]
        station_interval = parameters[2]
        start_measure = parameters[3]
        end_measure = parameters[4]
        tolerance = parameters[5]
        analysis_layers = parameters[6]

        # validate tolerance
        if tolerance.value:
            try:
                tol = float(tolerance.valueAsText.split()[0])

                if tol <= 0:
                    tolerance.setErrorMesage("Tolerance must be greate than zero")
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
                sm=float(start_measure.value)
                em=float(end_measure.value)

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