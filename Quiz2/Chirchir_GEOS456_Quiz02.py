# -------------------------------------------------------------------------------
# Name:       QUIZ 2
# Purpose:  The assignment consists of creating a script to perform a series of geoprocessing tasks
#
# Author:      954522
#
# Created:     14/04/2026
# Copyright:   (c) 954522 2026
# Licence:     <your licence>
# -------------------------------------------------------------------------------

"""
Use the following pseudo code to help generate your script and results.
You may modify these comments as needed.

Make sure to read the instructions carefully on the document provided.
There is no need to project any data.

Print the LAST message for all geoprocessing tools
Use print statements for all non-tool functions
"""

# Import required modules
import arcpy, os
from arcpy.sa import *
from arcpy import env

# Set your workspace location to match the document
env.workspace = r"C:\GEOS456\Quiz02.gdb"
gdb_path = env.workspace
# Make sure processes can be overwritten
env.overwriteOutput = True
arcpy.env.overwriteOutput = True

# Check out the required extension for raster processing
arcpy.CheckOutExtension("Spatial")


# List and print all the features and rasters within the workspace and Describe the spatial reference of each dataset
# Messages
def messages():
    print(arcpy.GetMessage(0))
    count = arcpy.GetMessageCount()
    print(arcpy.GetMessage(count - 1))
    print("")


# rasters
rastersList = arcpy.ListRasters()
for rasters in rastersList:
    desc = arcpy.Describe(rasters)
    print(rasters)
    print("Spatial Reference: ", desc.SpatialReference.name)
messages()

# print feature classes in the workspace
FCList = arcpy.ListFeatureClasses()
for fc in FCList:
    print(fc)
    print("Spatial Reference: ", desc.spatialReference.name)
    print("")
messages()

# Using a geometry token, determine and print to the interpreter the exact X, Y location of each volcano
volcano = "volcanoes"

# check fields
print("Identifying fields in volcanoes...")
fields = arcpy.ListFields(volcano)
for field in fields:
    print(field.name)
messages()

# Use Search Curosr
print("Determining exact X, Y location of each volcano...")
with arcpy.da.SearchCursor(volcano, ["NAME", "SHAPE@"]) as Scursor:
    for row in Scursor:
        print("Name: ", row[0])
        for point in row[1]:
            print("X:", point.X, "Y:", point.Y)
messages()

# Buffer each volcano at a distance of 5 kilometers

volcano = "volcanoes"
print("Buffering volcanoes...")
out_feature = os.path.join(gdb_path, volcano + "_Buffer")
distance = "5000 Meters"
arcpy.analysis.Buffer(volcano, out_feature, distance, "", "", "NONE")
messages()

# Print to the interpreter the **Maximum** elevation of each buffered volcano
# define parameters for zonal stats as table
InZoneData = out_feature
ZoneField = "NAME"
InValueRaster = "gtopo1km"
OutTable = "Volcano_Max_elv"

print("Creating Zone Stats Table...")
outzonaltable = ZonalStatisticsAsTable(
    InZoneData, ZoneField, InValueRaster, OutTable, "", "MAXIMUM"
)
messages()

# PRINT TO THE INTERPRETER
print("Printing maximum elevation...")
with arcpy.da.SearchCursor(OutTable, ["NAME", "MAX"]) as Scursoe:
    for row in Scursoe:
        print("Name: ", row[0], " has ", "Maximum Elevation of: ", row[1])
messages()

# Generate and save a slope surface to the workspace
dem = arcpy.Raster(rasters)

# create a variable called sloperaster
slopeRaster = Slope(dem)
print("Processing Slope...")
messages()

# save the slope raster
slope_name = "Oregon_Slope"
slopeRaster.save(os.path.join(gdb_path, slope_name))
print("Saving slope...")
messages()

# Determine the **Average** (mean) slope of each buffered volcano
zonal = ZonalStatistics(out_feature, "NAME", slope_name, "MEAN")
out_zone = os.path.join(gdb_path, "Volcano_Mean_Slope")
zonal.save(out_zone)
messages()

# PRINT TO THE INTERPRETER
print("Printing mean elevation...")
with arcpy.da.SearchCursor(volcano, ["NAME", "ELEVATION"]) as Scursoe:
    for row in Scursoe:
        print("Name: ", row[0], " has ", "Mean Slope of: ", row[1])
messages()

# Check in the extension used in the assignment
arcpy.CheckInExtension("Spatial")
