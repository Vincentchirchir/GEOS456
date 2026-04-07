import arcpy
import os
import sys
import urllib.request
import urllib.parse
import ssl

tool_folder = os.path.dirname(__file__)
if tool_folder not in sys.path:
    sys.path.append(tool_folder)

from workflow import run_stationing_workflow


def fetch_url_to_local(url, output_fc):
    """Download features from an ArcGIS REST feature service URL to a local feature class."""
    import json

    params = {"where": "1=1", "outFields": "*", "returnGeometry": "true", "f": "json"}
    token_info = arcpy.GetSigninToken()
    if token_info and token_info.get("token"):
        params["token"] = token_info["token"]

    query_url = url.rstrip("/") + "/query?" + urllib.parse.urlencode(params)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(query_url, timeout=60, context=ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if "error" in data:
        raise RuntimeError(f"Feature service error: {data['error']}")

    geom_type = {
        "esriGeometryPoint": "POINT",
        "esriGeometryPolyline": "POLYLINE",
        "esriGeometryPolygon": "POLYGON",
    }.get(data.get("geometryType"), "POLYLINE")

    wkid = data.get("spatialReference", {}).get("wkid", 4326)
    sr = arcpy.SpatialReference(wkid)

    if arcpy.Exists(output_fc):
        arcpy.management.Delete(output_fc)
    arcpy.management.CreateFeatureclass(
        os.path.dirname(output_fc),
        os.path.basename(output_fc),
        geom_type,
        spatial_reference=sr,
    )

    skip_types = {"esriFieldTypeOID", "esriFieldTypeGeometry"}
    field_type_map = {
        "esriFieldTypeString": ("TEXT", 255),
        "esriFieldTypeInteger": ("LONG", None),
        "esriFieldTypeSmallInteger": ("SHORT", None),
        "esriFieldTypeDouble": ("DOUBLE", None),
        "esriFieldTypeSingle": ("FLOAT", None),
        "esriFieldTypeDate": ("DATE", None),
    }
    add_fields = []
    for f in data.get("fields", []):
        if f["type"] in skip_types:
            continue
        arcpy_type, length = field_type_map.get(f["type"], ("TEXT", 255))
        kwargs = {"field_length": length} if length else {}
        arcpy.management.AddField(output_fc, f["name"], arcpy_type, **kwargs)
        add_fields.append(f["name"])

    with arcpy.da.InsertCursor(output_fc, ["SHAPE@JSON"] + add_fields) as cur:
        for feat in data.get("features", []):
            geom = json.dumps(feat.get("geometry") or {})
            attrs = [feat["attributes"].get(fn) for fn in add_fields]
            cur.insertRow([geom] + attrs)

    return output_fc


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
            name="input_line",
            datatype="GPFeatureRecordSetLayer",
            parameterType="Required",
            direction="Input",
        )
        station_interval = arcpy.Parameter(
            displayName="Station Interval",
            name="station_interval",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="Input",
        )
        station_interval.value = "100 Meters"

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

        tolerance = arcpy.Parameter(
            displayName="Search Tolerance",
            name="tolerance",
            datatype="GPLinearUnit",
            parameterType="Optional",
            direction="Input",
        )
        tolerance.value = "1 Meter"

        analysis_layers = arcpy.Parameter(
            displayName="Overlapping or Intersecting Features",
            name="analysis_layers",
            datatype="GPFeatureRecordSetLayer",
            parameterType="Optional",
            direction="Input",
        )
        analysis_layers.multiValue = True

        out_route = arcpy.Parameter(
            displayName="Output Route",
            name="out_route",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output",
        )

        out_stations = arcpy.Parameter(
            displayName="Output Station Points",
            name="out_stations",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output",
        )

        out_intersections = arcpy.Parameter(
            displayName="Output Intersections",
            name="out_intersections",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output",
        )

        out_overlaps = arcpy.Parameter(
            displayName="Output Overlaps",
            name="out_overlaps",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output",
        )

        out_segment = arcpy.Parameter(
            displayName="Output Segment",
            name="out_segment",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output",
        )

        input_line.description = "Select the main polyline feature to station."
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
            input_line,  # 0
            station_interval,  # 1
            start_measure,  # 2
            end_measure,  # 3
            tolerance,  # 4
            analysis_layers,  # 5
            out_route,  # 6
            out_stations,  # 7
            out_intersections,  # 8
            out_overlaps,  # 9
            out_segment,  # 10
        ]

    def updateMessages(self, parameters):
        input_line = parameters[0]
        station_interval = parameters[1]
        start_measure = parameters[2]
        end_measure = parameters[3]
        tolerance = parameters[4]
        analysis_layers = parameters[5]

        if tolerance.value:
            try:
                tol = float(tolerance.valueAsText.split()[0])
                if tol <= 0:
                    tolerance.setErrorMessage("Tolerance must be greater than zero.")
                elif tol > 100:
                    tolerance.setWarningMessage(
                        "Large tolerance may snap unrelated features to the route."
                    )
            except:
                tolerance.setErrorMessage("Invalid tolerance value. Example: 1 Meters")

        if station_interval.value:
            try:
                interval_parts = station_interval.valueAsText.split()
                if len(interval_parts) < 2:
                    station_interval.setErrorMessage(
                        "Station Interval must include a number and unit. Example: 100 Meters."
                    )
                else:
                    numeric_value = float(interval_parts[0])
                    if numeric_value <= 0:
                        station_interval.setErrorMessage(
                            "Station Interval must be greater than zero."
                        )
                    elif numeric_value < 0.01:
                        station_interval.setWarningMessage(
                            "Station Interval is extremely small. This may create too many points."
                        )
                    elif numeric_value < 1:
                        station_interval.setWarningMessage(
                            "Station Interval is very small. Confirm this is intentional."
                        )
            except Exception:
                station_interval.setErrorMessage(
                    "Invalid Station Interval. Example: 10 Meters."
                )

        if start_measure.value is None and end_measure.value is not None:
            start_measure.setWarningMessage(
                "Start Measure is empty. The tool will assume 0."
            )

        if start_measure.value is not None:
            try:
                sm = float(start_measure.value)
                if sm < 0:
                    start_measure.setWarningMessage(
                        "Start Measure is negative. Confirm this is intentional."
                    )
            except Exception:
                start_measure.setErrorMessage("Start Measure must be numeric.")

        if end_measure.value is not None:
            try:
                float(end_measure.value)
            except Exception:
                end_measure.setErrorMessage("End Measure must be numeric.")

        if start_measure.value is not None and end_measure.value is not None:
            try:
                sm = float(start_measure.value)
                em = float(end_measure.value)
                if em <= sm:
                    end_measure.setErrorMessage(
                        "End Measure must be greater than Start Measure."
                    )
                elif (em - sm) < 1:
                    end_measure.setWarningMessage(
                        "The selected measure range is very short."
                    )
            except Exception:
                pass

    def execute(self, parameters, messages):
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = arcpy.env.scratchGDB
        arcpy.env.scratchWorkspace = arcpy.env.scratchGDB

        input_line_fc = parameters[0].valueAsText
        scratch = arcpy.env.scratchGDB

        if input_line_fc and input_line_fc.startswith("http"):
            local_input = scratch + "\\input_line_local"
            input_line_fc = fetch_url_to_local(input_line_fc, local_input)
            messages.addMessage("Input feature downloaded from URL to scratch.")

        try:
            arcpy.env.outputCoordinateSystem = arcpy.Describe(
                input_line_fc
            ).spatialReference
        except Exception:
            pass

        station_interval = parameters[1].valueAsText

        start_measure = 0
        if parameters[2].value is not None:
            start_measure = float(parameters[2].value)

        end_measure = None
        if parameters[3].value is not None:
            end_measure = float(parameters[3].value)

        tolerance = "1 Meter"
        if parameters[4].valueAsText:
            tolerance = parameters[4].valueAsText

        analysis_layers = []
        if parameters[5].valueAsText:
            analysis_layers = parameters[5].valueAsText.split(";")

        localized_layers = []
        for i, lyr in enumerate(analysis_layers):
            if lyr and lyr.startswith("http"):
                local_lyr = scratch + f"\\analysis_layer_{i}_local"
                lyr = fetch_url_to_local(lyr, local_lyr)
                messages.addMessage(
                    f"Analysis layer {i} downloaded from URL to scratch."
                )
            localized_layers.append(lyr)
        analysis_layers = localized_layers

        messages.addMessage(f"Input feature: {input_line_fc}")
        messages.addMessage(f"Station interval: {station_interval}")
        messages.addMessage(f"Start measure: {start_measure}")
        messages.addMessage(f"End measure: {end_measure}")
        messages.addMessage(f"Tolerance: {tolerance}")
        messages.addMessage(f"Analysis layers: {analysis_layers}")
        messages.addMessage(f"Scratch GDB: {scratch}")

        outputs = run_stationing_workflow(
            input_line_fc=input_line_fc,
            station_interval=station_interval,
            tolerance=tolerance,
            start_measure=start_measure,
            end_measure=end_measure,
            analysis_layers=analysis_layers,
            messages=messages,
        )

        messages.addMessage(f"Output route: {outputs.route}")
        messages.addMessage(f"Output stations: {outputs.stations}")

        arcpy.SetParameter(6, outputs.route)
        arcpy.SetParameter(7, outputs.stations)

        intersection_output = getattr(outputs, "intersection_output", None)
        if not intersection_output and hasattr(outputs, "intersections") and outputs.intersections:
            intersection_output = outputs.intersections[0]

        if intersection_output:
            messages.addMessage(
                f"Intersections created: {len(outputs.intersections)} layer(s)"
            )
            arcpy.SetParameter(8, intersection_output)
        else:
            empty_pts = scratch + "\\empty_intersections"
            if arcpy.Exists(empty_pts):
                arcpy.management.Delete(empty_pts)
            arcpy.management.CreateFeatureclass(scratch, "empty_intersections", "POINT")
            arcpy.SetParameter(8, empty_pts)

        overlap_output = getattr(outputs, "overlap_output", None)
        if not overlap_output and hasattr(outputs, "overlaps") and outputs.overlaps:
            overlap_output = outputs.overlaps[0]

        if overlap_output:
            messages.addMessage(f"Overlaps created: {len(outputs.overlaps)} layer(s)")
            arcpy.SetParameter(9, overlap_output)
        else:
            empty_lines = scratch + "\\empty_overlaps"
            if arcpy.Exists(empty_lines):
                arcpy.management.Delete(empty_lines)
            arcpy.management.CreateFeatureclass(scratch, "empty_overlaps", "POLYLINE")
            arcpy.SetParameter(9, empty_lines)

        if hasattr(outputs, "segment") and outputs.segment:
            messages.addMessage(f"Output segment: {outputs.segment}")
            arcpy.SetParameter(10, outputs.segment)
