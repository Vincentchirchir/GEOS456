"""
ArcGIS Online notebook wrapper for the v6 stationing workflow.

Upload these existing helper files into the notebook workspace before running:
- workflow.py
- route_tools.py
- stationing_tools.py
- events_tools.py
- map_tools.py

Recommended notebook input parameters:
- input_line (Feature set, required)
- station_interval (Linear unit, required)
- start_measure (Double, optional)
- end_measure (Double, optional)
- tolerance (Linear unit, optional)
- analysis_layer (Feature set, optional)
- analysis_layer_2 (Feature set, optional)
- analysis_layer_3 (Feature set, optional)

Recommended notebook output parameters:
- out_route (Feature set)
- out_stations (Feature set)
- out_intersections (Feature set)
- out_overlaps (Feature set)
- out_segment (Feature set)
"""

import os
import sys

import arcpy
from arcgis.features import FeatureSet as AGSFeatureSet


tool_folder = os.getcwd()
if tool_folder not in sys.path:
    sys.path.insert(0, tool_folder)

from workflow import run_stationing_workflow


class NotebookMessages:
    def addMessage(self, text):
        text = str(text)
        print(text)
        arcpy.AddMessage(text)

    def addWarningMessage(self, text):
        text = str(text)
        print(f"WARNING: {text}")
        arcpy.AddWarning(text)

    def addErrorMessage(self, text):
        text = str(text)
        print(f"ERROR: {text}")
        arcpy.AddError(text)


def prepare_notebook_environment():
    arcpy.SignInToPortal("notebook")
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = arcpy.env.scratchGDB
    arcpy.env.scratchWorkspace = arcpy.env.scratchGDB


def _pick_wkid(sr_dict):
    if not sr_dict:
        return None
    return sr_dict.get("latestWkid") or sr_dict.get("wkid")


def apply_context_environment(context):
    if not context:
        return

    extent = context.get("extent")
    if extent:
        arcpy.env.extent = arcpy.Extent(
            extent["xmin"],
            extent["ymin"],
            extent["xmax"],
            extent["ymax"],
        )

    out_sr = context.get("outSR")
    wkid = _pick_wkid(out_sr)
    if wkid:
        arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(wkid)


def linear_unit_to_text(value, default_text=None):
    if value in (None, ""):
        return default_text

    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        distance = value.get("distance")
        units = value.get("units")
        unit_map = {
            "esriMeters": "Meters",
            "esriKilometers": "Kilometers",
            "esriFeet": "Feet",
            "esriMiles": "Miles",
            "esriYards": "Yards",
            "esriNauticalMiles": "NauticalMiles",
        }
        if distance is None or not units:
            return default_text
        return f"{distance} {unit_map.get(units, units)}"

    return default_text


def _to_ags_featureset(value):
    if value is None:
        return None

    if isinstance(value, AGSFeatureSet):
        return value

    if isinstance(value, dict):
        return AGSFeatureSet.from_dict(value)

    if isinstance(value, str):
        text = value.strip()
        if text.startswith("{") or text.startswith("["):
            return AGSFeatureSet.from_json(text)
        return None

    if hasattr(value, "features") and hasattr(value, "fields"):
        return value

    if hasattr(value, "JSON"):
        return AGSFeatureSet.from_json(value.JSON)

    return None


def input_value_to_feature_class(value, out_name):
    if value in (None, "", {}):
        return None

    out_fc = os.path.join(arcpy.env.scratchGDB, out_name)
    if arcpy.Exists(out_fc):
        arcpy.management.Delete(out_fc)

    if isinstance(value, str):
        text = value.strip()
        if text.lower().startswith("http") or arcpy.Exists(text):
            arcpy.management.CopyFeatures(text, out_fc)
            return out_fc

    ags_fs = _to_ags_featureset(value)
    if ags_fs is None:
        raise TypeError(f"Unsupported feature input type for {out_name}.")

    sdf = ags_fs.sdf
    if sdf is None or sdf.empty:
        return None

    sdf.spatial.to_featureclass(location=out_fc)
    return out_fc


def feature_class_to_output_featureset(fc_path):
    if not fc_path or not arcpy.Exists(fc_path):
        return None

    fs = arcpy.FeatureSet()
    fs.load(fc_path)
    return AGSFeatureSet.from_arcpy(fs)


