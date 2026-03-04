import arcpy
from arcpy import env
env.workspace=r"C:\GIS SCRIPTS\GEOS456\Data.gdb"

#list features inside gdb and use describe function to return the spatial reference of the feature class
fc=arcpy.ListFeatureClasses()
for fc_list in fc:
    print(fc_list)
    desc=arcpy.Describe(fc_list)
    print("Spatial Reference: ", desc.spatialReference.name)
    print("Shape Type: ", desc.shapeType)
    print("Path: ", desc.catalogPath)
    print(" ")

#create a variable that will reference every spatial data
fcName1="CityBoundaries"
fcName2="Parcels"
fcName3="Burglary"
fcName4="Crimes2009"

#use of searchcursor
fields=arcpy.ListFields(fcName1)
for field in fields:
    print(field.name)

Scursor=arcpy.da.SearchCursor(fcName1, ["NAME", "STATUS", "COUNTY"])
for row in Scursor:
    print("Name: " + str(row[0]))
    print("Status: " + str(row[1]))
    print("County: " + str(row[2]))
    print("")

#using with statement together with a for loop with the Searchcursor
with arcpy.da.SearchCursor(fcName1, ["NAME", "STATUS", "COUNTY", "STATE"]) as Scursor:
    for row in Scursor:
        print("Name: ", str(row[0]))
        print("Status: ", str(row[1]))
        print("County: ", str(row[2]))
        print("State: ", str(row[3]))
        print("")

# InsertCursor: its inserts rows in a table and populate those rows with information
# DEFINE VARIABLE THE COUNT NUMBER INTERVAL WITH A VARIABLE
# Start a while loop specifying the number of rows to be inserted
# Use the insertRow( ) method to reference the InsertCursor and populate the new row with user entered values
x=1
while x<=1:
    Icursor=arcpy.da.InsertCursor(fcName1, ["NAME"])
    Icursor.insertRow(["Red Deer"])
    x+=1

#To add a unique value to each new row
names=["Calgary", "Edmonton", "Red Deer", "Lethbridge"]
with arcpy.da.InsertCursor(fcName1, ["NAME"]) as Iscursor:
    for name in names:
        Iscursor.insertRow([name])

# Update Cursor
# Use the UpdateCursor( ) function with the AddField_management tool to update values in a new field.
arcpy.AddField_management(fcName1, "AREAS", "DOUBLE")
print("AREAS field has been added...")

#arcpy.AlterField_management(fcName1, "AREA", "AREA_", "AREA_", "DOUBLE")
with arcpy.da.UpdateCursor(fcName1, ["AREA", "Shape_Area"]) as cursor:
    for row in cursor:
        shape_area = row[1]
        if shape_area is None:
            # skip rows with NULL Shape_Area
            continue
        row[0] = shape_area / 1000
        cursor.updateRow(row)

#Construct queries to work with feature classes and tables using the {where_clause} in tool syntax
delimfield=arcpy.AddFieldDelimiters(fcName1, "STATUS")
Scursor=arcpy.da.SearchCursor(fcName1, ["NAME"], delimfield + "<> 'NO CITY'")
for row in Scursor:
    print("Name: " + row[0])

#Incorporate the use of Select by Attributes and Select by Location in Python scripts as well as
#the MakeFeatureLayer and GetCount functions to retrieve additional information.
feature_layer=arcpy.MakeFeatureLayer_management(fcName1, "citybound_layer")
delimfield=arcpy.AddFieldDelimiters(fcName1, "STATUS")
arcpy.SelectLayerByAttribute_management(feature_layer, "NEW_SELECTION", delimfield + " = 'NO CITY'")
count=arcpy.GetCount_management(feature_layer)
print("The number of selected records is: " + str(count))
arcpy.FeatureClassToFeatureClass_conversion(feature_layer, env.workspace, "City_Selection")
print("Successfully created selected feature class...")

#Select by location
layer_feature=arcpy.MakeFeatureLayer_management(fcName4, "crime_layer")
arcpy.SelectLayerByLocation_management(layer_feature, "COMPLETELY_WITHIN", fcName1)
get_count=arcpy.GetCount_management(layer_feature)
print("The number of features seleceted are: " + str(get_count))
arcpy.CopyFeatures_management(layer_feature, "CrimesWITHINCity")
print("Successfully exported feature...")