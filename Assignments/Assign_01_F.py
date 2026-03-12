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

gdb=r"C:\GEOS456\Assign01\Toulouse.gdb"
arcpy.env.workspace=gdb
for fc in arcpy.ListFeatureClasses():
    arcpy.management.Delete(fc)

#setting workspace
arcpy.env.workspace=r"C:\GEOS456\Assign01"
arcpy.env.overwriteOutput=True
gdb_path=r"C:\GEOS456\Assign01\Toulouse.gdb"
coordinates=arcpy.SpatialReference("NTF (Paris) Lambert Sud France")

#List of features in the folders
print("Below are the shapefiles in the folders")
for dirpath, dirname, filenames in arcpy.da.Walk(arcpy.env.workspace):
    for fc in filenames:
        print(f" - {fc}")

        #input path
        input_path=os.path.join(dirpath, fc)
        desc=arcpy.da.Describe(input_path)

        output_path=os.path.join(gdb_path, desc["baseName"])

        project=arcpy.management.Project(input_path, output_path, coordinates)

        output_path=arcpy.ListFeatureClasses()
        for fc_list in output_path:
            print(f" - {fc_list}")

###List of features in gdb
###arcpy.env.workspace=r"C:\GEOS456\Assign01\Toulouse.gdb"
##arcpy.env.workspace=r"C:\GEOS456\Assign01\Toulouse.gdb"
##
##New_fc=arcpy.ListFeatureClasses()
##print("The following are feature classes in gdb: ")
##if New_fc:
##    for fc in New_fc:
##        print(f" - {fc}")
##else:
##    print("Nothing in gdb")





