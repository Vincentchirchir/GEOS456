import arcpy, os
import arcpy.mp as MAP
from arcpy import env

#SET WORKSPACE AND OVERWRITE
env.overwriteOutput=True
env.workspace=r"C:\GEOS456\Mod06_Activity01_Data\Map_Scripting.gdb"

#referencing aprx
aprx=arcpy.mp.ArcGISProject(r"C:\GEOS456\Mod06_Activity01_Data\Map_Scripting.aprx")

#list maps within the aprx and the properties
maps1=aprx.listMaps()
for m in maps1:
    print(m.name) #print name of the map frame
    print(m.mapType) #print if the map is 2D, 3D, Scene
    print(m.mapUnits) #print current map units
    print(m.referenceScale) #current map scale
    print("_" * 30)

#creae a list of the feature classes in tthe geodatabase and save them as layer files
fcList=arcpy.ListFeatureClasses()
for fc in fcList:
    print(fc)
    #creatte a layer file
    layers=arcpy.management.MakeFeatureLayer(fc)
    #save the layer as .lyrx
    out_folder=r"C:\GEOS456\Mod06_Activity01_Data"
    out_path=os.path.join(out_folder, fc + ".lyrx")
    lyrfile=arcpy.management.SaveToLayerFile(layers, out_path)
    print(fc, "saved")

    map_obj=aprx.listMaps("Map")[0]
    layer_file=arcpy.mp.LayerFile(out_path)
    map_obj.addLayer(layer_file)

#list layouts
lyt=aprx.listLayouts()
for lyts in lyt:
    print(lyts.name)

#list elements in layout
elements=lyts.listElements()
for elm in elements:
    print(elm.name + " --> " + elm.type)
    if elm.name == "Map Title":
        elm.text = "Calgary"

#save and export as pdf
path1=os.path.join(out_folder, "layers.aprx")
aprx.saveACopy(path1)
del aprx

#export the map to pdf
path=os.path.join(out_folder, "Calgary.pdf")
lyts.exportToPDF(path)