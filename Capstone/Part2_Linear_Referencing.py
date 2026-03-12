import arcpy
import os
import shutil

# workspace settings
arcpy.env.overwriteOutput = True
arcpy.env.workspace = r"C:\Capstone\processing_data"
workspace = arcpy.env.workspace
aprx_path = r"C:\Capstone\Capstone_Project.aprx"

# projection settings
projection = arcpy.SpatialReference("NAD 1983 CSRS 3TM 114")
define_projection = arcpy.SpatialReference(3780)

# geodatabase settings
gdb_name = "Group2_Capstone"
gdb_path = os.path.join(workspace, gdb_name + ".gdb")

# Study Area Settings
study_area_section_name = "V4-1_SEC.shp"
study_area_field = "DESCRIPTOR"
study_area_ATS = "SEC-01 TWP-027 RGE-29 MER-4"
studyarea_path = os.path.join(gdb_path, "Study_Area")

# Pipeline features settings
pipeline_name = "Pipelines_GCS_NAD83.shp"
route_id_field = "Route_ID"
route_id_value = "PIPE_01"

# stations settings
station_interval = "100 Meters"

# user input data settings
analysis_layers = [
    "Subsurface_Lineaments__WebM.shp",
    "glac_landform_ln_ll.shp",
    "Base_Waterbody_Polygon.shp",
    "Target_A",
]
input_layers = [pipeline_name] + analysis_layers


def features(workspace):
    data = []
    for dirpath, dirname, filenames in arcpy.da.Walk(workspace):
        for f in filenames:
            data_path = os.path.join(dirpath, f)
            data.append(data_path)
    return data


data_shp = features(workspace)

print("Listing all data and their paths...")
for data in data_shp:
    print(data)
    print(arcpy.GetMessages())
    print("")

# Delete existing gdb
wkspace = arcpy.ListWorkspaces("", "FileGDB")
for gdb in wkspace:
    if arcpy.Exists(gdb):
        arcpy.management.Delete(gdb)
        print("Deleting existing gdb...")
        print(arcpy.GetMessages())
        print("")

# Create new gdb
arcpy.management.CreateFileGDB(workspace, gdb_name + ".gdb")
print(arcpy.GetMessages())
print("")

# identify study area
study_area_section = next(
    p for p in data_shp if os.path.basename(p).lower() == study_area_section_name.lower()
)

section_layer = arcpy.MakeFeatureLayer_management(study_area_section, "sections_layer")

delimfield = arcpy.AddFieldDelimiters(study_area_section, study_area_field)
sql_query = f"{delimfield} = '{study_area_ATS}'"
arcpy.SelectLayerByAttribute_management(section_layer, "NEW_SELECTION", sql_query)

arcpy.management.Project("sections_layer", studyarea_path, projection)

# clip needed data to study area
for data_list in input_layers:
    dataList_path = next(
        p for p in data_shp if os.path.basename(p).lower() == data_list.lower()
    )

    base = os.path.splitext(data_list)[0]
    valid_name = arcpy.ValidateTableName(base, gdb_path)

    desc = arcpy.Describe(dataList_path)
    print("Data Type: ", desc.dataType)
    print("Spatial Reference: ", desc.spatialReference.name)

    projected_data = os.path.join(gdb_path, valid_name + "_prj")
    clipped_data = os.path.join(gdb_path, valid_name + "_clip")
    contour_output = os.path.join(gdb_path, valid_name + "_contours")

    if desc.spatialReference.name == "Unknown":
        arcpy.DefineProjection_management(dataList_path, define_projection)
        print(arcpy.GetMessages())
        print("")

    if desc.dataType in ["FeatureClass", "ShapeFile"]:
        arcpy.management.Project(dataList_path, projected_data, projection)
        arcpy.analysis.Clip(projected_data, studyarea_path, clipped_data)

    elif desc.dataType == "RasterDataset":
        arcpy.management.ProjectRaster(
            dataList_path, projected_data, projection, "BILINEAR"
        )

    elif desc.dataType == "Tin":
        interval = 5
        print("Generating Contours...")
        arcpy.ddd.SurfaceContour(dataList_path, contour_output, interval)
        arcpy.management.Project(contour_output, projected_data, projection)
        arcpy.analysis.Clip(projected_data, studyarea_path, clipped_data)

    print(arcpy.GetMessages())
    print("")

    print("Deleting...")
    arcpy.management.Delete(projected_data)
    print(arcpy.GetMessages())
    print("")

    print(f"Successfully projected and clipped {data_list} = {clipped_data}")
    print(arcpy.GetMessages())
    print("")

# create route
pipeline_base = os.path.splitext(pipeline_name)[0]
pipeline_fc = os.path.join(gdb_path, f"{pipeline_base}_clip")

if route_id_field not in [f.name for f in arcpy.ListFields(pipeline_fc)]:
    arcpy.management.AddField(pipeline_fc, route_id_field, "TEXT", field_length=50)

