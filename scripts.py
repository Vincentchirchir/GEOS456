import arcpy
import os  # python library for joining folders, getting filenames

projection = arcpy.SpatialReference("NAD 1983 CSRS 3TM 114")

arcpy.env.workspace = r"C:\Capstone\processing_data"  # Data path
workspace = arcpy.env.workspace
arcpy.env.overwriteOutput = True  # can overwrite output datasets that already exist


# function to list all data
def features(workspace):
    data = []  # create a list to store data and path
    for dirpath, dirname, filenames in arcpy.da.Walk(workspace):
        for f in filenames:
            data_path = os.path.join(dirpath, f)  # for each file in f, create path
            data.append(data_path)  # Store the data path in data
    return data  # return the full list of data paths found


data_shp = features(workspace)  # calls the feature function to get all data and its path stored earlier

# print all data and path
##for data in data_shp:
##    print(data)

# Delete any gdb found and create a new one
wkspace = arcpy.ListWorkspaces("", "FileGDB")  # LIST ALL GDB IN THE WORKSPACE
for gdb in wkspace:
    if arcpy.Exists(gdb):  # checks if there is any existing gdb
        arcpy.management.Delete(gdb)  # if any gdb is found, it deletes
        print("Deleting existing gdb...")
        print(arcpy.GetMessages())

# Creating a new gdb
gdb_name = "Group2_Capstone"  # name of new gdb
arcpy.management.CreateFileGDB(workspace, gdb_name + ".gdb")  # creates the gdb in workspace folder
gdb_path = os.path.join(workspace, gdb_name + ".gdb")  # saving the full path of gdb
print(arcpy.GetMessages())
print("")

# identifying studying area
study_area_section = next( p for p in data_shp if os.path.basename(p).lower() == "V4-1_SEC.shp".lower())  # Searches through the data_shp to find section

# Create a temporary feature layer  of all section, before identifying the section we want
section_layer = arcpy.MakeFeatureLayer_management(study_area_section, "sections_layer")

# Create SQL function to select from the temporary layer
delimfield = arcpy.AddFieldDelimiters(study_area_section, "DESCRIPTOR")

# Select features from sections_layer whose DESCRIPTOR equals that exact text
arcpy.SelectLayerByAttribute_management(section_layer, "NEW_SELECTION", delimfield + "= 'SEC-01 TWP-027 RGE-29 MER-4'")

# create a study area and store in gdb
studyarea_path = os.path.join(gdb_path, "Study_Area")
arcpy.management.Project("sections_layer", studyarea_path, projection)

# clip needed data to study area
data = [
    "Pipelines_GCS_NAD83.shp",
    "Subsurface_Lineaments__WebM.shp",
    "glac_landform_ln_ll.shp",
    # "V4-1_LSD.shp",
    "Base_Waterbody_Polygon.shp",
]

for data_list in data:
    dataList_path = next( p for p in data_shp if os.path.basename(p).lower() == data_list.lower())  # Finds the full path of that shapefile in your workspace (case-insensitive).
    base = os.path.splitext(data_list)[0]  # Removes .shp to get the base name (example: "Airdrie_Roads")
    valid_name = arcpy.ValidateTableName(base, gdb_path)  # validating names before building output

    # set names
    projected_data = os.path.join(gdb_path, valid_name + "_prj")  # sets names for projected data. projected data will end with _prj
    clipped_data = os.path.join(gdb_path, valid_name + "_clip")

    # project data
    arcpy.management.Project(dataList_path, projected_data, projection)

    # clip data
    arcpy.analysis.Clip(projected_data, studyarea_path, clipped_data)

    # Delete internediate projected data
    arcpy.management.Delete(projected_data)

    print(f"Successfully projected and clipped {data_list} = {clipped_data}")

# creating a route [linear referencing]
pipeline_fc = os.path.join(gdb_path, "Pipelines_GCS_NAD83_clip")  # path for pipeline

# create a new field for route ID if the data do not have
route_id_field = "Route_ID"
if route_id_field not in [f.name for f in arcpy.ListFields(pipeline_fc)]:  # check if the field RouteID exists in pipeline data
    arcpy.management.AddField(pipeline_fc, route_id_field, "TEXT", field_length=50 )  # if not, add a new field

# calculate the new field
arcpy.management.CalculateField(pipeline_fc, route_id_field, "'PIPE_01'", "PYTHON3")  # CALCULATES A CONSTATNT VALUE FROM PIPE_01 for every pipe

# Dissolve pipeline to one feature or one per routeID
pipeline_diss = os.path.join(gdb_path, "Pipeline_Dissolve")
arcpy.management.Dissolve(pipeline_fc, pipeline_diss, route_id_field)


# CREATING M ENABLED ROUTE FEATURE CLASS
routes_fc = os.path.join(gdb_path, "Pipeline_Route")  # path for output route
arcpy.lr.CreateRoutes(
    pipeline_diss, route_id_field, routes_fc, "LENGTH"
)  # LENGTH tells ArcGIS to create measures from 0 to total length coz we dont have starting and ending distance

