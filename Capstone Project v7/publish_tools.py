import arcpy
from types import SimpleNamespace
from uuid import uuid4

from output_fields import get_field_names


def normalize_target_reference(value):
    if value in (None, ""):
        return None

    text = str(value).strip()
    if not text:
        return None

    return text.strip('"').strip("'")


def make_temp_layer_name(prefix):
    return f"{prefix}_{uuid4().hex[:8]}"


def validate_target_schema(target, expected_shape_type, required_fields):
    desc = arcpy.Describe(target)
    target_shape = getattr(desc, "shapeType", None)
    if target_shape != expected_shape_type:
        raise RuntimeError(
            f"Target shape type is {target_shape}, expected {expected_shape_type}."
        )

    target_fields = get_field_names(target)
    missing_fields = [field for field in required_fields if field not in target_fields]
    if missing_fields:
        raise RuntimeError(
            "Target layer is missing required fields: " + ", ".join(missing_fields)
        )


def clear_target_features(target):
    layer_name = make_temp_layer_name("publish_target")
    arcpy.management.MakeFeatureLayer(target, layer_name)
    try:
        arcpy.management.DeleteFeatures(layer_name)
    finally:
        arcpy.management.Delete(layer_name)


def append_source_to_target(source_fc, target, mode):
    if mode == "Replace":
        clear_target_features(target)

    arcpy.management.Append(source_fc, target, "NO_TEST")


def publish_result_layer(
    source_fc,
    target,
    mode,
    expected_shape_type,
    required_fields,
    label,
    messages,
):
    target = normalize_target_reference(target)
    if not target:
        return None

    if not source_fc or not arcpy.Exists(source_fc):
        messages.addWarningMessage(
            f"No {label.lower()} output was available to publish."
        )
        return None

    validate_target_schema(target, expected_shape_type, required_fields)
    append_source_to_target(source_fc, target, mode)

    count = int(arcpy.management.GetCount(target)[0])
    messages.addMessage(
        f"{label} published to target layer. Current target count: {count}"
    )
    return target


def publish_result_layers(
    outputs,
    publish_mode,
    station_target=None,
    intersection_target=None,
    overlap_target=None,
    route_id_field="ROUTE_ID",
    messages=None,
):
    messages = messages or arcpy

    published_station_target = publish_result_layer(
        source_fc=getattr(outputs, "stations", None),
        target=station_target,
        mode=publish_mode,
        expected_shape_type="Point",
        required_fields=[
            route_id_field,
            "Chainage",
            "Label_Text",
            "Run_ID",
            "Result_Type",
        ],
        label="Stations",
        messages=messages,
    )

    published_intersection_target = publish_result_layer(
        source_fc=getattr(outputs, "intersection_output", None),
        target=intersection_target,
        mode=publish_mode,
        expected_shape_type="Point",
        required_fields=[
            route_id_field,
            "Source_Name",
            "Chainage",
            "Label_Text",
            "Run_ID",
            "Result_Type",
        ],
        label="Intersections",
        messages=messages,
    )

    published_overlap_target = publish_result_layer(
        source_fc=getattr(outputs, "overlap_output", None),
        target=overlap_target,
        mode=publish_mode,
        expected_shape_type="Polyline",
        required_fields=[
            route_id_field,
            "Source_Name",
            "Range_Text",
            "Label_Text",
            "Length_m",
            "Run_ID",
            "Result_Type",
        ],
        label="Overlaps",
        messages=messages,
    )

    return SimpleNamespace(
        stations=published_station_target,
        intersections=published_intersection_target,
        overlaps=published_overlap_target,
    )
