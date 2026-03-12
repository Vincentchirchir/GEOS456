#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      954522
#
# Created:     16/01/2026
# Copyright:   (c) 954522 2026
# Licence:     <your licence>
#-------------------------------------------------------------------------------

#import arcpy
import arcpy
import os

#setting workspace
arcpy.env.workspace=r"C:\GEOS456\Assign01"
arcpy.env.overwriteOutput=True
output_gdb=r"C:\GEOS456\Toulouse.gdb"
coordinates_output=arcpy.SpatialReference("NTF (Paris) Sud France")

print("Below are the shapefiles in the folders: \n")

#iterating through the folders
for dirpath, dirname, filenames in arcpy.da.Walk(arcpy.env.workspace):
    for fc in filenames:
        print(f" - {fc} \n")

#Importing and exporting data to database

        #path to input shapefile
        input_shp=os.path.join(dirpath, fc)

        #clearing the .shp extension
        desc=arcpy.da.Describe(input_shp)

        #path to output feature class
        output_fc=os.path.join(output_gdb, desc["baseName"])

        #project
        projected_fc=arcpy.management.Project(input_shp, output_fc, coordinates_output)

#Whats in the gdb now?
arcpy.env.workspace=r"C:\GEOS456\Toulouse.gdb"
New_fc=arcpy.ListFeatureClasses()

print("Below are the feature classes in Toulouse gdb: \n")

if New_fc:
    for fc in New_fc:
        print(f" - {fc}")

else:
        print("No feature classes in geodatabase")