arcpy.management.CalculateField(
    pipeline_fc, route_id_field, f"'{route_id_value}'", "PYTHON3"
)

pipeline_diss = os.path.join(gdb_path, "Pipeline_Dissolve")
arcpy.management.Dissolve(pipeline_fc, pipeline_diss, route_id_field)

routes_fc = os.path.join(gdb_path, "Pipeline_Route")
arcpy.lr.CreateRoutes(pipeline_diss, route_id_field, routes_fc, "LENGTH")

calculate_field = r"""
def chain(m):
    m = int(round(float(m)))
    km = m // 1000
    remainder = m % 1000
    return f"{km}+{remainder:03d}"
"""

# Generate station points
station_points = os.path.join(gdb_path, "Station_Points")
arcpy.management.GeneratePointsAlongLines(
    routes_fc,
    station_points,
    "DISTANCE",
    Distance=station_interval,
    Include_End_Points="END_POINTS",
)


def locate_features(
    in_features,
    in_routes,
    route_id_field,
    out_table,
    out_event_properties,
    radius_or_tolerance="5 Meters",
    distance_field="DISTANCE",
):
    arcpy.lr.LocateFeaturesAlongRoutes(
        in_features=in_features,
        in_routes=in_routes,
        route_id_field=route_id_field,
        radius_or_tolerance=radius_or_tolerance,
        out_table=out_table,
        out_event_properties=out_event_properties,
        distance_field=distance_field,
    )
    return out_table


# Station events
station_table = os.path.join(gdb_path, "Station_Events")
station_table = locate_features(
    in_features=station_points,
    in_routes=routes_fc,
    route_id_field=route_id_field,
    out_table=station_table,
    out_event_properties=f"{route_id_field} POINT MEAS",
)

if "Chainage" not in [f.name for f in arcpy.ListFields(station_table)]:
    arcpy.management.AddField(station_table, "Chainage", "TEXT", field_length=20)

arcpy.management.CalculateField(
    station_table, "Chainage", "chain(!MEAS!)", "PYTHON3", calculate_field
)

station_lyr = "Station_Events_lyr"
arcpy.lr.MakeRouteEventLayer(
    in_routes=routes_fc,
    route_id_field=route_id_field,
    in_table=station_table,
    in_event_properties=f"{route_id_field} POINT MEAS",
    out_layer=station_lyr,
)

station_fc = os.path.join(gdb_path, "Station_Events_fc")
arcpy.management.CopyFeatures(station_lyr, station_fc)

# exclude route-related layers
arcpy.env.workspace = gdb_path
fc_gdb = arcpy.ListFeatureClasses()

exclude_fc = {
    "pipelines_gcs_nad83_clip",
    "pipeline_dissolve",
    "pipeline_route",
    "study_area",
    "station_points",
    "station_events_fc",
}

include_fc = [fc for fc in fc_gdb if fc.lower() not in exclude_fc]

for fc in include_fc:
    print(fc)

# Intersections / overlaps
intersect_points = []
overlap = []

for f in include_fc:
    fc_path = os.path.join(gdb_path, f)
    desc = arcpy.Describe(fc_path)
    geom = desc.shapeType
    base_name = os.path.basename(f)

    out_point = os.path.join(
        gdb_path, arcpy.ValidateTableName(base_name + "_point", gdb_path)
    )
    arcpy.analysis.Intersect([pipeline_diss, fc_path], out_point, output_type="POINT")
    intersect_points.append(out_point)
    print(f"Point Intersect created: {out_point}")

    if geom == "Polygon":
        out_overlap = os.path.join(
            gdb_path, arcpy.ValidateTableName(base_name + "_overlap", gdb_path)
        )
        arcpy.analysis.Intersect(
            [pipeline_diss, fc_path], out_overlap, "", "", output_type="LINE"
        )
        overlap.append(out_overlap)
        print(f"Overlap Created: {out_overlap}")

# Locate features along route
event_tables_points = []
event_tables_lines = []

for point_fc in intersect_points:
    out_table = os.path.join(
        gdb_path,
        arcpy.ValidateTableName(os.path.basename(point_fc) + "_event", gdb_path),
    )

    out_table = locate_features(
        in_features=point_fc,
        in_routes=routes_fc,
        route_id_field=route_id_field,
        out_table=out_table,
        out_event_properties=f"{route_id_field} POINT MEAS",
    )
    event_tables_points.append(out_table)
    print("Created event table: ", out_table)
    print(arcpy.GetMessages())

for overlaps in overlap:
    out_table_overlap = os.path.join(
        gdb_path,
        arcpy.ValidateTableName(os.path.basename(overlaps) + "_events", gdb_path),
    )

    out_table_overlap = locate_features(
        in_features=overlaps,
        in_routes=routes_fc,
        route_id_field=route_id_field,
        out_table=out_table_overlap,
        out_event_properties=f"{route_id_field} LINE FMEAS TMEAS",
    )
    event_tables_lines.append(out_table_overlap)
    print("Overlap Event Table: ", out_table_overlap)
    print(arcpy.GetMessages())

