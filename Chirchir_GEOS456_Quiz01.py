# -------------------------------------------------------------------------------
# Name:        Quiz 01
# Purpose:     Quiz 1
#
# Author:      Chirchir Vincent
#
# Created:     06/01/2022
# Copyright:   (c) SAIT
# -------------------------------------------------------------------------------


"""

*** READ THE INSTRUCTIONS CAREFULLY!!! ***

--> Use the following comments as a guide to build your script
--> You may add additional comments/processes to complete the assignment
--> You may modify the comments below
--> Use geoprocessing messages for all geoprocessing tools
--> You may use ArcGIS Pro to view the data and access tool help menus
--> The assignment is open book!
--> DO NOT MODIFY THE ORIGINAL FEATURES IN THE GDB!!!

*** YOU MUST NOT COMMUNICATE WITH ONE ANOTHER IN ANY WAY DURING THE QUIZ ***

*** THE USE OF CHATGPT, COPILOT, ETC. MAY NOT BE USED AT ANY TIME DURING THE QUIZ! ***

"""

# Import the ArcPy Module
import arcpy
import os


# messages
def messages():
    print(arcpy.GetMessage(0))
    count = arcpy.GetMessageCount()
    print(arcpy.GetMessage(count - 1))
    print()


# Define your workspace as outlined in the assignment document
arcpy.env.workspace = r"C:\GEOS456\Quiz01_Redo_Data.gdb"
workspace = arcpy.env.workspace

# Ensure your process can be overwritten
arcpy.env.overwriteOutput = True

# Create a list and describe the Spatial Reference and Geometry of all the feature classes in the geodatabase
print("Listing all features and descriprions...")
fc = arcpy.ListFeatureClasses()
for fc_list in fc:
    print(fc_list)
    desc = arcpy.Describe(fc_list)
    print("Spatial Reference: ", desc.spatialReference.name)
    print("Shape Type: ", desc.shapeType)
    print("Data Type: ", desc.dataType)
    print(" ")
messages()
print("")
# Using the Clip tool, clip the Hydro feature to the city boundary and name the output "Hydro_Clip"
print("Clipping...")
fcname1 = "Hydro"
fcname2 = "City_Boundary"
fcname3 = "Community_District"
out_name = os.path.join(workspace, fcname1 + "_clip")
arcpy.analysis.Clip(fcname1, fcname2, out_name)
messages()
print("")

## Use a Select by Attributes for the following:
# -> Select the Residential features in the Community_District feature class
# -> Return a total count of selected features
# -> Save the selection to the workspace as outlined in the assignment document
feature_layer = arcpy.management.MakeFeatureLayer(fcname3, "Community_layers")
delimfield = arcpy.AddFieldDelimiters(fcname3, "class")
print("Finished creating layer...")
messages()
print("")

arcpy.SelectLayerByAttribute_management(
    feature_layer, "NEW_SELECTION", delimfield + " = 'Residential'"
)
count = arcpy.GetCount_management(feature_layer)
print("The number of selected records is: " + str(count))
print("")
arcpy.FeatureClassToFeatureClass_conversion(
    feature_layer, workspace, "Residential_Communities"
)
print("Successfully created selected feature class...")
messages()
print("")

## Use a Geometry Token for the following:
# -> Print the centroid of each feature in the Residential_Communites feature class to the interpreter
# -> Follow the quiz document for print formatting
fcname4 = "Residential_Communities"
print("Listing rows...")
with arcpy.da.SearchCursor(fcname4, ["SHAPE@XY", "name"]) as Scursor:
    for row in Scursor:
        field = row[1]
        x, y = row[0]
        print(field, ":", x, y)
messages()
print("")

## Use a select by location to accomplish the following:
# -> Select the Hydro_Clip features that intersect with the Residential_Communities feature class created above
# -> Return a total count of selected features
# -> Save the selection to the workspace as outlined in the assignment document
fcname5 = "Hydro_clip"
layer_feature = arcpy.MakeFeatureLayer_management(fcname5, "hydro_layer")
print("Finished creating features")
messages()
print("")

arcpy.SelectLayerByLocation_management(layer_feature, "INTERSECT", fcname4)
get_count = arcpy.GetCount_management(layer_feature)
print("The number of features seleceted are: " + str(get_count))
print("")
arcpy.CopyFeatures_management(layer_feature, "Hydro_Communities")
print("Successfully exported features...")
messages()
print("")

# Create a new text field (with 25 allowable characters) called "Hydro" in the newly created Hydro_Communities feature class
print("Adding new field...")
fcname6 = "Hydro_Communities"
arcpy.AddField_management(fcname6, "Hydro", "TEXT", 25)
print(messages())
print("")

# Using an Update Cursor, populate all the features in the newly created field with “Res_Hydro”
print("Populating new field...")
with arcpy.da.UpdateCursor(fcname6, ["Hydro"]) as cursor:
    for row in cursor:
        row[0] = "Res_Hydro"
        cursor.updateRow(row)
messages()
print("")
# Use a Search Cursor to print the updated values in the new field to the interpreter as outlined in the quiz document
print("Listing rows of new field...")
with arcpy.da.SearchCursor(fcname6, ["OBJECTID", "Hydro"]) as scursor:
    for row in scursor:
        print("OBJECTID ", row[0], ":", row[1])
messages()
print("")

"""
Your script must produce the FIRST and LAST message of each tool function.
Print statements must also be used for all non-tool functions.
"""
