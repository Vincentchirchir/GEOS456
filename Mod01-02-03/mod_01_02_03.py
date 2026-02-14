import arcpy
import os

arcpy.env.overwriteOutput=True
arcpy.env.workspace=r"C:\GEOS456\Mod01-02-03\Crestview.gdb"
workspace=arcpy.env.workspace

#List features
features=arcpy.ListFeatureClasses()
for index, element in enumerate(features):
    print(index, ":", element)
print("")

#Describe features
for feature in features:
    desc=arcpy.Describe(feature)
    print(f" - {feature}")
    print("Spatial Reference: ", desc.SpatialReference.name)
    print("Geometry: ", desc.shapeType)
    print("")
print(arcpy.GetMessages())

#Buffer
workspace=arcpy.env.workspace
in_features="streets"
out_feature=os.path.join(workspace, in_features + "_Buffer")
buffer_distance= "10 Feet"
dissolve_option="ALL"
arcpy.analysis.Buffer(in_features, out_feature, buffer_distance, "", "", dissolve_option)

#Get Count
def countfeatures (workspace):
    count_address=arcpy.management.GetCount(workspace)
    count=[]
    for count_fc in count_address:
        count.append(count_fc)
    return count
count_add=countfeatures ("addresspts")
count=int(count_add[0])
print(f"Address has {count} records")
print("")

workspace=arcpy.env.workspace
arcpy.analysis.Intersect(["addresspts", "streets_buffer"], "streets_intersect")
arcpy.management.CopyFeatures("streets_intersect", "Street_Address")
arcpy.management.Delete("streets_intersect")
print(arcpy.GetMessages())
print("")

count_select=countfeatures("Street_Address")
count_se=int(count_select[0])
print(f"Selected features are {count_se}" )
print("")

workspace_streets=r"C:\GEOS456\Mod01-02-03\Crestview.gdb\Street_Address"
fields=arcpy.ListFields(workspace_streets)
for field_name in fields:
    print(field_name.name)
print("")

#Search Cursor
scursor=arcpy.SearchCursor(workspace_streets)
field="FULL_NAME"; "SUBDIVISIO"
for row in scursor:
    print(row.getValue(field))
# print(arcpy.GetMessages())
print("")

icursor=arcpy.InsertCursor()
