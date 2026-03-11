#-------------------------------------------------------------------------------
# Name:        module05
# Purpose:      Map Algebra
#
# Author:      954522
#
# Created:     11/03/2026
# Copyright:   (c) 954522 2026
# Licence:     <your licence>
#-------------------------------------------------------------------------------

#import the required module and set the workspace and overwrtite the output
import arcpy
from arcpy import env
from arcpy.sa import *

env.workspace=r"C:\GEOS456\Module5\Avalanche.gdb"
env.overwriteOutput=True

#check out extension for the spatial tools --->OPTIONAL
arcpy.CheckOutExtension("Spatial") #This will make sure it works everytime


#generate a list of rasters
rastersList=arcpy.ListRasters()

#we will describe some raster properties
for raster in rastersList:
    desc=arcpy.Describe(raster)
    print(raster)
    print(desc.meanCellWidth)
    print(desc.spatialReference.name)
    print("")

#define raster object to use in the raster calculator
dem=arcpy.Raster("LakeLouise_DEM")

#generate the additional raster surfaces (slope and aspect)
slopeRaster=Slope(dem) #this will create a temporary raster in the current session
slopeRaster.save("LL_Slope")#This will save the raster to the workspace

aspectRaster=Aspect(dem)
aspectRaster.save("LL_Aspect")

#extract the criteria from each raster
dem_criteria=(dem >= 1900) & (dem <=2700)
dem_criteria.save("Criteria_DEM")

slope_criteria=(slopeRaster >=30) & (slopeRaster<=45)
slope_criteria.save("Criteria_Slope")

aspect_criteria=(aspectRaster >=157.5) & (aspectRaster <=202.5)
aspect_criteria.save("Criteria_Aspect")

#combine all the rasters together
final_raster=dem_criteria * slope_criteria * aspect_criteria
final_raster.save("AVALANCHE")

#Calculating the area of the resulting raster
area_table=TabulateArea("AVALANCHE", "Value", "AVALANCHE", "Value", "Avalanche_Table")

#print the area to the interpreter
scursor=arcpy.da.SearchCursor(area_table, ["VALUE_1"])
for row in scursor:
    print(row[0])
    print("")

#check in the extension -->OPTIONAL
arcpy.CheckInExtension("Spatial")