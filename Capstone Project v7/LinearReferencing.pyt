import arcpy
import importlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import ssl

tool_folder = os.path.dirname(__file__)
if tool_folder not in sys.path:
    sys.path.append(tool_folder)

import route_tools
import stationing_tools
import events_tools
import map_tools
import output_fields
import publish_tools
import workflow

for module in (
    output_fields,
    publish_tools,
    route_tools,
    stationing_tools,
    events_tools,
    map_tools,
    workflow,
):
    importlib.reload(module)

run_stationing_workflow = workflow.run_stationing_workflow


def is_placeholder_layer_name(name):
    return not output_fields.is_meaningful_display_name(name)


def normalize_layer_name_candidate(value):
    if value in (None, ""):
        return None

    text = str(value).strip().strip('"').strip("'")
    if not text or text.startswith("<"):
        return None

    if text.startswith("http"):
        return get_service_layer_name(text)

    if text.lstrip().startswith("{") or text.lstrip().startswith("["):
        return None

    # Keep plain layer titles exactly as ArcGIS provides them.
    # Only collapse file-system-like paths down to their basename.
    if "\\" in text or "/" in text:
        text = os.path.basename(text.rstrip("/\\")) or text

    # Remove only common file extensions, not arbitrary suffixes.
    lowered = text.lower()
    for extension in (".shp", ".geojson", ".json", ".kml", ".kmz", ".csv", ".zip"):
        if lowered.endswith(extension):
            text = text[: -len(extension)]
            break

    text = text.strip()
    return text or None


def choose_best_layer_name(candidates, fallback_name=None):
    unique_candidates = []
    seen = set()

    for value in candidates:
        candidate = normalize_layer_name_candidate(value)
        if not candidate or is_placeholder_layer_name(candidate):
            continue

        key = candidate.casefold()
        if key in seen:
            continue

        seen.add(key)
        unique_candidates.append(candidate)

    if not unique_candidates:
        return fallback_name

    # Prefer the most descriptive visible name rather than shortened internal names.
    unique_candidates.sort(
        key=lambda name: (
            len(name.replace("_", "").replace(" ", "")),
            len(name),
            name,
        ),
        reverse=True,
    )
    return unique_candidates[0]


def collect_layer_name_candidates_from_json(payload, candidates=None):
    candidates = candidates or []

    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key).lower()
            if "url" in key_text and isinstance(value, str):
                candidates.append(get_service_layer_name(value))

            if any(token in key_text for token in ("name", "title", "label", "alias")):
                candidates.append(value)

            if key in {"fields", "features", "geometry", "attributes"}:
                continue
            if isinstance(value, (dict, list)):
                collect_layer_name_candidates_from_json(value, candidates)

    elif isinstance(payload, list):
        for item in payload:
            collect_layer_name_candidates_from_json(item, candidates)

    return candidates


def extract_layer_name_from_json(text):
    if text in (None, ""):
        return None

    raw_text = str(text).strip()
    if not raw_text or raw_text[0] not in "{[":
        return None

    try:
        payload = json.loads(raw_text)
    except Exception:
        return None

    candidates = collect_layer_name_candidates_from_json(payload)
    return choose_best_layer_name(candidates)


def describe_layer_name(source):
    if source in (None, ""):
        return None

    try:
        desc = arcpy.Describe(source)
    except Exception:
        return None

    for attr in (
        "nameString",
        "name",
        "baseName",
        "aliasName",
        "datasetName",
        "catalogPath",
    ):
        candidate = normalize_layer_name_candidate(getattr(desc, attr, None))
        if candidate and not is_placeholder_layer_name(candidate):
            return candidate

    return None


def collect_object_metadata_candidates(
    source,
    candidate_urls=None,
    candidate_json=None,
    candidate_names=None,
):
    candidate_urls = candidate_urls if candidate_urls is not None else []
    candidate_json = candidate_json if candidate_json is not None else []
    candidate_names = candidate_names if candidate_names is not None else []

    if source in (None, ""):
        return candidate_urls, candidate_json, candidate_names

    try:
        attr_names = dir(source)
    except Exception:
        return candidate_urls, candidate_json, candidate_names

    for attr in attr_names:
        if attr.startswith("_"):
            continue

        attr_lower = attr.lower()
        if not any(
            token in attr_lower
            for token in ("name", "title", "label", "alias", "url", "json", "layer")
        ):
            continue

        try:
            value = getattr(source, attr)
        except Exception:
            continue

        if callable(value) or value in (None, ""):
            continue

        if isinstance(value, (dict, list, tuple, set)):
            try:
                text = json.dumps(value)
            except Exception:
                continue
        else:
            text = str(value).strip()

        if not text:
            continue

        if ("json" in attr_lower or text[:1] in "{[") and text[:1] in "{[":
            candidate_json.append(text)
        elif "url" in attr_lower or (
            text.startswith("http")
            and any(
                token in text for token in ("FeatureServer", "MapServer", "GPServer")
            )
        ):
            candidate_urls.append(text)
        elif any(token in attr_lower for token in ("name", "title", "label", "alias")):
            candidate_names.append(text)

    return candidate_urls, candidate_json, candidate_names


