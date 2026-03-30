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
import auto_populate
import map_series_tools_v3


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

from band_tools import (
    build_band_records,
    get_route_measure_range,
    get_route_measures_in_current_extent,
    build_layout_band_positions,
    prepare_layout_band_records,
    clear_line_band_labels,
    draw_line_band_labels,
    assign_line_label_sides,
    filter_point_records_for_labeling,
    build_point_records_with_layout_xy,
    draw_point_ticks_and_labels,
    clear_point_ticks_and_labels,
)
from auto_populate import auto_populate_layout
from map_series_tools_v3 import update_map_series_pages, create_layout_map_series
from band_tools import build_line_records_with_layout_xy

importlib.reload(route_tools_v3)
importlib.reload(stationing_tools_v3)
importlib.reload(events_tools_v3)
importlib.reload(map_tools_v3)
importlib.reload(layout_tools_v3)
importlib.reload(layout_elements_v3)
importlib.reload(band_tools)
importlib.reload(auto_populate)
importlib.reload(map_series_tools_v3)


# Import band-position constants from layout_elements_v3 AFTER the reload so
# any in-session changes to that module are reflected here without restarting.
# Single source of truth — do NOT redefine these here.
from layout_elements_v3 import (
    BAND_TOP_UPPER_FRAC,
    BAND_BOTTOM_UPPER_FRAC,
    BAND_TOP_LOWER_FRAC,
    BAND_BOTTOM_LOWER_FRAC,
    TOP_BAR1_FRAC,
    TOP_BAR2_FRAC,
    TOP_BAR3_FRAC,
    TOP_BAR4_FRAC,
    BOT_BAR4_FRAC,
    BOT_BAR5_FRAC,
    BOT_BAR6_FRAC,
    BOT_BAR7_FRAC,
)


