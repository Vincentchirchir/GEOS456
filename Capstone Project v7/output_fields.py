import arcpy
from datetime import datetime
import re


def get_field_names(dataset):
    return [field.name for field in arcpy.ListFields(dataset)]


def add_field_if_missing(dataset, field_name, field_type, field_length=None):
    if field_name in get_field_names(dataset):
        return

    kwargs = {}
    if field_type.upper() == "TEXT" and field_length:
        kwargs["field_length"] = field_length

    arcpy.management.AddField(dataset, field_name, field_type, **kwargs)


def get_first_value(dataset, field_name, default=None):
    if field_name not in get_field_names(dataset):
        return default

    with arcpy.da.SearchCursor(dataset, [field_name]) as cursor:
        for row in cursor:
            if row[0] not in (None, ""):
                return row[0]

    return default


def build_run_id(run_time=None):
    run_time = run_time or datetime.now()
    return run_time.strftime("RUN_%Y%m%d_%H%M%S")


def map_shape_type(shape_type):
    return {
        "Point": "point",
        "Polyline": "line",
        "Polygon": "polygon",
    }.get(shape_type, str(shape_type).lower() if shape_type else None)


def is_meaningful_display_name(name):
    text = str(name or "").strip()
    if not text or text.startswith("<"):
        return False

    lowered = text.casefold()
    if lowered in {
        "featureset",
        "recordset",
        "layer",
        "input feature",
        "input route",
        "analysis layer",
    }:
        return False

    if re.fullmatch(r"[a-z]", lowered):
        return False

    if re.fullmatch(r"\d+", lowered):
        return False

    if re.fullmatch(r"layer[ _-]*\d+", lowered):
        return False

    if re.fullmatch(r"analysis[ _-]*layer[ _-]*\d+([ _-]*local)?", lowered):
        return False

    if re.fullmatch(r"input[ _-]*line([ _-]*local)?", lowered):
        return False

    if re.fullmatch(r"analysis[ _-]*layer[ _-]*\d+[ _-]*local", lowered):
        return False

    if re.fullmatch(r"publish[ _-]*target[ _-]*[0-9a-f]+", lowered):
        return False

    if lowered in {"empty_intersections", "empty_overlaps"}:
        return False

    return True


def normalize_display_name(name):
    text = str(name or "").strip()
    if not text:
        return None

    # Strip common ArcGIS service-style layer prefixes such as
    # L2Pipeline_StudyArea -> Pipeline_StudyArea
    prefix_match = re.match(r"^L\d+(?=[A-Z_ -])", text)
    if prefix_match:
        text = text[prefix_match.end() :].lstrip("_- ")

    return text or None


def clean_display_name(name, fallback=None):
    primary = normalize_display_name(name)
    if is_meaningful_display_name(primary):
        return primary

    secondary = normalize_display_name(fallback)
    if is_meaningful_display_name(secondary):
        return secondary

    return None
