#-------------------------------------------------------------------------------
# Name:        module 6
# Purpose:      Mapping
#
# Author:      954522
#
# Created:     01/04/2026
# Copyright:   (c) 954522 2026
# Licence:     <your licence>
#-------------------------------------------------------------------------------

#import all required modules
import arcpy
import arcpy.mp as MAP #ALLOW YOU TO BYPASS TYPING ARCPY.MP PRIOR TO ANY MAPPING FUNCTION

#set the workspace location to access the features to add to the aprx
arcpy.env.workspace= r"C:\Winter 2026\GEOS456\Module 6\Mod06_Activity01_Data\Map_Scripting.gdb"

#allow for overwriting outputs
arcpy.env.overwriteOutput=True

#use the mapping module to access the existing aprx and map frame and layout
#aprx=MAP.ArcGISProject("CURRENT")
aprx=MAP.ArcGISProject(r"C:\Winter 2026\GEOS456\Module 6\Mod06_Activity01_Data\Map_Scripting.aprx")

#save a copy of the aprx to preserve the original file (optional)
aprx.saveACopy("C:\Winter 2026\GEOS456\Module 6\Mod06_Activity01_Data\Map_Scripting_VC.aprx")

#use the new aprx copy to add data and modify
aprx_copy=MAP.ArcGISProject(r"C:\Winter 2026\GEOS456\Module 6\Mod06_Activity01_Data\Map_Scripting.aprx")

#list all the maps in the aprx
mapFrames=aprx_copy.listMaps()

#print the map frame properties
for eachmap in mapFrames:
    print(eachmap) #name of the map (as seen in the contents pane)
    print(eachmap.mapType) #MAP=2D, SCENE 3D

#access a specific map frame in the aprx
m=aprx_copy.listMaps ("Map")[0]

#add all the features from the workspace to the referenced map frame
listFC= arcpy.ListFeatureClasses()

for fc in listFC:
    fc_path=arcpy.env.workspace + "\\" + fc

    #add the feature classes directly to the map
    m.addDataFromPath(fc_path)

    #print statement to show everything worked
    print(fc, "added to the map")

#access and modify the map layout elements (not modifying features, only the elements)
layout=aprx_copy.listLayouts()[0]

#list all the elements in the indexed map layout (text, legend, scale bar, etc)
elements = layout.listElements()

for elm in elements:
    print(elm.name)
    print(elm.type) #print the type (text element, legend element, title element, etc)

    #if the element is the map title, update its text
    if elm.name == "Map Title":
        elm.text = "CALGARY"

#zoom to specific layer in the map layout
#find the layer we want to zoom to
lyr=m.listLayers("CALGIS_CITYBOUND_LIMIT")[0]

#define the map frame that contains the layer
mf=layout.listElements("MAPFRAME_ELEMENT")[0]

#set the map frame extent to match the layer defined above
mf.camera.setExtent(mf.getLayerExtent(lyr, True))


#export the map layout to pdf
layout.exportToPDF(r"C:\Winter 2026\GEOS456\Module 6\Mod06_Activity01_Data\Calgary_Map.pdf")

#save the changes in  the aprx
aprx_copy.save()

#delete any objects created by the script
del aprx, aprx_copy