arcpy.env.workspace = gdb_path
fc_gdb = arcpy.ListFeatureClasses()
exclude_fc = {
    "pipelines_gcs_nad83_clip",  # the clipped pipe
    "pipeline_dissolve",  # dissolve output
    "pipeline_route",  # route output
}
include_fc = [fc for fc in fc_gdb if fc.lower() not in exclude_fc]
for fc in include_fc:
    print(fc)

intersect_points = []
overlap = []

for f in include_fc:
    desc = arcpy.Describe(f)
    geom = desc.shapeType

    base_name = os.path.basename(f)

    out_point = os.path.join(
        gdb_path, arcpy.ValidateTableName(base_name + "_point", gdb_path)
    )
    arcpy.analysis.Intersect([pipeline_diss, f], out_point, output_type="POINT")
    intersect_points.append(out_point)
    print(f"Point Intersect created: {out_point}")

    if geom == "Polygon":
        out_overlap = os.path.join(
            gdb_path, arcpy.ValidateTableName(base_name + "_overlap", gdb_path)
        )
        arcpy.analysis.Intersect([pipeline_diss, f], out_overlap, "", "", output_type="LINE")
        overlap.append(out_overlap)
        print(f"Overlap Created: {out_overlap}")

# Locating features along the route. It produces table
event_tables_points = []
event_tables_lines = []

# locate points intersecting pipeline
for point_fc in intersect_points:
    out_table = os.path.join(
        gdb_path,
        arcpy.ValidateTableName(os.path.basename(point_fc) + "_event", gdb_path),
    )

    arcpy.lr.LocateFeaturesAlongRoutes(
        in_features=point_fc,
        in_routes=routes_fc,
        route_id_field=route_id_field,
        radius_or_tolerance="5 Meters",
        out_table=out_table,
        out_event_properties=f"{route_id_field} POINT MEAS",
        route_locations="",
        distance_field="DISTANCE",
    )
    event_tables_points.append(out_table)
    print("Created event table: ", out_table)
    print(arcpy.GetMessages())

    # locating overlps
    for overlaps in overlap:
        out_table_overlap = os.path.join(
            gdb_path,
            arcpy.ValidateTableName(os.path.basename(overlaps) + "_events", gdb_path),
        )

        arcpy.lr.LocateFeaturesAlongRoutes(
            in_features=overlaps,
            in_routes=routes_fc,
            route_id_field=route_id_field,
            radius_or_tolerance="5 Meters",
            out_table=out_table_overlap,
            out_event_properties=f"{route_id_field} LINE From To",
            distance_field="DISTANCE",
        )
        event_tables_lines.append(out_table_overlap)
        print("Overlap Event Table: ", out_table_overlap)
        print(arcpy.GetMessages())

# Chainage
calculate_field = r"""
def chain(m):
    m=int(round(m))
    km=m//1000
    remainder=m % 1000
    return f"{km} + {rem:03d}"

"""

# chainage for point
for table in event_tables_points:
    if "Chainage" not in [f.name for f in arcpy.ListFields(table)]:
        arcpy.management.Addfield(table, "Chainage", "TEXT", field_length=20)

    arcpy.management.CalculateField(
        table, "Chainage", "ch(!MEAS!)", "PYTHON3", calculate_field
    )
    print("Chainage added (points):", table)

# For LINE event tables (overlaps)
for table_overlap in event_tables_lines:
    existing = [f.name for f in arcpy.ListFields(table_overlap)]

    if "FromCh" not in existing:
        arcpy.management.AddField(table_overlap, "FromCh", "TEXT", field_length=20)
    if "ToCh" not in existing:
        arcpy.management.AddField(table_overlap, "ToCh", "TEXT", field_length=20)
    if "ChainageRange" not in existing:
        arcpy.management.AddField(
            table_overlap, "ChainageRange", "TEXT", field_length=35
        )

    arcpy.management.CalculateField(
        table_overlap, "FromCh", "ch(!FromM!)", "PYTHON3", calculate_field
    )
    arcpy.management.CalculateField(
        table_overlap, "ToCh", "ch(!ToM!)", "PYTHON3", calculate_field
    )
    arcpy.management.CalculateField(
        table_overlap, "ChainageRange", "!FromCh! + ' – ' + !ToCh!", "PYTHON3"
    )
    print("Chainage range added (lines):", table_overlap)

# Create Route Event Layers for display
# POINT event layers
for tbl in event_tables_points:
    lyr_name = os.path.basename(tbl) + "_lyr"
    arcpy.lr.MakeRouteEventLayer(
        in_routes=routes_fc,
        route_id_field=route_id_field,
        in_table=tbl,
        in_event_properties=f"{route_id_field} POINT MEAS",
        out_layer=lyr_name,
    )
    print("Made POINT event layer:", lyr_name)

# LINE event layers
for tbl in event_tables_lines:
    lyr_name = os.path.basename(tbl) + "_lyr"
    arcpy.lr.MakeRouteEventLayer(
        in_routes=routes_fc,
        route_id_field=route_id_field,
        in_table=tbl,
        in_event_properties=f"{route_id_field} LINE FromM ToM",
        out_layer=lyr_name,
    )
    print("Made LINE event layer:", lyr_name)
