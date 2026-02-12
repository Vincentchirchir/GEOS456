#---------------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      vince
#
# Created:     19/01/2026
# Copyright:   (c) vince 2026
# Licence:     <your licence>
#---------------------------------------------------------------------------------------
import arcpy
import os

arcpy.env.workspace=r"C:\GEOS456\Assign1"
arcpy.env.overwriteOutput=True
output_gdb=r"C:\GEOS456\Assign1\Toulouse.gdb"
output_sr=arcpy.SpatialReference("NTF (Paris) Lambert Sud France")

print("Below is the list of raw data(shapefile) in the folders: \n")

#ITERATING THROUGH THE FOLDERS
for dirpath, dirname, filenames in arcpy.da.Walk(arcpy.env.workspace):
    for fc in filenames:
        print(f" - {fc} \n")

#Import/export the shapefiles to the geodatabase provided (Toulouse.gdb)

        #DEFINING INPUT PATH
        input_shp=os.path.join(dirpath, fc)

        #removing the shp initials in shapefiles
        desc=arcpy.da.Describe(input_shp)

        #defining path for output data
        output_fc=os.path.join(output_gdb, desc["baseName"])

        #project
        output_prj=arcpy.management.Project(input_shp, output_fc, output_sr)

        #Coordinats of shapefiles
        print("Below is the coordinate system of the shapefiles in the folders: \n")

        sr=arcpy.Describe(input_shp).spatialReference
        print(f" - Coordinate System Name: {sr.name}\n")
        print(f" - Coordinate System Type: {sr.type}\n")
        print(f" - Datum: {sr.datumName}\n")

#What is in gdb now
arcpy.env.workspace=output_gdb
data=arcpy.ListFeatureClasses()

print("Below is the list of feature classes in geodatabse: \n")
if data:
    for fc in data:
        print(f" - {fc}")
else:
    print("No Feature Classes Yet .\n")
##print("We have " + str(len(fc)) + " feature classes in the gdb.\n")

#What is the projection:
print("Below is the coordinate system of the feature classes in the gdb: \n")

sr=arcpy.Describe(fc).spatialReference
print(f" - Coordinate System Name: {sr.name}\n")
print(f" - Coordinate System Type: {sr.type}\n")
print(f" - Datum: {sr.datumName}\n")

#Using intersect
arcpy.env.workspace=(r"C:\GEOS456\Assign1\Toulouse.gdb")

cycling_fc=["Bande_Cyclable", "Piste_Cyclable", "ReseauVert"]
township="communes"

for features in cycling_fc:
    output_intersect=f"{features}_intersected"
    arcpy.analysis.Intersect([features, township], output_intersect)
    fields=arcpy.ListFields(output_intersect)
    print(features, "-", output_intersect, "count:", arcpy.management.GetCount(output_intersect)[0])

#what is in toulouse_intersect Fields?
arcpy.env.workspace=(r"C:\GEOS456\Assign1\Toulouse.gdb")
fields=arcpy.ListFields(output_intersect)
print("\nFields in toulouse_intersect:")
for field in fields:
    print(f" - {field.name}")

#Add length field
arcpy.env.workspace=(r"C:\GEOS456\Assign1\Toulouse.gdb")

attribute_table= "output_intersect"
field_name="Length"
field_type="DOUBLE"

arcpy.management.AddField(attribute_table, field_name, field_type)

#Calculating the Length Field
arcpy.env.workspace=(r"C:\GEOS456\Assign1\Toulouse.gdb")
arcpy.management.CalculateGeometryAttributes("output_intersect", [["Length", "LENGTH"]], "KILOMETERS")


#what is in table After adding and calculating Field?
arcpy.env.workspace=(r"C:\GEOS456\Assign1\Toulouse.gdb")
print("\nFields after new added Length Field:")
fields=arcpy.ListFields(output_intersect)
for field in fields:
    print(f" - {field.name}")