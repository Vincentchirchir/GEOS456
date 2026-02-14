#---------------------------------------------------------------------------------------
# Name:        Assignment 02
# Purpose:     Automate conversion, projection, merging, clipping, and geodatabase dataset creation of Base and DLS features
#
# Author:      vince
#
# Created:     03/02/2026
# Copyright:   (c) vince 2026
# Licence:     <your licence>
#---------------------------------------------------------------------------------------
import arcpy
import os

coordinates = arcpy.SpatialReference("NAD 1983 UTM ZONE 12N")
define_coord = arcpy.SpatialReference("NAD 1983 10TM AEP Resource")
arcpy.env.overwriteOutput = True

#setting workspace
arcpy.env.workspace = r"C:\GEOS456\Assign02"
workspace = arcpy.env.workspace

def messages():
    print(arcpy.GetMessage(0)) #print only the FIRST geoprocessing message
    count = arcpy.GetMessageCount()#counts ALL geoprocessing messages for any tool
    print(arcpy.GetMessage(count-1))#indexes the LAST message from a tool
    print()

#Create a list of all the datasets prior to importing into the geodatabase
print("1.Below are the shapefile features before exporting to gdb:")

for dirpath, dirname, filenames in arcpy.da.Walk(workspace, datatype="FeatureClass"):
    for shapefiles in filenames:
        shp_path = os.path.join(dirpath, shapefiles)
        print(f"  - {shapefiles}")
        print("")

        desc = arcpy.Describe(shp_path)
        print("Spatial Reference: " + desc.spatialReference.name)
        print("Geometry: " + desc.shapeType)
        print("Data Type: " + desc.dataType)
        print(arcpy.GetMessages())
        print("")

#Check if gdb exists
gdb_path = r"C:\GEOS456\Assign02\Assignment02.gdb"
if arcpy.Exists(gdb_path):
    arcpy.management.Delete(gdb_path)
    print("Deleting Geodatabase...")
    print(arcpy.GetMessages())
    print("")
else:
    print("No Existing Geodatabase")
    print("")
messages()

#Creating gdb
gdb_name = "Assignment02"
arcpy.management.CreateFileGDB(workspace, gdb_name + ".gdb")
print("Creating Geodatabse...")
print(arcpy.GetMessages())
print("")

#Creating Datasets inside gdb
dataset_path = gdb_path
dataset_name = ["Base_Features", "DLS"]
for datasets in dataset_name:
    arcpy.management.CreateFeatureDataset(dataset_path, datasets, coordinates)
    print(f" Creating {datasets} Dataset...")
    print(arcpy.GetMessages())
    print("")

#Identifying study area
workspace = arcpy.env.workspace
in_layer = "82I_TWP"
relationship = "INTERSECT"
selecting_fc = "GSP_Pointe"
in_layer_path = None
selecting_fc_path = None
for dp, dn, fns in arcpy.da.Walk(workspace, datatype="FeatureClass"):
    for f in fns:
        if os.path.splitext(f)[0].lower() == in_layer.lower():
            in_layer_path = os.path.join(dp, f)
        if os.path.splitext(f)[0].lower() == selecting_fc.lower():
            selecting_fc_path = os.path.join(dp, f)

# make layers and select on layers
in_layer_lyr = arcpy.management.MakeFeatureLayer(in_layer_path, "in_layer_lyr")
selecting_fc_lyr = arcpy.management.MakeFeatureLayer(selecting_fc_path, "selecting_fc_lyr")
study_area = arcpy.management.SelectLayerByLocation(in_layer_lyr, relationship, selecting_fc_lyr)
print(arcpy.GetMessages())
print("")

#Export study area to geodatabase
in_feature = study_area
out = gdb_path
out_name = "Study_Area"
studyArea_path = os.path.join(out, out_name)

# copy selected features then project
temp_study = os.path.join(out, "Study_Area_temp")
arcpy.management.CopyFeatures(in_feature, temp_study)
arcpy.management.Project(temp_study, studyArea_path, coordinates)
arcpy.management.Delete(temp_study)
print("Exporting study area...")
print(arcpy.GetMessages())
print("")