def resolve_layer_name(raw_value, raw_text, localized_fc, fallback_name=None):
    candidate_urls = []
    candidate_json = []
    candidate_names = []
    candidate_attr_names = []
    all_candidates = []

    raw_text_value = str(raw_text or "").strip()
    if raw_text_value:
        if raw_text_value.startswith("http"):
            candidate_urls.append(raw_text_value)
        candidate_json.append(raw_text_value)
        candidate_names.append(raw_text_value)

    for attr in ("url", "serviceURL", "serviceUrl", "layerUrl"):
        value = getattr(raw_value, attr, None)
        if value:
            candidate_urls.append(value)

    raw_json = getattr(raw_value, "JSON", None)
    if raw_json:
        candidate_json.append(raw_json)

    for attr in (
        "displayName",
        "title",
        "label",
        "name",
        "longName",
        "serviceLayerName",
        "sourceLayerName",
        "dataSourceName",
    ):
        value = getattr(raw_value, attr, None)
        if value not in (None, ""):
            candidate_attr_names.append(value)

    collect_object_metadata_candidates(
        raw_value,
        candidate_urls=candidate_urls,
        candidate_json=candidate_json,
        candidate_names=candidate_attr_names,
    )

    for source in candidate_json:
        candidate = extract_layer_name_from_json(source)
        if candidate:
            all_candidates.append(candidate)

    for url in candidate_urls:
        all_candidates.append(get_service_layer_name(url))

    for source in candidate_attr_names:
        all_candidates.append(source)

    for source in candidate_names:
        all_candidates.append(source)

    for source in (raw_value, raw_text, localized_fc):
        all_candidates.append(describe_layer_name(source))

    best_name = choose_best_layer_name(all_candidates, fallback_name=fallback_name)
    return output_fields.clean_display_name(best_name, fallback=fallback_name)


def fetch_url_to_local(url, output_fc):
    """Download a feature service layer URL to a local feature class."""
    if arcpy.Exists(output_fc):
        arcpy.management.Delete(output_fc)

    try:
        arcpy.management.CopyFeatures(url, output_fc)
        return output_fc
    except Exception:
        pass

    params = {"where": "1=1", "outFields": "*", "returnGeometry": "true", "f": "json"}

    try:
        token_info = arcpy.GetSigninToken()
    except Exception:
        token_info = None

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
    for field_info in data.get("fields", []):
        if field_info["type"] in skip_types:
            continue
        arcpy_type, length = field_type_map.get(field_info["type"], ("TEXT", 255))
        kwargs = {"field_length": length} if length else {}
        arcpy.management.AddField(output_fc, field_info["name"], arcpy_type, **kwargs)
        add_fields.append(field_info["name"])

    with arcpy.da.InsertCursor(output_fc, ["SHAPE@JSON"] + add_fields) as cur:
        for feature in data.get("features", []):
            geometry = json.dumps(feature.get("geometry") or {})
            attributes = [feature["attributes"].get(name) for name in add_fields]
            cur.insertRow([geometry] + attributes)

    return output_fc


