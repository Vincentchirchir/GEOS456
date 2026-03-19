#-------------------------------------------------------------------------------
# Name:        Module 5
# Purpose:      Generate optimal routes for mountain Lions
#
# Author:      954522
#
# Created:     18/03/2026
# Copyright:   (c) 954522 2026
# Licence:     <your licence>
#-------------------------------------------------------------------------------

#import all required modules
import arcpy
from arcpy.sa import *

#set workspace location and overwrite outputs to equal true
arcpy.env.workspace = r"C:\Winter 2026\GEOS456\Mountain_Lion_Corridors\Mountain_Lion_Corridors.gdb"
arcpy.env.overwriteOutput=True

#check out the spatial extension
arcpy.CheckOutExtension("Spatial")

#define the last geoprocessing message for each tool function
##def messages():
##    count=(arcpy.Get)


'''
We are going to create a cost surface for mountain Lion movement
Lower the cost = more suitable movement

Criteria:
    - Landcover: dense vegetation = lower cost(better habitat)
    - Protected Areas: more protection = lower cost
    - Roads: farther away from roads = lower cost
    - Terrai: more rugged = lower cost

================================================================================

The following raster will determine whether to rescale by function or reclassify
Raster:
    - Discrete rasters --> Reclassify
    - Continous rasters --> Rescale by Function

Landcover: Discrete raster --> reclassify
Protected Areas: discrete raster --> reclassify
proximity to roads: continous raster --> rescale
Terrain: continous raster --> rescale

'''

#Define the input raster as objects
#elevation raster (used to generate the terrain ruggedness)
Elavation = arcpy.Raster("Elevation")

#landcover raster (discrete)
Land_Cover= arcpy.Raster("Land_Cover")

#protected areas raster (discrete)
Protected_Status= arcpy.Raster("Protected_Status")

#DEFINE THE VECTOR INPUTS(HABITAT AREAS)
#feature class that represents the core habitat areas
Habitats="Core_Mountain_Lion_Habitats"


#DERIVE THE TERRAIN RUGGEDNESS RASTER
#focal stats tool which will calculate a stat for each celll based on its neigbour
#NbrRectangle (3x3) = uses a 3x3 moving window across the raster
#RANGE = the difference between max and min elevation in the 3x3 window
#--> Higher value = more rugged terrain
Ruggedness= FocalStatistics(Elavation, NbrRectangle(3, 3, "CELL"), "RANGE")
print(arcpy.GetMessages())

#save the raster
Ruggedness.save("Terrain_R")

#CREATE THE DISTANCE TO ROADS RASTER
#DistanceAccumulation calculate distance from each cell to the nesrest road
# --> Higher Value = farther from the roads (more suitable)
Roads_Distance = DistanceAccumulation("Roads")
print(arcpy.GetMessages())

#save the raster
Roads_Distance.save("Distance_to_Roads")

#RESCALE THE CONTINOUS RASTERS
#Rescale By Function standardise the rasters values to a common scale
#TfLarge --> Larger input values get lower cost (preferred)
#Output Scale: 1 (low cost) to 10 (high cost)

#Terrain ruggedness rescaling
#large values = more rugged
#more rugged = preffered by mountain Lion movement (low cost)
rescale_tr=RescaleByFunction(Ruggedness, "TfLarge", 10, 1)
print(arcpy.GetMessages())

#save the output raster
rescale_tr.save("Terrain_Rescale")

#Distance to roads rescaling
#large values = far from roads
#far from roads --> better habitat (low cost)
rescale_roads= RescaleByFunction(Roads_Distance, "TfLarge", 10, 1)
print(arcpy.GetMessages())

#save the raster
rescale_roads.save("Roads_Rescale")

#RECLASSIFY THE DISCRETE RASTERS
#use the reclassify tool to assign classes to each discrete raster
#reclassify the landcover and the proected areas
land_cover_reclass=Reclassify(Land_Cover, "Value", "11 10; 21 8; 22 7; 23 8;\
24 9; 31 6; 41 2; 42 1; 43 2; 52 3; 71 3; 81 4; 82 6; 90 4; 95 4")
print(arcpy.GetMessages())

#save the rasters
land_cover_reclass.save("LC_Reclass")

#protected areas reclassification
#lower values = more protected =lower cost
protected_status_reclass=Reclassify(Protected_Status, "Value", "1 1; 2 2; 3 3; 4 4; NODATA 10")
print(arcpy.GetMessages())

#save the raster
protected_status_reclass.save("PS_Reclass")

#COMBINE ALL THE RASTER INTO A COST SURFACE
#weightedSum combine multiple rasters into one
#each raster has a weight (importance)

#Terrain & Roads =weight 1
#Landcover & protected Areas = weight 1.25 (slightly more important)
weighted_sum = WeightedSum(WSTable([[rescale_tr, "Value", 1], [rescale_roads, "Value", 1], \
[land_cover_reclass, "Value", 1.25], [protected_status_reclass, "Value", 1.25]]))
print(arcpy.GetMessages())

#save the raster
weighted_sum.save("COST_RASTER")

#GENERATE THE OPTIONAL CORRIDORS
#optimalRegionalCoonectiobs find the least cost path between the habitats
#uses the cost surface (weighted sum)
optimal_routes=OptimalRegionConnections(Habitats, "Paths", "", weighted_sum)
print(arcpy.GetMessages())

#Check in the spatial extension
arcpy.CheckInExtension("Spatial")
