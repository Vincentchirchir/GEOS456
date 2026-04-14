#working with neighbourhood functions

import arcpy, os
from arcpy.sa import *
from arcpy import env

#setting workspace and overwrite
env.overwriteOutput=True
env.workspace=r"C:\GEOS456\Mod05_Activity03_Data\NeighborhoodStats.gdb"
workspace= env.workspace

#check in extensio
arcpy.CheckOutExtension("Spatial")
print("There we go..!")
print("")

def messages():
    print(arcpy.GetMessage(0))
    count=(arcpy.GetMessageCount())
    print(arcpy.GetMessage(count -1 ))
    print("")

rasterList=arcpy.ListRasters()
for rasters in rasterList:
    desc=arcpy.Describe(rasters)
    print(rasters)
    print("Raster Format: ", desc.format)
    print("Cell Size: ", desc.meanCellWidth)
    print("Spatial Reference: ", desc.SpatialReference.name)
messages()

#next step is to use neighbourhood toolset to generate a new raster with the block statistics
# tool using 3 by 3 rectangle

# Create a variable called landraster that will hold the raster dataset to be used
landraster="lndcover"

# Create another variable called nbr (neighborhood) to specify the parameters of the tool
nbr=NbrRectangle(3,3, "CELL")

# Use the Block Statistics tool generate a new raster
#create a raster using a BLOCK STATS from the neighborhood toolset
#use all default settings for optional parameters
print("Creating Block Stats...")
outBlockStats=BlockStatistics(landraster, nbr, "VARIETY")
messages()

# Save the raster to the geodatabase in your workspace called Varlndblock3_3
print("Saving Block Statistics...")
blockstats_name="Varlndblock3_3"
outBlockStats.save(os.path.join(workspace, blockstats_name))
messages()


#results are new raster is an interger raster dataset. Meaning there is attribute table associated with it

#create a list of fields
fields=arcpy.ListFields(outBlockStats)
for field in fields:
    print("Field Name: ", field.name)

#use searchcursor to retrieve values from the atribute table
with arcpy.da.SearchCursor ("Varlndblock3_3", ["Value", "Count"]) as Scursor:
    print("")
    for row in Scursor:
        print("Value: ", row[0], " ", "Count: ", row[1])
messages()