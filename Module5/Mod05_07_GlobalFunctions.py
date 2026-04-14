#imports
import arcpy
from arcpy.sa import *
from arcpy import env

#Seting workspace and overwrite
env.workspace= r"C:\GEOS456\Mod05_Activity05_Data\GlobalStats.gdb"
env.overwriteOutput=True

#Messages
def messages():
    print(arcpy.GetMessage(0))
    count=(arcpy.GetMessageCount())
    print(arcpy.GetMessage(count -1))
    print("")

#Describe data
rasterList=arcpy.ListRasters()
for rasters in rasterList:
    desc=arcpy.Describe(rasters)
    print(rasters)
    print("Format: ", desc.format)
    print("Cell Size: ", desc.meanCellWidth)
    print("Spatial Reference: ", desc.SpatialReference.name)
messages()

fcList=arcpy.ListFeatureClasses()
for fc in fcList:
    desc=arcpy.Describe(fc)
    print(fc)
    print("Shape Type: ", desc.shapeType)
    print("Spatial Reference: ", desc.spatialReference.name)
    print("")

#Next step is using the distance toolset to generate a new distance rasters with the euclidean distance tool

#create an environment object for the processsing extent
#define a variable for each required parameter of the euclidean distance tool
#pply the euclidean distance tool
#save

#set the extent
env.extent="elevation"
#set parameters
InDataUrban="urban"
OutEucUrban="DistUrban"

InDataHighway="highways"
OutDataHighway="DistHighway"

InDataPark="parks"
OutDataPark="DistPark"

#apply euclidean distance
outDistRas=EucDistance(InDataUrban, "", 25)
outDistRas1=EucDistance(InDataHighway, "", 25)
outDistRas2=EucDistance(InDataPark, "", 25)

#save
outDistRas.save(OutEucUrban)
outDistRas1.save(OutDataHighway)
outDistRas2.save(OutDataPark)

print("Distances Created...")
desc=arcpy.Describe(outDistRas)
desc=arcpy.Describe(outDistRas1)
desc=arcpy.Describe(outDistRas2)
print(outDistRas, "|", "Cell Size: ", desc.meanCellWidth)
print(outDistRas1, "|", "Cell Size: ", desc.meanCellWidth)
print(outDistRas2, "|", "Cell Size: ", desc.meanCellWidth)
messages()