def get_service_layer_name(url):
    """Query a FeatureServer sublayer URL to get its real name."""
    try:
        import json

        query_url = url.rstrip("/") + "?f=json"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        token_info = None
        try:
            token_info = arcpy.GetSigninToken()
        except Exception:
            pass
        if token_info and token_info.get("token"):
            query_url += "&token=" + token_info["token"]
        with urllib.request.urlopen(query_url, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("name") or data.get("displayField") or None
    except Exception:
        return None


def localize_layer_input(layer_value, output_fc, label, messages):
    """Convert remote layer URLs to local scratch feature classes for server use."""
    if layer_value and layer_value.startswith("http"):
        local_fc = fetch_url_to_local(layer_value, output_fc)
        messages.addMessage(f"{label} downloaded from URL to scratch.")
        return local_fc
    return layer_value


def copy_input_to_scratch(raw_value, raw_text, output_fc, label, messages):
    """Normalize web-tool feature inputs into scratch feature classes."""
    if arcpy.Exists(output_fc):
        arcpy.management.Delete(output_fc)

    source_value = raw_value if raw_value not in (None, "") else raw_text
    if source_value in (None, ""):
        return None

    try:
        arcpy.management.CopyFeatures(source_value, output_fc)
        messages.addMessage(f"{label} copied to scratch.")
        return output_fc
    except Exception:
        pass

    if raw_text and raw_text.startswith("http"):
        return localize_layer_input(raw_text, output_fc, label, messages)

    return raw_text


def get_multivalue_inputs(parameter):
    """Return multivalue GP inputs as (raw_value, raw_text) pairs."""
    values = getattr(parameter, "values", None)
    if values:
        pairs = []
        for value in values:
            text = getattr(value, "valueAsText", None)
            if not text:
                text = str(value)
            pairs.append((value, text))
        return pairs

    text = parameter.valueAsText
    if not text:
        return []

    return [(None, part) for part in text.split(";") if part]


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

        publish_mode = arcpy.Parameter(
            displayName="Existing Layer Update Mode",
            name="publish_mode",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        publish_mode.filter.list = ["Replace", "Append"]
        publish_mode.value = "Replace"

        stations_target = arcpy.Parameter(
            displayName="Existing Stations Layer URL or Path",
            name="stations_target",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        stations_target.value = "https://services.arcgis.com/xYjDUN35YwdCEcMm/arcgis/rest/services/Stationing_Output/FeatureServer/1"

        intersections_target = arcpy.Parameter(
            displayName="Existing Intersections Layer URL or Path",
            name="intersections_target",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        intersections_target.value = "https://services.arcgis.com/xYjDUN35YwdCEcMm/arcgis/rest/services/Stationing_Output/FeatureServer/0"

        overlaps_target = arcpy.Parameter(
            displayName="Existing Overlaps Layer URL or Path",
            name="overlaps_target",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        overlaps_target.value = "https://services.arcgis.com/xYjDUN35YwdCEcMm/arcgis/rest/services/Stationing_Output/FeatureServer/2"

        out_route = arcpy.Parameter(
            displayName="Output Route",
            name="out_route",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output",
        )

        out_stations = arcpy.Parameter(
            displayName="Output Station Points",
            name="out_stations",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output",
        )

        out_intersections = arcpy.Parameter(
            displayName="Output Intersections",
            name="out_intersections",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output",
        )

        out_overlaps = arcpy.Parameter(
            displayName="Output Overlaps",
            name="out_overlaps",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output",
        )

        out_segment = arcpy.Parameter(
            displayName="Output Segment",
            name="out_segment",
            datatype="DEFeatureClass",
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
        publish_mode.description = (
            "Optional update mode for existing preconfigured output layers."
        )
        stations_target.description = "Optional hosted feature layer URL or catalog path for labeled station outputs."
        intersections_target.description = "Optional hosted feature layer URL or catalog path for labeled intersection outputs."
        overlaps_target.description = "Optional hosted feature layer URL or catalog path for labeled overlap outputs."

        return [
            input_line,  # 0
            station_interval,  # 1
            start_measure,  # 2
            end_measure,  # 3
            tolerance,  # 4
            analysis_layers,  # 5
            publish_mode,  # 6
            stations_target,  # 7
            intersections_target,  # 8
            overlaps_target,  # 9
            out_route,  # 10
            out_stations,  # 11
            out_intersections,  # 12
            out_overlaps,  # 13
            out_segment,  # 14
        ]

    def updateMessages(self, parameters):
        input_line = parameters[0]
        station_interval = parameters[1]
        start_measure = parameters[2]
        end_measure = parameters[3]
        tolerance = parameters[4]
        analysis_layers = parameters[5]
        publish_mode = parameters[6]
        stations_target = parameters[7]
        intersections_target = parameters[8]
        overlaps_target = parameters[9]

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

        target_values = [
            stations_target.valueAsText,
            intersections_target.valueAsText,
            overlaps_target.valueAsText,
        ]
        if any(target_values) and not publish_mode.valueAsText:
            publish_mode.setErrorMessage(
                "Choose Replace or Append when target layers are provided."
            )

    def execute(self, parameters, messages):
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = arcpy.env.scratchGDB
        arcpy.env.scratchWorkspace = arcpy.env.scratchGDB

        scratch = arcpy.env.scratchGDB

        input_raw_text = str(parameters[0].valueAsText or "")

        input_line_fc = copy_input_to_scratch(
            parameters[0].value,
            parameters[0].valueAsText,
            scratch + "\\input_line_local",
            "Input feature",
            messages,
        )

        input_route_name = (
            resolve_layer_name(
                raw_value=parameters[0].value,
                raw_text=input_raw_text,
                localized_fc=input_line_fc,
                fallback_name="Input Route",
            )
            or "Input Route"
        )

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

        localized_layers = []
        original_layer_names = []
        for index, (raw_value, raw_text) in enumerate(
            get_multivalue_inputs(parameters[5])
        ):
            localized_fc = copy_input_to_scratch(
                raw_value,
                raw_text,
                scratch + f"\\analysis_layer_{index}_local",
                f"Analysis layer {index}",
                messages,
            )
            if localized_fc:
                localized_layers.append(localized_fc)
                original_name = (
                    resolve_layer_name(
                        raw_value=raw_value,
                        raw_text=raw_text,
                        localized_fc=localized_fc,
                        fallback_name=f"Analysis Layer {index + 1}",
                    )
                    or f"Analysis Layer {index + 1}"
                )
                original_layer_names.append(original_name)
                messages.addMessage(
                    f"Resolved analysis layer {index + 1} name: {original_name}"
                )
        analysis_layers = localized_layers

        publish_mode = parameters[6].valueAsText or "Replace"
        stations_target = parameters[7].valueAsText
        intersections_target = parameters[8].valueAsText
        overlaps_target = parameters[9].valueAsText

        messages.addMessage(f"Input feature: {input_line_fc}")
        messages.addMessage(f"Resolved input route name: {input_route_name}")
        messages.addMessage(f"Station interval: {station_interval}")
        messages.addMessage(f"Start measure: {start_measure}")
        messages.addMessage(f"End measure: {end_measure}")
        messages.addMessage(f"Tolerance: {tolerance}")
        messages.addMessage(f"Analysis layers: {analysis_layers}")
        messages.addMessage(f"Publish mode: {publish_mode}")
        messages.addMessage(f"Stations target: {stations_target}")
        messages.addMessage(f"Intersections target: {intersections_target}")
        messages.addMessage(f"Overlaps target: {overlaps_target}")
        messages.addMessage(f"Scratch GDB: {scratch}")

        outputs = run_stationing_workflow(
            input_line_fc=input_line_fc,
            station_interval=station_interval,
            tolerance=tolerance,
            start_measure=start_measure,
            end_measure=end_measure,
            analysis_layers=analysis_layers,
            layer_names=original_layer_names,
            input_route_name=input_route_name,
            publish_mode=publish_mode,
            station_target=stations_target,
            intersection_target=intersections_target,
            overlap_target=overlaps_target,
            messages=messages,
        )

        messages.addMessage(f"Output route: {outputs.route}")
        messages.addMessage(f"Output stations: {outputs.stations}")
        if getattr(outputs, "published_stations", None):
            messages.addMessage(
                f"Published stations layer updated: {outputs.published_stations}"
            )
        if getattr(outputs, "published_intersections", None):
            messages.addMessage(
                f"Published intersections layer updated: {outputs.published_intersections}"
            )
        if getattr(outputs, "published_overlaps", None):
            messages.addMessage(
                f"Published overlaps layer updated: {outputs.published_overlaps}"
            )

        arcpy.SetParameter(10, outputs.route)
        arcpy.SetParameter(11, outputs.stations)

        intersection_output = getattr(outputs, "intersection_output", None)
        if (
            not intersection_output
            and hasattr(outputs, "intersections")
            and outputs.intersections
        ):
            intersection_output = outputs.intersections[0]

        if intersection_output:
            messages.addMessage(
                f"Intersections created: {len(outputs.intersections)} layer(s)"
            )
            arcpy.SetParameter(12, intersection_output)
        else:
            empty_pts = scratch + "\\empty_intersections"
            if arcpy.Exists(empty_pts):
                arcpy.management.Delete(empty_pts)
            arcpy.management.CreateFeatureclass(scratch, "empty_intersections", "POINT")
            arcpy.SetParameter(12, empty_pts)

        overlap_output = getattr(outputs, "overlap_output", None)
        if not overlap_output and hasattr(outputs, "overlaps") and outputs.overlaps:
            overlap_output = outputs.overlaps[0]

        if overlap_output:
            messages.addMessage(f"Overlaps created: {len(outputs.overlaps)} layer(s)")
            arcpy.SetParameter(13, overlap_output)
        else:
            empty_lines = scratch + "\\empty_overlaps"
            if arcpy.Exists(empty_lines):
                arcpy.management.Delete(empty_lines)
            arcpy.management.CreateFeatureclass(scratch, "empty_overlaps", "POLYLINE")
            arcpy.SetParameter(13, empty_lines)

        if hasattr(outputs, "segment") and outputs.segment:
            messages.addMessage(f"Output segment: {outputs.segment}")
            arcpy.SetParameter(14, outputs.segment)
