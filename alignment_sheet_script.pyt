'''
Project: Alignment Sheet Automation Using Python (GEOS459 - Capstone)
Purpose: Generate a script to automate a procedure to creating alignment sheets in ArcGIS Pro
Creators: Nail Murshudov, Vincent Chirchir, Siqin Xiong
Client: Associated Environmental (Tiffany Gauce, Wallace La)
Date Created: January 26th, 2026
'''

#Getting things set up
import arcpy

#CREATING A CUSTOM GEOPROCESSING TOOL:
class Toolbox(object):
    def __init__(self):
        self.label = "Generator"
        self.alias = "generator"
        self.tools = [AlignmentSheetGenerator]

class AlignmentSheetGenerator:
    def __init__(self):
        self.label = "Alignment Sheet Generator" #Gives the name of the geoprocessing tool.
        self.description = "Generates an alignment sheet using a layout template \nONLY PRODUCES LANDSCAPE LAYOUT SHEET" #This gives information on the custom Geoprocessing tool

    #Defining parameters in the geoprocessing tool:
    def getParameterInfo(self):
        #Layout Name
        layout_name = arcpy.Parameter(
            displayName = "Alignment Sheet Name",
            name = "alignment_sheet_name",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input"
        )

        #Layout Size
        layout_size = arcpy.Parameter(
            displayName = "Size",
            name = "layout_size",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input"
        )

        #Size Options
        layout_size.filter.type = "ValueList"
        layout_size.filter.list = ["Letter (11x8.5)",
                                   "Legal (14x8.5)",
                                   "Tabloid (17x11)",
                                   "ANSI C (22x17)",
                                   "ANSI D (34x22)",
                                   "ANSI E (44x34)"]
        
        #Map
        layout_map = arcpy.Parameter(
            displayName = "Input Map",
            name = "input_map",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input"
        )

        layout_map.filter.type = "ValueList"
        arcgispro_project = arcpy.mp.ArcGISProject("CURRENT")          
        map_names = arcgispro_project.listMaps()
        list_maps = [maps.name for maps in map_names] #GEMINI helped with this (Helped to iterate)
        layout_map.filter.list = list_maps #GEMINI helped with this (Helped to add None as a scenario if there is no map frames)

        #Layout Stationings (ONLY WORKS IF YOU HAVE A LINE/POLYLINE IN THE DATA!)
        layout_stationings = arcpy.Parameter(
            displayName = "Showcase stationings?",
            name = "showcase_stationings",
            datatype = "GPBoolean",
            parameterType = "Optional",
            direction = "Input"
        )

        layout_stationings.value = False #GEMINI helped to figure this out

        #Intervals in meters for the stationings (5m = 0+005m, 0+010m. 20m = 0+020m, 0+040m, etc.)
        stationings_interval = arcpy.Parameter(
            displayName = "Stationing Interval (m)",
            name = "interval_in_meters",
            datatype = "GPLong",
            parameterType = "Optional",
            direction = "Input"
        )

        stationings_interval.enabled = False #GEMINI helped to figure this out

        parameters = [layout_name, #0
                      layout_size, #1
                      layout_map, #2
                      layout_stationings, #3
                      stationings_interval] #4

        return parameters

    def updateParameters(self, parameters):
        if parameters[3].value == True: #GEMINI helped with this
            parameters[4].enabled = True
            parameters[4].parameterType = "Required"

        else:
            parameters[4].enabled = False
            parameters[4].parameterType = "Optional"

        # if parameters[?].value == True:
        #     parameters[?].enabled = True

        return
    
    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        #Defining Variables
        lyt_name = parameters[0].valueAsText
        lyt_size = parameters[1].value
        lyt_map_frame = parameters[2].valueAsText
        st_interval = parameters[4].value

        #Setting up the project reference
        arcgispro_project = arcpy.mp.ArcGISProject("CURRENT") #This references the ArcGIS Pro Project (This is needed so python knows what project you are working in)
        targeted_map = arcgispro_project.listMaps(lyt_map_frame)[0]

        #CREATING THE LAYOUT, MAP FRAME, and setting locations for other features (DIFFERENT LAYOUT SIZE = DIFFERENT MAP FRAME SIZE)
        #Setting different layout sizes
        letter = [11, 8.5]
        legal = [14, 8.5]
        tabloid = [17, 11]
        ansi_c = [22, 17]
        ansi_d = [34, 22]
        ansi_e = [44, 34]
        sizes = {"Letter (11x8.5)": letter, 
                 "Legal (14x8.5)": legal, 
                 "Tabloid (17x11)": tabloid,
                 "ANSI C (22x17)": ansi_c,
                 "ANSI D (34x22)": ansi_d,
                 "ANSI E (44x34)": ansi_e
                 }
        layout_size = sizes.get(lyt_size, letter) 

        #CREATING A LAYOUT SHEET
        #Layout Size 
        width = layout_size[0] 
        height = layout_size[1] 

        #Creating Layout
        layout = arcgispro_project.createLayout(width, height, "INCH", lyt_name) #This setting creates the layout sheet in ArcGIS Pro.

        #CREATING A MAP FRAME
        #Map Frame Sizes - MAIN
        x_min = width * 0.2545
        y_min = height * 0.1976
        x_max = width

        #Creating Map Frame
        mp_frame_extent = arcpy.Extent(x_min, y_min, x_max, y_max) #This sets the extension for the map frame
        mp_frame = layout.createMapFrame(mp_frame_extent, targeted_map, "Map Frame") #This creates a mini map frame

# References
# 1. Esri arcpy guides (ALOT OF GUIDES).
# 2. This video helped with the geoprocessing tool: https://www.youtube.com/watch?v=nPUkTyDaIhg
# 3. https://www.w3schools.com/python/ref_dictionary_get.asp
# 4. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/layout-class.htm 