# Chainage for point events
for table in event_tables_points:
    if "Chainage" not in [f.name for f in arcpy.ListFields(table)]:
        arcpy.management.AddField(table, "Chainage", "TEXT", field_length=20)

    arcpy.management.CalculateField(
        table, "Chainage", "chain(!MEAS!)", "PYTHON3", calculate_field
    )
    print("Chainage added (points):", table)

# Chainage for line events
for table_overlap in event_tables_lines:
    existing = [f.name for f in arcpy.ListFields(table_overlap)]

    if "FromCh" not in existing:
        arcpy.management.AddField(table_overlap, "FromCh", "TEXT", field_length=20)
    if "ToCh" not in existing:
        arcpy.management.AddField(table_overlap, "ToCh", "TEXT", field_length=20)
    if "ChainageRange" not in existing:
        arcpy.management.AddField(table_overlap, "ChainageRange", "TEXT", field_length=30)

    arcpy.management.CalculateField(
        table_overlap, "FromCh", "chain(!FMEAS!)", "PYTHON3", calculate_field
    )
    arcpy.management.CalculateField(
        table_overlap, "ToCh", "chain(!TMEAS!)", "PYTHON3", calculate_field
    )
    arcpy.management.CalculateField(
        table_overlap, "ChainageRange", "!FromCh! + ' - ' + !ToCh!", "PYTHON3"
    )
    print("Chainage range added (lines):", table_overlap)

# Create point event layers
for tbl in event_tables_points:
    lyr_name = os.path.basename(tbl) + "_lyr"
    arcpy.lr.MakeRouteEventLayer(
        in_routes=routes_fc,
        route_id_field=route_id_field,
        in_table=tbl,
        in_event_properties=f"{route_id_field} POINT MEAS",
        out_layer=lyr_name,
    )
    out_fc = os.path.join(gdb_path, arcpy.ValidateTableName(lyr_name + "_fc", gdb_path))
    arcpy.management.CopyFeatures(lyr_name, out_fc)
    print("Made POINT event layer:", lyr_name)

# Create line event layers
for tbl in event_tables_lines:
    lyr_name = os.path.basename(tbl) + "_lyr"
    arcpy.lr.MakeRouteEventLayer(
        in_routes=routes_fc,
        route_id_field=route_id_field,
        in_table=tbl,
        in_event_properties=f"{route_id_field} LINE FMEAS TMEAS",
        out_layer=lyr_name,
    )
    out_fc = os.path.join(gdb_path, arcpy.ValidateTableName(lyr_name + "_fc", gdb_path))
    arcpy.management.CopyFeatures(lyr_name, out_fc)
    print("Made LINE event layer:", lyr_name)

# APRX setup
template_aprx = r"C:\Capstone\Alignmentsheet\Alignmentsheet.aprx"
output_aprx = aprx_path

if os.path.exists(output_aprx):
    os.remove(output_aprx)

shutil.copy(template_aprx, output_aprx)

aprx = arcpy.mp.ArcGISProject(output_aprx)

map_name = "Capstone Map"
existing_maps = aprx.listMaps(map_name)
if existing_maps:
    m = existing_maps[0]
else:
    m = aprx.createMap(map_name)

layers_to_add = [
    os.path.join(gdb_path, "Study_Area"),
    os.path.join(gdb_path, "Pipeline_Route"),
    os.path.join(gdb_path, "Station_Events_fc"),
    os.path.join(gdb_path, "Base_Waterbody_Polygon_clip"),
    os.path.join(gdb_path, "Base_Waterbody_Polygon_clip_point_event_lyr_fc"),
    os.path.join(gdb_path, "glac_landform_ln_ll_clip"),
    os.path.join(gdb_path, "glac_landform_ln_ll_clip_point_event_lyr_fc"),
    os.path.join(gdb_path, "Subsurface_Lineaments__WebM_clip"),
    os.path.join(gdb_path, "Subsurface_Lineaments__WebM_clip_point_event_lyr_fc"),
]

for lyr in layers_to_add:
    if arcpy.Exists(lyr):
        m.addDataFromPath(lyr)
        print(f"Added: {lyr}")
    else:
        print(f"Missing: {lyr}")

layouts = aprx.listLayouts("Alignment_Sheet")
if layouts:
    layout = layouts[0]
    mapframes = layout.listElements("MAPFRAME_ELEMENT", "Main Map Frame")
    if mapframes:
        mf = mapframes[0]
        mf.map = m

        route_layers = m.listLayers("Pipeline_Route")
        if route_layers:
            mf.camera.setExtent(mf.getLayerExtent(route_layers[0], False, True))

aprx.save()
del aprx

print(f"Project saved successfully: {output_aprx}")