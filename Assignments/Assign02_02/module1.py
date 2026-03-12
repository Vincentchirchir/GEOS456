import arcpy
import os
coordinates=arcpy.SpatialReference("NAD 1983 UTM ZONE 12N")
arcpy.env.overwriteOutput=True


arcpy.env.workspace=r"C:\GEOS456\Assign02_02"
workspace=arcpy.env.workspace

def listfeatures(workspace):
    shp_data=[]
    for dirpath, dirname, filenames in arcpy.da.Walk(workspace):
        for files in filenames:
            shp_data.append(os.path.join(dirpath, files))
    return shp_data

shp=listfeatures(workspace)
for index, element in enumerate(shp):
    print(index, ":", os.path.basename(element))
print()

#desc datatype
print("Below are the description of data")
print("")
for fc in shp:
    desc=arcpy.Describe(fc)
    print(f" - {os.path.basename(fc)}")
    print("Spatial Reference: " + desc.SpatialReference.name)
    print("Geometry: " + desc.shapeType)
    print("Data Type: " + desc.dataType)
    print()

#checking gdb
list_gdb=arcpy.ListWorkspaces("", "FileGDB")
for gdb in list_gdb:
    arcpy.management.Delete(gdb)

#Creating gdb
gdb_name="Assignment02"
gdb_path=os.path.join(workspace, gdb_name + ".gdb")
arcpy.management.CreateFileGDB(workspace, gdb_name)
print(arcpy.GetMessages())

#Creating dataset
dataset_path=gdb_path
out_name= ["Base_features", "DLS"]
for dataset in out_name:
   arcpy.management.CreateFeatureDataset(dataset_path, dataset, coordinates)
print(arcpy.GetMessages())

#Identfying study area