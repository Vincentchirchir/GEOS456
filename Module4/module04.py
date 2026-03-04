import arcpy
arcpy.env.overwriteOutput=True
arcpy.env.workspace=r"C:\GIS SCRIPTS\GEOS456\Data.gdb"
print("")
fc=arcpy.ListFeatureClasses()
print(fc)
print("")

fcName1="BexarCountyBoundaries"
fcName2="Crimes2009"
fcName3="SchoolDistricts"
# desc=arcpy.Describe(fcName1)
# print("Spatial Reference: ", desc.SpatialReference.name)
# print('')

# scurcsor=arcpy.da.SearchCursor(fcName1, ["SHAPE@AREA"])
# for row in scurcsor:
#     print("Area: ", row[0])
#     print("")
# count=arcpy.GetCount_management(fcName2)
# print(f"There are: {count} records")
# #Read point XY geometry
# with arcpy.da.SearchCursor(fcName2, ["SHAPE@XY"]) as scursor:
#     for row in scursor:
#         x, y=row[0]
#         #print(x, y)

# #Read Polygon X,Y geometry
# with arcpy.da.SearchCursor(fcName3, ["OID@", "SHAPE@"]) as scurcor:
#     for row in scurcor:
#         print("Feature: ", row[0])

#         for point in row[1].getPart(0):
#             print("x: ", point.X, " y: ", point.Y)

#Writing geometries
