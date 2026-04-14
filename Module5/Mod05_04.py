import arcpy, os
from arcpy.sa import *
from arcpy import env

#checking extension
arcpy.CheckExtension("Spatial")
print("Ready!")
print("")

#workspace aand overwrite the ouputs
env.workspace=r"C:\GEOS456\Mod05_Activity02_Data\Avalanche.gdb"
workspace=env.workspace
env.overwriteOutput=True

#define messages
def messages():
    print(arcpy.GetMessage(0))
    count = (arcpy.GetMessageCount())
    print(arcpy.GetMessage(count -1 ))
    print("")

#describe the DEM and retrieve:
rasterList=arcpy.ListRasters()
for rasters in rasterList:
    rasDesc=arcpy.Describe(rasters)
    print(rasters)
    print("Cell Size: ", rasDesc.meanCellWidth)
    print("Spatial Reference: ", rasDesc.SpatialReference.name)
    print("")

#Next is to create a various surfaces from the DEMM, inclusding Slope and Aspect
dem= arcpy.Raster(rasters) #dem must be defined to work with the raster calculaor

#create a variable called sloperaster
slopeRaster=Slope(dem)
print("Processing Slope...")
messages()

#save the slope raster
slope_name="LL_Slope"
slopeRaster.save(os.path.join(workspace, slope_name))
print("Saving slope...")
messages

#create a aspect raster
aspectRaster=Aspect(dem)
print("Processing Aspect...")
messages()

#save aspect
aspect_name="LL_Aspect"
aspectRaster.save(os.path.join(workspace, aspect_name))
print("Saving Aspect...")
messages()

#criteria using map algebra to satisfy criteria
avi_elev=((dem >= 1900) & (dem<=2700))

#save the elevation criteria
avi_elev_name="Elev_Criteria"
avi_elev.save(os.path.join(workspace, avi_elev_name))
print("Saving Elevation Criteria...")
messages()

#specify the slope criteria
avi_slope=((slopeRaster >= 30) & (slopeRaster <=45))

#save the slope criteria
avi_slope_name="Slope_Criteria"
avi_slope.save(os.path.join(workspace, avi_slope_name))
print("Saving slope criteria...")
messages()

#specify aspect criteria
avi_aspect=(aspectRaster >=157.5 & (aspectRaster <= 202.5))

#save aspect cruiteria
avi_aspect_name="Aspect_Criteria"
avi_aspect.save(os.path.join(workspace, avi_aspect_name))
print("Saving Aspect Criteria...")
messages()

#Now that we have created a raster for each of the criteria, we want to combine all 3 rasters
# together to show where the highest likelihood of an avalanche can take place based on the
# parameters

#first ADD all the rasters
finalraster1=((avi_elev) + (avi_slope) + (avi_aspect))

#save the addition above
finalraster1_name="Final_Criteria_Add"
finalraster1.save(os.path.join(workspace, finalraster1_name))
print("Saving Addition...")
messages()

#multiply all the rasters
finalraster2 = ((avi_elev) * (avi_slope) * (avi_aspect))

#save multiplication
finalraster2_name="Final_Criteria_Mult"
finalraster2.save(os.path.join(workspace, finalraster2_name))
print("Saving Multiplication...")
messages()