def create_empty_output_featureclass(name, geometry_type, template_fc=None):
    out_fc = os.path.join(arcpy.env.scratchGDB, name)
    if arcpy.Exists(out_fc):
        arcpy.management.Delete(out_fc)

    spatial_reference = None
    if template_fc and arcpy.Exists(template_fc):
        try:
            spatial_reference = arcpy.Describe(template_fc).spatialReference
        except Exception:
            spatial_reference = None

    arcpy.management.CreateFeatureclass(
        os.path.dirname(out_fc),
        os.path.basename(out_fc),
        geometry_type,
        spatial_reference=spatial_reference,
    )
    return out_fc


def run_notebook_web_tool():
    prepare_notebook_environment()
    apply_context_environment(globals().get("context"))

    messages = NotebookMessages()

    input_line_value = globals().get("input_line")
    if input_line_value in (None, "", {}):
        raise ValueError("Notebook input parameter 'input_line' is required.")

    station_interval_text = linear_unit_to_text(globals().get("station_interval"))
    if not station_interval_text:
        raise ValueError("Notebook input parameter 'station_interval' is required.")

    start_measure_value = globals().get("start_measure")
    start_measure_value = (
        float(start_measure_value) if start_measure_value not in (None, "") else 0.0
    )

    end_measure_value = globals().get("end_measure")
    end_measure_value = (
        float(end_measure_value) if end_measure_value not in (None, "") else None
    )

    tolerance_text = linear_unit_to_text(globals().get("tolerance"), "1 Meters")

    input_line_fc = input_value_to_feature_class(input_line_value, "input_line_fc")
    if not input_line_fc:
        raise ValueError("The input line feature set is empty.")

    try:
        arcpy.env.outputCoordinateSystem = arcpy.Describe(input_line_fc).spatialReference
    except Exception:
        pass

    analysis_layers = []
    for idx, param_name in enumerate(
        ("analysis_layer", "analysis_layer_2", "analysis_layer_3"),
        start=1,
    ):
        value = globals().get(param_name)
        if value in (None, "", {}):
            continue
        local_fc = input_value_to_feature_class(value, f"{param_name}_{idx}")
        if local_fc:
            analysis_layers.append(local_fc)

    messages.addMessage(f"Input feature: {input_line_fc}")
    messages.addMessage(f"Station interval: {station_interval_text}")
    messages.addMessage(f"Start measure: {start_measure_value}")
    messages.addMessage(f"End measure: {end_measure_value}")
    messages.addMessage(f"Tolerance: {tolerance_text}")
    messages.addMessage(f"Analysis layers: {analysis_layers}")
    messages.addMessage(f"Scratch GDB: {arcpy.env.scratchGDB}")

    outputs = run_stationing_workflow(
        input_line_fc=input_line_fc,
        station_interval=station_interval_text,
        tolerance=tolerance_text,
        start_measure=start_measure_value,
        end_measure=end_measure_value,
        analysis_layers=analysis_layers,
        messages=messages,
    )

    if not outputs.intersection_output:
        outputs.intersection_output = create_empty_output_featureclass(
            "empty_intersections",
            "POINT",
            template_fc=outputs.route,
        )

    if not outputs.overlap_output:
        outputs.overlap_output = create_empty_output_featureclass(
            "empty_overlaps",
            "POLYLINE",
            template_fc=outputs.route,
        )

    return {
        "out_route": feature_class_to_output_featureset(outputs.route),
        "out_stations": feature_class_to_output_featureset(outputs.stations),
        "out_intersections": feature_class_to_output_featureset(
            outputs.intersection_output
        ),
        "out_overlaps": feature_class_to_output_featureset(outputs.overlap_output),
        "out_segment": feature_class_to_output_featureset(outputs.segment),
    }


if "input_line" in globals() and "station_interval" in globals():
    _tool_outputs = run_notebook_web_tool()
    out_route = _tool_outputs["out_route"]
    out_stations = _tool_outputs["out_stations"]
    out_intersections = _tool_outputs["out_intersections"]
    out_overlaps = _tool_outputs["out_overlaps"]
    out_segment = _tool_outputs["out_segment"]
else:
    print(
        "Insert notebook input variables from the Parameters pane or define "
        "test values above this cell before running the script."
    )