#Exporting GSP Point to gdb
in_feature = selecting_fc_path
out_feature = os.path.join(gdb_path, os.path.splitext(os.path.basename(in_feature))[0])
arcpy.management.CopyFeatures(in_feature, out_feature)
print("Exporting GSP Point...")
print(arcpy.GetMessages())
print("")

#making feature layers
base_workspace = r"C:\GEOS456\Assign02\Base"
for dirpath, dirnames, filenames in arcpy.da.Walk(base_workspace, datatype="FeatureClass"):
    for file in filenames:
        shp_path = os.path.join(dirpath, file)
        if file == "BF_CONTOUR_ARC.shp":
            contour_layer = arcpy.MakeFeatureLayer_management(shp_path, "Contours")
        elif file == "BF_CUT_TRAIL_ARC.shp":
            cut_trail_layer = arcpy.MakeFeatureLayer_management(shp_path, "Cut_Trails")
        elif file == "BF_PIPELINE_ARC.shp":
            pipeline_layer = arcpy.MakeFeatureLayer_management(shp_path, "Pipelines")
        elif file == "BF_POWERLINE_ARC.shp":
            powerline_layer = arcpy.MakeFeatureLayer_management(shp_path, "Powerlines")
        elif file == "BF_ROAD_ARC.shp":
            roads_layer = arcpy.MakeFeatureLayer_management(shp_path, "Roads")
print("Making layers...")
messages()

#merging
layer_list = ["Contours", "Cut_Trails", "Pipelines", "Powerlines", "Roads"]
layer_dict = {
    "Contours": contour_layer,
    "Cut_Trails": cut_trail_layer,
    "Pipelines": pipeline_layer,
    "Powerlines": powerline_layer,
    "Roads": roads_layer
}
for layers in layer_list:
    output = os.path.join(gdb_path, f"{layers}_Merged")
    arcpy.management.Merge([layer_dict[layers]], output)
    arcpy.management.DefineProjection(output, define_coord)
    out_dataset = os.path.join(gdb_path, f"{layers}_Projected")
    arcpy.management.Project(output, out_dataset, coordinates)
    out_clip = os.path.join(gdb_path, layers)
    arcpy.analysis.Clip(out_dataset, studyArea_path, out_clip)
    for features in [output, out_dataset]:
        arcpy.management.Delete(features)
print("Merging...")
messages()

#DLS
arcpy.env.workspace = r"C:\GEOS456\Assign02\DLS"
DLS_fc = arcpy.ListFeatureClasses()

for fc in DLS_fc:
    in_fc = os.path.join(arcpy.env.workspace, fc)
    base_name = os.path.splitext(fc)[0]
    out_DLS = os.path.join(gdb_path, arcpy.ValidateTableName(base_name + "_temp", gdb_path))
    arcpy.management.CopyFeatures(in_fc, out_DLS)
    out_DLS_final = os.path.join(gdb_path, arcpy.ValidateTableName(base_name, gdb_path))
    arcpy.analysis.Clip(out_DLS, studyArea_path, out_DLS_final)
    arcpy.management.Delete(out_DLS)
print("DLS...")
messages()

# List outputs in final GDB
arcpy.env.workspace = r"C:\GEOS456\Assign02\Assignment02.gdb"
print("Below are features in geodatabase")
fc_list = arcpy.ListFeatureClasses()
for files in fc_list:
    print(f" - {files}")
print("")
messages()

#Fieldnames
print("FIELDS:\n")
dls_layer = os.path.join(gdb_path, "T82I_LSD")
for f in arcpy.ListFields(dls_layer):
    print(f.name)
print("")
print("Completed listing fields")
messages()

#Identifying full DLS Description
print("The following is DLS full description:\n")
dls_layer = os.path.join(gdb_path, "T82I_LSD")
fields = ["DESCRIPTOR", "TWP", "RGE", "MER"]

#Search Cursor
with arcpy.da.SearchCursor(dls_layer, fields) as cursor:
    for row in cursor:
        descriptor = row[0]
        township = row[1]
        range_ = row[2]
        meridian = row[3]
        print(f"{descriptor} - TWP{township} - RGE{range_} - W{meridian}")
        break
print("")
messages()
print("")