#working with rasters
#imports
import arcpy, os
from arcpy import env
from arcpy.sa import *

#checking extension
arcpy.CheckExtension ("Spatial")
print("Ready!")

#overwrite 
env.overwriteOutput = True
env.workspace = r"C:\GEOS456\Mod05_Activity01_Data"

#set workspace for gdb
gdb=r"C:\GEOS456\Mod05_Activity01_Data\RasterData.gdb"
gdb_FD=r"C:\GEOS456\Mod05_Activity01_Data\RasterData.gdb\BaseData"

#use strip method to remove.shp extension in shapefiles
shpList=arcpy.ListFeatureClasses()
for shp in shpList:
    #outFC=os.path.join(gdb_FD, shp.strip(".shp"))
    outFC=os.path.join(gdb_FD, os.path.splitext(shp)[0]) #this also removes extension
    arcpy.CopyFeatures_management(shp, outFC)
    print("Success!!")



#use interpolation tool in the spatial analyst toolbox to create different surfaces from
#the temperature feature class
#define the point feature class which will serve as the input for the raster datasets
#generate the raster surfaces

#define the point feature class
point=os.path.join(gdb_FD, "Temperature")

print(arcpy.Exists(point))
print([f.name for f in arcpy.ListFields(point)])

for f in arcpy.ListFields(point):
    if f.name == "TEMP":
        print(f.name, f.type)

try:
    outIDW = Idw(point, "TEMP")
    outIDW.save(os.path.join(gdb, "Temp_IDW"))
    print("IDW OK")
except:
    print(arcpy.GetMessages())

try:
    outKrig = Kriging(point, "TEMP", "SPHERICAL")
    outKrig.save(os.path.join(gdb, "Temp_Krig"))
    print("Kriging OK")
except:
    print(arcpy.GetMessages())

try:
    outSpline = Spline(point, "TEMP")
    outSpline.save(os.path.join(gdb, "Temp_Spline"))
    print("Spline OK")
except:
    print(arcpy.GetMessages())


print(arcpy.Exists(os.path.join(gdb, "Temp_Spline")))

spline_path = os.path.join(gdb, "Temp_Spline")

print(arcpy.Exists(spline_path))

d = arcpy.Describe(spline_path)
print(d.dataType)
print(d.catalogPath)
print(d.baseName)

#generate the rasters
# outIDW=Idw(point, "TEMP")
# outKrig=Kriging(point, "TEMP", "SPHERICAL")
# outSpline=Spline(point, "TEMP")

# #save the rasters to the gdb
# outIDW.save(os.path.join(gdb, "Temp_IDW"))
# outKrig.save(os.path.join(gdb, "Temp_Krig"))
# outSpline.save(os.path.join(gdb, "Temp_Spline"))


# #Now that we have created the rasters, the next step is to gather raster a list of the raster datasets generated as well as a description
# #of each raster using the ListRasters function and the Describe function
env.workspace=gdb
rasterList=arcpy.ListRasters()
for rasters in rasterList:
    rasterDec=arcpy.Describe(rasters)
    print(rasters)
    print("Rasters Format: ", rasterDec.format)
    print("Cell size: ", rasterDec.meanCellWidth)
    print("Spatial Reference: ", rasterDec.spatialReference.name)
    print("")
