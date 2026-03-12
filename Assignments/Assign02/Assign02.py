#---------------------------------------------------------------------------------------
# Name:        Assignment 02
# Purpose:      
#
# Author:      vince
#
# Created:     03/02/2026
# Copyright:   (c) vince 2026
# Licence:     <your licence>
#---------------------------------------------------------------------------------------
import arcpy
import os
coordinates=arcpy.SpatialReference("NAD 1983 UTM ZONE 12N")
define_coord=arcpy.SpatialReference("NAD 1983 10TM AEP Resource")
arcpy.env.overwriteOutput=True
#setting workspace
arcpy.env.workspace=r"C:\GEOS456\Assign02"
workspace=arcpy.env.workspace

#Create a list of all the datasets prior to importing into the geodatabase
print("1.Below are the shapefile features before exporting to gdb:")

for dirpath, dirname, filenames in arcpy.da.Walk(workspace):
    for shapefiles in filenames:
        shp_path=os.path.join(dirpath, shapefiles)
        print(f"  - {shapefiles}")
        print("")

        desc=arcpy.Describe(shp_path)
        print("Spatial Reference: " + desc.SpatialReference.name)
        print("Geometry: " + desc.ShapeType)
        print("Data Type: " + desc.dataType)
        print(arcpy.GetMessages())
        print("")

#Check if gdb exists
gdb_path=r"C:\GEOS456\Assign02\Assignment02.gdb"
if arcpy.Exists(gdb_path):
    arcpy.management.Delete(gdb_path)
    print("Deleting Geodatabase...")
    print(arcpy.GetMessages())
    print("")
else:
    print("No Existing Geodatabase")
    print("")

# Creating gdb
gdb_name="Assignment02"
arcpy.management.CreateFileGDB(workspace, gdb_name + ".gdb")
print("Creating Geodatabse...")
print(arcpy.GetMessages())
print("")

#Creating Datasets inside created gdb
dataset_path=gdb_path
dataset_name=["Base_Features", "DLS"]
for datasets in dataset_name:
   arcpy.management.CreateFeatureDataset(dataset_path, datasets, coordinates)
   print(f" Creating { datasets} Dataset...")
   print(arcpy.GetMessages())
   print("")

#Identifying study area
workspace=arcpy.env.workspace
in_layer="82I_TWP"
relationship="INTERSECT"
selecting_fc="GSP_Pointe"
in_layer_path=os.path.join(dirpath, in_layer)
selecting_fc_path=os.path.join(dirpath, selecting_fc)
study_area=arcpy.management.SelectLayerByLocation(in_layer_path, relationship, selecting_fc)

print(arcpy.GetMessages())
print("")

#Export study area to geodatabase
in_feature=study_area
out=gdb_path
out_name="Study_Area"
studyArea_path=os.path.join(out, out_name)

#project first and Export
arcpy.management.Project(in_feature, studyArea_path, coordinates)
print(arcpy.GetMessages())


#Exporting GSP Point to gdb
in_feature="GSP_Pointe"
out_feature=os.path.join(gdb_path, os.path.splitext(in_feature)[0])
arcpy.management.CopyFeatures(in_feature, out_feature)
print(arcpy.GetMessages())
print("")

#making feature layers
base_workspace=r"C:\GEOS456\Assign02\Base"
for dirpath, dirnames, filenames in arcpy.da.Walk(base_workspace):
   for file in filenames:
       shp_path=os.path.join(dirpath, file)
       if file=="BF_CONTOUR_ARC.shp":
           contour_layer=arcpy.MakeFeatureLayer_management(shp_path, "Contours")
       elif file=="BF_CUT_TRAIL_ARC.shp":
           cut_trail_layer=arcpy.MakeFeatureLayer_management(shp_path, "Cut_Trails")
       elif file=="BF_PIPELINE_ARC.shp":
           pipeline_layer=arcpy.MakeFeatureLayer_management(shp_path, "Pipelines")
       elif file=="BF_POWERLINE_ARC.shp":
           powerline_layer=arcpy.MakeFeatureLayer_management(shp_path, "Powerlines")
       elif file=="BF_ROAD_ARC.shp":
           roads_layer=arcpy.MakeFeatureLayer_management(shp_path, "Roads")

#merging
layer_list= ["Contours", "Cut_Trails", "Pipelines", "Powerlines", "Roads"]
for layers in layer_list:
   output=os.path.join(gdb_path, f"{layers}_Merged")
   arcpy.management.Merge([layers], output)

   arcpy.management.DefineProjection(output, define_coord)

   out_dataset=os.path.join(gdb_path, f"{layers}_projected")
   arcpy.management.Project(output, out_dataset, coordinates)

   out_clip=os.path.join(gdb_path, f"{layers}_clipped")

#Cliping
   arcpy.analysis.Clip(out_dataset, studyArea_path, out_clip)
   for features in [output, out_dataset]:
       arcpy.management.Delete(features)

arcpy.env.workspace=r"C:\GEOS456\Assign02\DLS"
DLS_fc=arcpy.ListFeatureClasses()
for fc in DLS_fc:
   valid_name = arcpy.ValidateTableName(fc, gdb_path)
   out_DLS=os.path.join(gdb_path, os.path.splitext(valid_name)[0])
   arcpy.management.CopyFeatures(fc, out_DLS)

   out_DLS_clip=os.path.join(gdb_path, f"{out_DLS}_clipped")

   arcpy.analysis.Clip(out_DLS, studyArea_path, out_DLS_clip)

   arcpy.management.Delete(out_DLS)

arcpy.env.workspace=r"C:\GEOS456\Assign02\Assignment02.gdb"
print("Below are features in geodatabase")
fc_list=arcpy.ListFeatureClasses()
for files in fc_list:
   print(f" - {files}")
   print("")