def _get_stationing_band_geometry(layout, map_frame):
    """
    Returns geometry for both the top and bottom stationing bands.

    All positions are derived from the page height so the layout
    scales correctly if the page size changes.

    The top band sits above the map frame (9.50" to 10.50" on an 11" page).
    The bottom band sits below the map frame (2.17" to 3.17" on an 11" page).

    Returns
    -------
    dict with keys:
        band_left           -- left edge of both bands (matches map frame left)
        band_width          -- width of both bands (matches map frame width)

        -- TOP BAND --
        top_band_top        -- top edge of top band in inches
        top_band_bottom     -- bottom edge of top band = top of map frame
        top_label_bar1_y    -- label y for odd records (Bar 1 centre)
        top_label_bar3_y    -- label y for even records (Bar 3 centre)

        -- BOTTOM BAND --
        bot_band_top        -- top edge of bottom band = bottom of map frame
        bot_band_bottom     -- bottom edge of bottom band in inches
        bot_label_bar5_y    -- label y for odd records (Bar 5 centre)
        bot_label_bar6_y    -- label y for even records (Bar 6 centre)
    """
    page_height = layout.pageHeight  # full page height in inches

    # Three label rows cycling through the top band gaps

    # Band left and width follow the map frame so ticks align with the map
    band_left = map_frame.elementPositionX
    band_width = map_frame.elementWidth

    # Top band positions
    top_band_top = page_height * BAND_TOP_UPPER_FRAC  # 10.50"
    # top_band_bottom = page_height * BAND_BOTTOM_UPPER_FRAC  #  9.50"
    top_band_bottom = (
        map_frame.elementPositionY + map_frame.elementHeight
    )  # top edge of frame

    # Four label rows — each sits in the centre of a gap between bar lines
    # Row 1: gap between top border and Bar 1
    top_label_row1_y = page_height * ((BAND_TOP_UPPER_FRAC + TOP_BAR1_FRAC) / 2)

    # Row 2: gap between Bar 1 and Bar 2
    top_label_row2_y = page_height * ((TOP_BAR1_FRAC + TOP_BAR2_FRAC) / 2)

    # Row 3: gap between Bar 2 and Bar 3
    top_label_row3_y = page_height * ((TOP_BAR2_FRAC + TOP_BAR3_FRAC) / 2)

    # Row 4: gap between Bar 3 and Bar 4
    top_label_row4_y = page_height * ((TOP_BAR3_FRAC + TOP_BAR4_FRAC) / 2)

    # Bottom band positions
    bot_band_top = map_frame.elementPositionY  # bottom edge of frame
    bot_band_bottom = page_height * BAND_BOTTOM_LOWER_FRAC

    # Four label rows for the bottom band
    # Row 1: gap between band top border and Bot Bar 4
    bot_label_row1_y = page_height * ((BAND_TOP_LOWER_FRAC + BOT_BAR4_FRAC) / 2)

    # Row 2: gap between Bot Bar 4 and Bot Bar 5
    bot_label_row2_y = page_height * ((BOT_BAR4_FRAC + BOT_BAR5_FRAC) / 2)

    # Row 3: gap between Bot Bar 5 and Bot Bar 6
    bot_label_row3_y = page_height * ((BOT_BAR5_FRAC + BOT_BAR6_FRAC) / 2)

    # Row 4: gap between Bot Bar 6 and Bot Bar 7
    bot_label_row4_y = page_height * ((BOT_BAR6_FRAC + BOT_BAR7_FRAC) / 2)

    return {
        "band_left": band_left,
        "band_width": band_width,
        # Top band
        "top_band_top": top_band_top,
        "top_band_bottom": top_band_bottom,  # = top of map frame
        "top_label_row1_y": top_label_row1_y,
        "top_label_row2_y": top_label_row2_y,
        "top_label_row3_y": top_label_row3_y,
        "top_label_row4_y": top_label_row4_y,
        # Bottom band
        "bot_band_top": bot_band_top,  # = bottom of map frame
        "bot_band_bottom": bot_band_bottom,
        "bot_label_row1_y": bot_label_row1_y,
        "bot_label_row2_y": bot_label_row2_y,
        "bot_label_row3_y": bot_label_row3_y,
        "bot_label_row4_y": bot_label_row4_y,
    }


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

        export_pdf = arcpy.Parameter(
            displayName="Export Map Series to PDF",
            name="export_pdf",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        export_pdf.value = False

        pdf_output_folder = arcpy.Parameter(
            displayName="PDF Output Folder",
            name="pdf_output_folder",
            datatype="DEFolder",
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
            export_pdf,           # 16 
            pdf_output_folder,    # 17 
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

        # Enable export PDF only when both layout and map series are checked
        if create_layout.value and create_map_series.value:
            parameters[16].enabled = True  # export_pdf
        else:
            parameters[16].enabled = False
            parameters[17].enabled = False

        # Enable PDF folder only when export PDF is checked
        if create_layout.value and create_map_series.value and parameters[16].value:
            parameters[17].enabled = True
        else:
            parameters[17].enabled = False

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

        export_pdf        = bool(parameters[16].value)
        pdf_output_folder = parameters[17].valueAsText

        if event_feature_outputs:
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
            route_fc = outputs["route_fc"]

            messages.addMessage(f"route_fc before layout: {route_fc}")
            messages.addMessage(f"type(route_fc): {type(route_fc)}")

            if not arcpy.Exists(route_fc):
                raise ValueError(f"Invalid route_fc passed to layout logic: {route_fc}")

            messages.addMessage("Preparing layout band records...")

            layout = layout_result["layout"]
            map_frame = layout_result["main_map_frame"]
            route_fc = outputs["route_fc"]

            # Build geometry for both stationing bands from the actual layout
            band_geom = _get_stationing_band_geometry(layout, map_frame)

            band_left = band_geom["band_left"]
            band_width = band_geom["band_width"]

            messages.addMessage(
                f"Band geometry -> left={band_left:.4f}, width={band_width:.4f}"
            )
            messages.addMessage(
                f"Top band    -> bottom={band_geom['top_band_bottom']:.4f}, "
                f"top={band_geom['top_band_top']:.4f}"
            )
            messages.addMessage(
                f"Bottom band -> bottom={band_geom['bot_band_bottom']:.4f}, "
                f"top={band_geom['bot_band_top']:.4f}"
            )

            # Get the full route measure range for the current page
            route_start, route_end = get_route_measure_range(route_fc)
            messages.addMessage(f"Using measure range: {route_start} to {route_end}")

            # Line overlap labels — drawn in the top band only
            band_info = prepare_layout_band_records(
                band_records=band_records,
                band_left=band_left,
                band_width=band_width,
                point_row_y=band_geom["top_label_row1_y"],
                line_row_y=band_geom["top_label_row1_y"],
                route_start=route_start,
                route_end=route_end,
            )

            row_ready_records = band_info["row_ready_records"]

            # Separate point and line records
            point_records = [r for r in row_ready_records if r["type"] == "POINT"]
            line_records = [r for r in row_ready_records if r["type"] == "LINE"]

            # Remove point labels already covered by line overlap labels
            point_records = filter_point_records_for_labeling(
                point_records, line_records
            )

            # Assign alternating rows to line overlap labels (top band only)
            line_records = assign_line_label_sides(
                line_records,
                top_y=band_geom["top_label_row1_y"],
                bottom_y=band_geom["top_label_row3_y"],
            )

            # Point ticks and labels — drawn across BOTH bands
            # Odd records  → tick at TOP band bottom edge, label in top band
            # Even records → tick at BOTTOM band top edge, label in bottom band
            if event_feature_outputs and event_feature_outputs.get(
                "point_event_features"
            ):

                # Clear any old ticks and labels before redrawing
                clear_point_ticks_and_labels(layout)

                # Build records with real map layout coordinates for each point

                # Build point records
                point_records_with_xy = build_point_records_with_layout_xy(
                    point_event_features=event_feature_outputs["point_event_features"],
                    map_frame=map_frame,
                    route_start=route_start,
                    route_end=route_end,
                    band_left=band_left,
                    band_width=band_width,
                )

                # Build line records
                line_records_with_xy = build_line_records_with_layout_xy(
                    line_event_features=event_feature_outputs["line_event_features"],
                    map_frame=map_frame,
                    route_start=route_start,
                    route_end=route_end,
                    band_left=band_left,
                    band_width=band_width,
                )

                # Get source names that have overlap records
                line_source_names = {r.get("source_name") for r in line_records_with_xy}

                # Log what will be filtered so you can verify
                arcpy.AddMessage(
                    f"Line source names (will filter from points): {line_source_names}"
                )

                # Remove POINT records whose source also appears as a LINE overlap
                # — the overlap entry/exit ticks already cover those crossings
                point_records_with_xy = [
                    r
                    for r in point_records_with_xy
                    if r.get("source_name") not in line_source_names
                ]

                arcpy.AddMessage(
                    f"Point records after filter: {len(point_records_with_xy)}"
                )
                arcpy.AddMessage(f"Line records: {len(line_records_with_xy)}")

                # Combine — points to top band, lines to bottom band
                all_records_with_xy = point_records_with_xy + line_records_with_xy

                # Draw ticks and labels
                ticks = draw_point_ticks_and_labels(
                    layout=layout,
                    point_records=all_records_with_xy,
                    band_y_top=band_geom["top_band_bottom"],
                    band_y_bottom=band_geom["bot_band_top"],
                    label_top_row1_y=band_geom["top_label_row1_y"],
                    label_top_row2_y=band_geom["top_label_row2_y"],
                    label_top_row3_y=band_geom["top_label_row3_y"],
                    label_top_row4_y=band_geom["top_label_row4_y"],
                    label_bottom_row1_y=band_geom["bot_label_row1_y"],
                    label_bottom_row2_y=band_geom["bot_label_row2_y"],
                    label_bottom_row3_y=band_geom["bot_label_row3_y"],
                    label_bottom_row4_y=band_geom["bot_label_row4_y"],
                    half_tick=0.1,
                    text_height=0.17,
                    font_name="Tahoma",
                )

                messages.addMessage(f"Created {len(ticks)} tick marks.")

            else:
                # No analysis layers were provided — nothing to tick
                messages.addMessage(
                    "No analysis layers provided — skipping tick drawing."
                )

            # Auto-populate all derivable text elements on the layout
            auto_populate_layout(
                layout=layout,
                project=arcpy.mp.ArcGISProject("CURRENT"),
                width=layout_result["width"],
                height=layout_result["height"],
                input_line_fc=input_line_fc,
                route_fc=route_fc,
                route_start=route_start,
                route_end=route_end,
                band_records=band_records,
            )

            if create_map_series and layout_result.get("map_series_info"):
                map_series_info = layout_result["map_series_info"]

                update_map_series_pages(
                    layout=layout,
                    map_frame=map_frame,
                    map_series=map_series_info["map_series"],
                    index_fc=map_series_info["index_fc"],
                    route_fc=route_fc,
                    band_records=band_records,
                    point_event_features=event_feature_outputs["point_event_features"] if event_feature_outputs else [],
                    line_event_features=event_feature_outputs["line_event_features"] if event_feature_outputs else [],
                    band_geom=band_geom,
                    route_start=route_start,
                    route_end=route_end,
                    input_line_fc=input_line_fc,
                    project=arcpy.mp.ArcGISProject("CURRENT"),
                    width=layout_result["width"],
                    height=layout_result["height"],
                    scale=map_series_scale,
                    export_pdf=export_pdf,
                    pdf_output_folder=pdf_output_folder,
                    layout_name=layout_name,
                )
                messages.addMessage("Map series pages updated.")

            # try:
            #     layout.openView()
            # except Exception as e:
            #     messages.addWarningMessage(
            #         f"Layout created but could not open automatically: {e}"
            # )
            # if create_layout and layout_result:
        #     map_frame = layout_result["main_map_frame"]

        #     page_start_meas, page_end_meas = get_route_measures_in_current_extent(
        #         outputs["route_fc"],
        #         map_frame,
        #     )

        #     messages.addMessage(f"Page start meas: {page_start_meas}")
        #     messages.addMessage(f"Page end meas: {page_end_meas}")
