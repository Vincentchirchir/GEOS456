'''
Project: Alignment Sheet Automation Using Python (GEOS459 - Capstone)
Purpose: Generate a script to automate a procedure to creating alignment sheets in ArcGIS Pro
Creators: Nail Murshudov, Vincent Chirchir, Siqin Xiong
Client: Associated Environmental (Tiffany Gauce, Wallace La)
Date Created: January 26th, 2026
'''

#Getting things set up
import arcpy, os, time
arcpy.env.overwriteOutput = True

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
            displayName = "Page Size",
            name = "page_size",
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
        
        #Main Map
        layout_main_map = arcpy.Parameter(
            displayName = "Input Main Map",
            name = "input_main_map",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input"
        )

        #Mini Map
        layout_mini_map = arcpy.Parameter(
            displayName = "Input Mini Map",
            name = "input_mini_map",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input"
        )
        
        maps = arcpy.mp.ArcGISProject("CURRENT").listMaps()  
        maps_names = [all_maps.name for all_maps in maps] #GEMINI helped with this (Helped to iterate)
        layout_main_map.filter.type = "valueList"
        layout_main_map.filter.list = maps_names
        layout_mini_map.filter.type = "valueList"
        layout_mini_map.filter.list = maps_names

        #Include Stations?
        show_stationing = arcpy.Parameter(
            displayName = "Show Stationing?",
            name = "show_stationing",
            datatype = "GPBoolean",
            parameterType = "Optional",
            direction = "Input"
        )

        show_stationing.enabled = True 
        show_stationing.values = False

        #Select your linear data (This is for stationings)
        stationing_data = arcpy.Parameter(
            displayName = "Input Feature",
            name = "input_line_or_polyline_feature",
            datatype = "DEFeatureClass",
            parameterType = "Optional",
            direction = "Input"
        )

        stationing_data.filter.list = ["Polyline"]

        #Intervals in meters for the stationings (5m = 0+005m, 0+010m. 20m = 0+020m, 0+040m, etc.)
        stationings_interval = arcpy.Parameter(
            displayName = "Stationing Interval (m)",
            name = "interval_in_meters",
            datatype = "GPLong",
            parameterType = "Optional",
            direction = "Input"
        )

        #Exclude features you do not want to have intersection points
        exclude_intersect_features = arcpy.Parameter(
            displayName = "Exclude Features from Intersect",
            name = "exclude_layers_from_intersect",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input",
            multiValue = True
        )

        exclude_intersect_features.filter.type = "ValueList" 
        arcgispro_project = arcpy.mp.ArcGISProject("CURRENT")
        main_map = arcgispro_project.listMaps()[0]
        exclude_intersect_features.filter.list = [feature.name for feature in main_map.listLayers() if feature.isFeatureLayer] 

        #Implement Map Series?
        map_series = arcpy.Parameter(
            displayName = "Implement Map Series?",
            name = "implement_map_series",
            datatype = "GPBoolean",
            parameterType = "Optional",
            direction = "Input"
        )

        map_series.enabled = True 
        map_series.values = False

        #Map Series Data
        map_series_data = arcpy.Parameter(
            displayName = "Input Feature",
            name = "input_feature",
            datatype = "DEFeatureClass",
            parameterType = "Optional",
            direction = "Input"
        )

        map_series_data.filter.list = ["Polyline"]

        #Select your map scale
        map_series_scale = arcpy.Parameter(
            displayName = "Scale",
            name = "map_series_scale",
            datatype = "GPLong",
            parameterType = "Optional",
            direction = "Input"
        )

        parameters = [layout_name, #0
                      layout_size, #1
                      layout_main_map, #2
                      layout_mini_map, #3
                      show_stationing, #4
                      stationing_data, #5
                      stationings_interval, #6
                      exclude_intersect_features, #7
                      map_series, #8
                      map_series_data, #9
                      map_series_scale #10
                      ] 

        return parameters

    def updateParameters(self, parameters):
        arcgispro_project = arcpy.mp.ArcGISProject("CURRENT")
        if parameters[4].value == True:
            for station in [5, 6, 7]:
                parameters[station].enabled = True         
            selected_map = arcgispro_project.activeMap 
            if selected_map:
                selected_data = parameters[5].valueAsText
                if selected_data:
                    data_name = os.path.basename(selected_data).split(".")[0]
                else:
                    data_name = ""
                data = [feature.name for feature in selected_map.listLayers() if feature.isFeatureLayer and feature.name != data_name] 
                parameters[7].filter.list = data
        
        else:
            for station in [5, 6, 7]:
                parameters[station].enabled = False   

        if parameters[8].value == True:
            for mapseries in [9, 10]:
                parameters[mapseries].enabled = True         

        else:
            for mapseries in [9, 10]:
                parameters[mapseries].enabled = False
                
        return
    
    def updateMessages(self, parameters):
        if parameters[4].value == True:
            for st in [5, 6, 7]:
                parameters[st].parameterType = "Required"
                if not parameters[st].value:
                    parameters[st].setErrorMessage("This parameter is required!")
                
        else: 
            for ms in [5, 6, 7]:
                parameters[ms].parameterType = "Optional"
                parameters[ms].clearMessage()

        if parameters[8].value == True:
            for ms in [9, 10]:
                parameters[ms].parameterType = "Required"
                if not parameters[ms].value:
                    parameters[ms].setErrorMessage("This parameter is required!")
                
        else: 
            for ms in [9, 10]:
                parameters[ms].parameterType = "Optional"
                parameters[ms].clearMessage()
  
        return 
    
    def execute(self, parameters, messages):
        #Defining Variables
        lyt_name = parameters[0].valueAsText
        lyt_size = parameters[1].value
        lyt_main_map_frame = parameters[2].valueAsText
        lyt_mini_map_frame = parameters[3].valueAsText
        stationing = parameters[4].valueAsText
        st_data = parameters[5].valueAsText
        st_interval = parameters[6].value
        st_data_exclude = parameters[7].valueAsText
        mp_series = parameters[8].valueAsText
        mp_series_data = parameters[9].valueAsText
        mp_series_scale = parameters[10].value

        #Setting up the project reference
        arcgispro_project = arcpy.mp.ArcGISProject("CURRENT") #This references the ArcGIS Pro Project (This is needed so python knows what project you are working in)
        gdb_path = arcgispro_project.defaultGeodatabase
        targeted_main_map = arcgispro_project.listMaps(lyt_main_map_frame)[0]
        targeted_mini_map = arcgispro_project.listMaps(lyt_mini_map_frame)[0]

        #CREATING THE LAYOUT, MAP FRAME, and setting locations for other features (DIFFERENT LAYOUT SIZE = DIFFERENT MAP FRAME SIZE)
        #Setting different layout sizes
        letter = [11, 8.5]
        legal = [14, 8.5]
        tabloid = [17, 11]
        ansi_c = [22, 17]
        ansi_d = [34, 22]
        ansi_e = [44, 34]

        sizes = {
                "Letter (11x8.5)": letter, 
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
        layout = arcgispro_project.createLayout(width, 
                                                height, 
                                                "INCH", 
                                                lyt_name) #This setting creates the layout sheet in ArcGIS Pro.

        #CREATING A MAP FRAME
        #Map Frame Sizes - MAIN
        x_min = width * 0.011818181818182
        y_min = height * 0.197647058823529
        x_max = width
        y_max = height * 0.801176470588235

        #MINI
        x_min_mini = width * 0.32545454545
        y_min_mini = height * 0
        x_max_mini = width * 0.4809090909
        y_max_mini = height * 0.18470588235
         
        #Creating Map Frame
        mp_frame_main_extent = arcpy.Extent(x_min, 
                                            y_min, 
                                            x_max, 
                                            y_max) 
        
        mp_frame = layout.createMapFrame(mp_frame_main_extent, 
                                         targeted_main_map, 
                                         "Map Frame") 
        
        mp_frame_cim = mp_frame.getDefinition("V3")
        mp_frame_cim.graphicFrame.borderSymbol.symbol.symbolLayers[0].width = 0.5
        mp_frame.setDefinition(mp_frame_cim)
        mp_frame.locked = True

        #Creating Mini Map Frame
        mp_frame_main_extent_mini = arcpy.Extent(x_min_mini, 
                                                 y_min_mini, 
                                                 x_max_mini, 
                                                 y_max_mini) 
        
        mp_frame_mini = layout.createMapFrame(mp_frame_main_extent_mini, 
                                              targeted_mini_map, 
                                              "Mini Map Frame") 
        
        mp_frame_mini_cim = mp_frame_mini.getDefinition("V3")
        mp_frame_mini_cim.graphicFrame.borderSymbol.symbol.symbolLayers[0].width = 0.5
        mp_frame_mini.setDefinition(mp_frame_mini_cim)
        mp_frame_mini.locked = True

        ###MAKING ATTRIBUTES IN THE LAYOUT
        width_ratio = width / 11
        height_ratio = height / 8.5
        #LEGEND
        #Legend Creation
        legend_x = width * 0.019090909
        legend_y = height * 0.192941176
        legend_location = arcpy.Point(legend_x, 
                                      legend_y)
        
        legend_style = arcgispro_project.listStyleItems("ArcGIS 2D", 
                                                        "LEGEND", 
                                                        "Legend 1")[0]
        
        legend = layout.createMapSurroundElement(legend_location, 
                                                 "LEGEND", 
                                                 mp_frame, 
                                                 legend_style, 
                                                 "Legend")
        legend.syncLayerVisibility = True
        for data_layers in targeted_main_map.listLayers():
            legend.addItem(data_layers)

        #Legend Size
        legend.elementWidth = 3.314 * width_ratio
        legend.elementHeight = 1.5835 * height_ratio

        #Legend Setting
        legend_cim = legend.getDefinition("V3")
        legend_cim.patchWidth = 10
        legend_cim.patchHeight = 10
        legend_cim.useMapSeriesShape = True
        legend_cim.showTitle = False

        for legend_items in legend_cim.items: 
            legend_items.showLayerName = False
            legend_items.showHeading = False
            legend_items.showGroupLayerName = False
            
        legend_cim.locked = True
        legend_cim.fittingStrategy = "AdjustColumnsAndFont"
        legend.setDefinition(legend_cim)

        #NORTH ARROW
        #North Arrow Creation
        north_arrow_x = width * 0.9247818181818180
        north_arrow_y = height * 0.0404588235294118
        north_arrow_location = arcpy.Point(north_arrow_x, 
                                           north_arrow_y)
        north_arrow_style = arcgispro_project.listStyleItems("ArcGIS 2D", 
                                                             "North_Arrow", 
                                                             "ArcGIS North 3")[0]
        
        north_arrow = layout.createMapSurroundElement(north_arrow_location, 
                                                      "North_Arrow", 
                                                      mp_frame, 
                                                      north_arrow_style, 
                                                      "North Arrow")
        north_arrow.locked = True

        #North Arrow Size
        north_arrow.elementWidth = 0.0948 * width_ratio
        north_arrow.elementHeight = 0.1972 * height_ratio

        #SCALE BAR
        #Scale Bar Creation
        scale_bar_x = width * 0.9204636363636360
        scale_bar_y = height * 0.0534470588235294
        scale_bar_location = arcpy.Point(scale_bar_x, 
                                         scale_bar_y)
        scale_bar_style = arcgispro_project.listStyleItems("ArcGIS 2D", 
                                                           "SCALE_BAR", 
                                                           "Alternating Scale Bar 1 Metric")[0]
        
        scale_bar = layout.createMapSurroundElement(scale_bar_location, 
                                                    "SCALE_BAR", 
                                                    mp_frame, 
                                                    scale_bar_style, 
                                                    "Scale Bar")

        #Scale Bar Size
        scale_bar.elementWidth = 0.7725 * width_ratio
        scale_bar.elementHeight = 0.3148 * height_ratio
        
        #Scale Bar Properties 
        scale_bar_cim = scale_bar.getDefinition("V3")
        scale_bar_cim.unitLabelPosition = "Below"
        scale_bar_cim.divisions = 1
        scale_bar_cim.subdivisions = 3
        scale_bar_cim.fittingStrategy = "AdjustDivision"
        scale_bar_cim.markPosition = "BelowBar"
        scale_bar_cim.unitLabelGap = 3 
        scale_bar_cim.labelSymbol.symbol.height = 4
        scale_bar_cim.unitLabelSymbol.symbol.height = 4
        scale_bar.setDefinition(scale_bar_cim)
                         
        #Map Scale 
        original_size = 4
        dynamic_size = original_size * (height / 8.5)
        map_scale_x = width * 0.9489818181818180
        map_scale_y = height * 0.03927058823529414
        map_scale_location = arcpy.Point(map_scale_x, 
                                         map_scale_y)
        
        map_scale = arcgispro_project.createTextElement(layout, map_scale_location, 
                                                        "POINT", 
                                                        '<dyn type="mapFrame" name="Map Frame" property="scale" preStr="1:"/>', 
                                                        original_size)
        map_scale.name = "Map Scale"
        map_scale.locked = True

        #Map Scale Properties
        map_scale_cim = map_scale.getDefinition("V3")
        map_scale_cim.fontFamilyName = "Tahoma"
        map_scale_cim.graphic.symbol.symbol.height = dynamic_size
        map_scale.setDefinition(map_scale_cim)

        #MAKING TEXTS
        #Setting Properties
        def text_properties(titles, layout, height):

            location = arcpy.Point(titles["text_x"], 
                                   titles["text_y"])
            
            create_text = arcgispro_project.createTextElement(layout, 
                                                              location, 
                                                              "POINT", 
                                                              titles["text"], 
                                                              titles["font_size"])

            create_text.elementRotation = titles["rotation"]
            create_text.name = titles["name"]

            original_size = titles["font_size"]
            dynamic_size = original_size * (height / 8.5)

            text_cim = None
            for timer in range(2):
                try:
                    text_cim = create_text.getDefinition("V3")
                    if text_cim: break   #AI HELPED WITH THIS
                except:
                    time.sleep(0.1)
            
            if text_cim:
                text_cim.graphic.symbol.symbol.fontFamilyName = "Tahoma"
                text_cim.graphic.symbol.symbol.fontStyleName = titles["font_style"]
                text_cim.graphic.symbol.symbol.underline = titles["underline"]
                text_cim.graphic.symbol.symbol.height = dynamic_size
                text_cim.locked = titles["locked"]
                create_text.setDefinition(text_cim)

        #Creating Texts
        texts = [{
            "text": "Legend", 
            "text_x": width * 0.0100636363636364, 
            "text_y": height * 0.0809058823529412, 
            "rotation": 90, 
            "name": "Legend Text", 
            "font_size": 6, 
            "underline": False,
            "font_style": "Bold",
            "locked": True            
        },{
            "text": "Plan View", 
            "text_x": width * 0.0100636363636364,
            "text_y": height * 0.4750941176470590, 
            "rotation": 90, 
            "name": "Plan View",             
            "font_size": 6, 
            "underline": False,            
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Stationing", 
            "text_x": width * 0.0100636363636364, 
            "text_y": height * 0.8750235294117650, 
            "rotation": 90, 
            "name": "Stationing", 
            "font_size": 6, 
            "underline": False,            
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Site Area", 
            "text_x": width * 0.39314545454545500, 
            "text_y": height * 0.18712941176470600, 
            "rotation": 0, 
            "name": "Site Area", 
            "font_size": 4, 
            "underline": False,            
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Summary Table", 
            "text_x": width * 0.52360909090909100, 
            "text_y": height * 0.18716470588235300, 
            "rotation": 0, 
            "name": "Summary Table", 
            "font_size": 4, 
            "underline": False,            
            "font_style": "Bold",    
            "locked": True         
        },{
            "text": "Intersection Table", 
            "text_x": width * 0.665454545454546, 
            "text_y": height * 0.187058823529412, 
            "rotation": 0, 
            "name": "Intersection Table", 
            "font_size": 4, 
            "underline": False,            
            "font_style": "Bold", 
            "locked": True             
        },{
            "text": "Intersection Summary", 
            "text_x": width * 0.778181818181818, 
            "text_y": height * 0.187058823529412, 
            "rotation": 0, 
            "name": "Intersection Summary", 
            "font_size": 4, 
            "underline": False,            
            "font_style": "Bold",
            "locked": True     
        },{
            "text": "Project Name", 
            "text_x": width * 0.860909090909091, 
            "text_y": height * 0.187058823529412, 
            "rotation": 0, 
            "name": "Project Name", 
            "font_size": 4, 
            "underline": True,            
            "font_style": "Bold", 
            "locked": True  
        },{
            "text": "Project Number", 
            "text_x": width * 0.85814545454545500, 
            "text_y": height * 0.16167058823529400, 
            "rotation": 0, 
            "name": "Project Number", 
            "font_size": 4, 
            "underline": True,              
            "font_style": "Bold",
            "locked": True   
        },{
            "text": "Location Address", 
            "text_x": width * 0.85640909090909100, 
            "text_y": height * 0.13356470588235300, 
            "rotation": 0, 
            "name": "Location Address", 
            "font_size": 4, 
            "underline": True,              
            "font_style": "Bold", 
            "locked": True         
        },{
            "text": "Client", 
            "text_x": width * 0.87070909090909100, 
            "text_y": height * 0.10138823529411800, 
            "rotation": 0, 
            "name": "Client", 
            "font_size": 4, 
            "underline": True,              
            "font_style": "Bold",
            "locked": True       
        },{
            "text": "Notes", 
            "text_x": width * 0.87080909090909100, 
            "text_y": height * 0.06797647058823530, 
            "rotation": 0, 
            "name": "Notes", 
            "font_size": 4, 
            "underline": True,              
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Data Sources", 
            "text_x": width * 0.78954545454545500, 
            "text_y": height * 0.06797647058823530, 
            "rotation": 0, 
            "name": "Data Sources", 
            "font_size": 4, 
            "underline": True,              
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Disclaimer", 
            "text_x": width * 0.52998181818181800, 
            "text_y": height * 0.04317647058823530, 
            "rotation": 0, 
            "name": "Disclaimer", 
            "font_size": 4, 
            "underline": True,              
            "font_style": "Bold",
            "locked": True
        },{
            "text": "ID", 
            "text_x": width * 0.63047272727272700, 
            "text_y": height * 0.17443529411764700, 
            "rotation": 0, 
            "name": "Point ID", 
            "font_size": 4, 
            "underline": False,              
            "font_style": "Bold",   
            "locked": True         
        },{
            "text": "Stationing", 
            "text_x": width * 0.67589090909090900, 
            "text_y": height * 0.17443529411764700, 
            "rotation": 0, 
            "name": "Stationing Info", 
            "font_size": 4, 
            "underline": False,              
            "font_style": "Bold",
            "locked": True            
        },{
            "text": "Type", 
            "text_x": width * 0.73805454545454600, 
            "text_y": height * 0.17443529411764700, 
            "rotation": 0, 
            "name": "Intersection Type", 
            "font_size": 4, 
            "underline": False,              
            "font_style": "Bold",  
            "locked": True
        },{
            "text": "Company Logo", 
            "text_x": width * 0.9258000000000000, 
            "text_y": height * 0.1644117647058820, 
            "rotation": 0, 
            "name": "Company Logo", 
            "font_size": 8, 
            "underline": False,              
            "font_style": "Regular", 
            "locked": False 
        },{
            "text": "Completed By:", 
            "text_x": width * 0.92046363636363600, 
            "text_y": height * 0.13342352941176500, 
            "rotation": 0, 
            "name": "Completed By", 
            "font_size": 3, 
            "underline": False,              
            "font_style": "Regular", 
            "locked": False             
        },{
            "text": "Reviewed By:", 
            "text_x": width * 0.92046363636363600, 
            "text_y": height * 0.11680000000000000, 
            "rotation": 0, 
            "name": "Reviewed By", 
            "font_size": 3, 
            "underline": False,              
            "font_style": "Regular", 
            "locked": False            
        },{
            "text": "Signed By:", 
            "text_x": width * 0.92046363636363600, 
            "text_y": height * 0.10018823529411800, 
            "rotation": 0, 
            "name": "Signed By", 
            "font_size": 3, 
            "underline": False,              
            "font_style": "Regular",  
            "locked": False
        },{
            "text": "Coordinate System", 
            "text_x": width * 0.94052727272727300, 
            "text_y": height * 0.02751764705882350, 
            "rotation": 0, 
            "name": "Coordinate System", 
            "font_size": 4, 
            "underline": False,              
            "font_style": "Regular",  
            "locked": False
        },{
            "text": "??/??/20??", 
            "text_x": width * 0.92413636363636400, 
            "text_y": height * 0.00757647058823529, 
            "rotation": 0, 
            "name": "Date", 
            "font_size": 4, 
            "underline": False,              
            "font_style": "Regular",  
            "locked": False
        },{
            "text": "Pipe Name", 
            "text_x": width * 0.5170454545454550, 
            "text_y": height * 0.1740235294117650, 
            "rotation": 0, 
            "name": "Pipe Name", 
            "font_size": 4, 
            "underline": False,              
            "font_style": "Regular",  
            "locked": False
        },{
            "text": "Starting Station: <>", 
            "text_x": width * 0.5170454545454550, 
            "text_y": height * 0.1610941176470590, 
            "rotation": 0, 
            "name": "Starting Station", 
            "font_size": 4, 
            "underline": False,              
            "font_style": "Regular",  
            "locked": True
        },{
            "text": "Ending Station: <>", 
            "text_x": width * 0.5170454545454550, 
            "text_y": height * 0.1481647058823530,
            "rotation": 0, 
            "name": "Ending Station", 
            "font_size": 4, 
            "underline": False,              
            "font_style": "Regular",  
            "locked": True
        },{
            "text": "Total Length: <>", 
            "text_x": width * 0.5170454545454550, 
            "text_y": height * 0.1352235294117650,
            "rotation": 0, 
            "name": "Total Length", 
            "font_size": 4, 
            "underline": False,              
            "font_style": "Regular",  
            "locked": True
        },{
            "text": "From:", 
            "text_x": width * 0.5170454545454550, 
            "text_y": height * 0.1222941176470590,
            "rotation": 0, 
            "name": "From", 
            "font_size": 4, 
            "underline": False,              
            "font_style": "Regular",  
            "locked": False
        },{
            "text": "To:", 
            "text_x": width * 0.5170454545454550, 
            "text_y": height * 0.1093529411764710,
            "rotation": 0, 
            "name": "To", 
            "font_size": 4, 
            "underline": False,              
            "font_style": "Regular",  
            "locked": False
        },{
            "text": "Diameter:", 
            "text_x": width * 0.5170454545454550, 
            "text_y": height * 0.0964235294117647,
            "rotation": 0, 
            "name": "Diameter", 
            "font_size": 4, 
            "underline": False,              
            "font_style": "Regular",  
            "locked": False
        },{
            "text": "Material:", 
            "text_x": width * 0.5170454545454550, 
            "text_y": height * 0.0834352941176471,
            "rotation": 0, 
            "name": "Material", 
            "font_size": 4, 
            "underline": False,              
            "font_style": "Regular",  
            "locked": False
        },{
            "text": "Type:", 
            "text_x": width * 0.5170454545454550, 
            "text_y": height * 0.0704941176470588,
            "rotation": 0, 
            "name": "Type", 
            "font_size": 4, 
            "underline": False,              
            "font_style": "Regular",  
            "locked": False
        },{
            "text": "Company:", 
            "text_x": width * 0.5170454545454550, 
            "text_y": height * 0.0575647058823529,
            "rotation": 0, 
            "name": "Company", 
            "font_size": 4, 
            "underline": False,              
            "font_style": "Regular",  
            "locked": False
        }
        ]
        
        for titles in texts:
            text_properties(titles, layout, height)

        #Making Boundaries
        def boundary_properties(boundary):

            poly_blc = arcpy.Point(boundary["x_min_poly"], 
                                   boundary["y_min_poly"])
            
            poly_tlc = arcpy.Point(boundary["x_min_poly"], 
                                   boundary["y_max_poly"]) 
            
            poly_trc = arcpy.Point(boundary["x_max_poly"], 
                                   boundary["y_max_poly"]) 
            
            poly_brc = arcpy.Point(boundary["x_max_poly"], 
                                   boundary["y_min_poly"]) 

            poly_array = arcpy.Array([poly_blc, 
                                      poly_tlc, 
                                      poly_trc, 
                                      poly_brc, 
                                      poly_blc])
            
            poly_extent = arcpy.Polygon(poly_array)

            poly_type = arcgispro_project.listStyleItems("ArcGIS 2D", 
                                                         "Polygon", 
                                                         "Black Outline (1pt)")[0]
            
            poly = arcgispro_project.createGraphicElement(layout, 
                                                          poly_extent, 
                                                          poly_type, 
                                                          name=boundary["polygon_name"])

            poly_cim = poly.getDefinition("V3")
            poly_cim.locked = True
            poly_cim.graphic.symbol.symbol.symbolLayers[0].width = boundary["outline"] 
            poly.setDefinition(poly_cim)

        #Creating boundaries
        boundaries = [{
            "polygon_name": "Legend", 
            "x_min_poly": width * 0.011818181818182, 
            "y_min_poly": 0, 
            "x_max_poly": width * 0.325454545454545, 
            "y_max_poly": height * 0.197647058823529, 
            "outline": 0.5
        },{
            "polygon_name": "Legend Title", 
            "x_min_poly": 0,
            "y_min_poly": 0, 
            "x_max_poly": width * 0.011818181818182, 
            "y_max_poly": height * 0.197647058823529, 
            "outline": 0.5
        },{
            "polygon_name": "Plan View", 
            "x_min_poly": 0,
            "y_min_poly": height * 0.197647058823529,
            "x_max_poly": width * 0.011818181818182,
            "y_max_poly": height * 0.801176470588235,
            "outline": 0.5
        },{
            "polygon_name": "Stationing", 
            "x_min_poly": 0,
            "y_min_poly": height * 0.801176470588235,
            "x_max_poly": width * 0.011818181818182,
            "y_max_poly": height * 1,
            "outline": 0.5
        },{
            "polygon_name": "Site Area", 
            "x_min_poly": width * 0.325454545454545,
            "y_min_poly": 0,
            "x_max_poly": width * 0.480909090909091,
            "y_max_poly": height * 0.184705882352941,
            "outline": 0.5
        },{
            "polygon_name": "Site Area Title", 
            "x_min_poly": width * 0.3254090909090910,
            "y_min_poly": height * 0.1841647058823530,
            "x_max_poly": width * 0.4809090909090910,
            "y_max_poly": height * 0.1979882352941180,
            "outline": 0.5            
        },{
            "polygon_name": "Summary Table Title", 
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": height * 0.1844352941176470,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.1977764705882350,
            "outline": 0.5     
        },{
            "polygon_name": "Summary Table Column 1", 
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": height * 0.1585647058823530,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.1714941176470590,
            "outline": 0.25     
        },{
            "polygon_name": "Summary Table Column 2", 
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": height * 0.1327058823529410,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.1456352941176470,
            "outline": 0.25                       
        },{
            "polygon_name": "Summary Table Column 3", 
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": height * 0.1068352941176470,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.1197647058823530,
            "outline": 0.25                               
        },{
            "polygon_name": "Summary Table Column 4", 
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": height * 0.0809058823529412,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.0939058823529412,
            "outline": 0.25                                            
        },{
            "polygon_name": "Summary Table Column 5", 
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": height * 0.0550470588235294,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.0679764705882353,
            "outline": 0.25    
        },{
            "polygon_name": "Disclaimer Boundary", 
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": 0,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.0550470588235294,
            "outline": 0.5                
        },{
            "polygon_name": "Intersection Table", 
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.1844352941176470, 
            "x_max_poly": width * 0.7715454545454550,
            "y_max_poly": height * 0.1977882352941180,
            "outline": 0.5                                
        },{
            "polygon_name": "Intersection Table Row", 
            "x_min_poly": width * 0.6612818181818180,
            "y_min_poly": 0,
            "x_max_poly": width * 0.7167363636363640,
            "y_max_poly": height * 0.1844352941176470,
            "outline": 0.25 
        },{
            "polygon_name": "Intersection Table Column 1", 
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.1600000000000000,
            "x_max_poly": width * 0.7715000000000000,
            "y_max_poly": height * 0.1723176470588240,
            "outline": 0.25     
        },{
            "polygon_name": "Intersection Table Column 2", 
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.1353647058823530,
            "x_max_poly": width * 0.7715000000000000,
            "y_max_poly": height * 0.1476823529411760,
            "outline": 0.25     
        },{
            "polygon_name": "Intersection Table Column 3", 
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.1107294117647060,
            "x_max_poly": width * 0.7715000000000000,
            "y_max_poly": height * 0.1230470588235290,
            "outline": 0.25     
        },{
            "polygon_name": "Intersection Table Column 4", 
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.0984117647058824,
            "x_max_poly": width * 0.7715000000000000,
            "y_max_poly": height * 0.1107294117647060,
            "outline": 0.25     
        },{
            "polygon_name": "Intersection Table Column 5", 
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.0737764705882353,
            "x_max_poly": width * 0.7715000000000000,
            "y_max_poly": height * 0.0860941176470588,
            "outline": 0.25     
        },{
            "polygon_name": "Intersection Table Column 6", 
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.0491411764705882,
            "x_max_poly": width * 0.7715000000000000,
            "y_max_poly": height * 0.0614588235294118,
            "outline": 0.25     
        },{
            "polygon_name": "Intersection Table Column 7", 
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.0245058823529412,
            "x_max_poly": width * 0.7715000000000000,
            "y_max_poly": height * 0.0368235294117647,
            "outline": 0.25     
        },{
            "polygon_name": "Intersection Table Column 8", 
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.0121882352941176,
            "x_max_poly": width * 0.7715000000000000,
            "y_max_poly": height * 0.0245058823529412,
            "outline": 0.25     
        },{
            "polygon_name": "Intersection Table Column Border", 
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": 0,
            "x_max_poly": width * 0.7715454545454550,
            "y_max_poly": height * 0.1844352941176470,
            "outline": 0.5    
        },{
            "polygon_name": "Intersection Summary Border", 
            "x_min_poly": width * 0.7715454545454550,
            "y_min_poly": height * 0.1844352941176470,
            "x_max_poly": width * 0.8410363636363640,
            "y_max_poly": height * 0.1977764705882350,
            "outline": 0.5                
        },{
            "polygon_name": "Intersection Summary Column 1", 
            "x_min_poly": width * 0.7715454545454550,
            "y_min_poly": height * 0.1585529411764710,
            "x_max_poly": width * 0.8410363636363640,
            "y_max_poly": height * 0.1714941176470590,
            "outline": 0.25     
        },{
            "polygon_name": "Intersection Summary Column 2", 
            "x_min_poly": width * 0.7715454545454550,
            "y_min_poly": height * 0.1326352941176470,
            "x_max_poly": width * 0.8410363636363640,
            "y_max_poly": height * 0.1455764705882350,
            "outline": 0.25              
        },{
            "polygon_name": "Intersection Summary Column 3", 
            "x_min_poly": width * 0.7715454545454550,
            "y_min_poly": height * 0.1068117647058820,
            "x_max_poly": width * 0.8410363636363640,
            "y_max_poly": height * 0.1197647058823530,
            "outline": 0.25              
        },{
            "polygon_name": "Intersection Summary Column 4", 
            "x_min_poly": width * 0.7715454545454550,
            "y_min_poly": height * 0.0809058823529412,
            "x_max_poly": width * 0.8410363636363640,
            "y_max_poly": height * 0.0944000000000000,
            "outline": 0.25              
        },{
            "polygon_name": "Data Sources", 
            "x_min_poly": width * 0.7715454545454550,
            "y_min_poly": 0,
            "x_max_poly": width * 0.8410363636363640,
            "y_max_poly": height * 0.0809058823529412,
            "outline": 0.5 
        },{
            "polygon_name": "Project name", 
            "x_min_poly": width * 0.8410363636363640,
            "y_min_poly": height * 0.1714941176470590,
            "x_max_poly": width * 0.9152909090909090,
            "y_max_poly": height * 0.1977764705882350,
            "outline": 0.5 
        },{
            "polygon_name": "Project Number", 
            "x_min_poly": width * 0.8410363636363640,
            "y_min_poly": height * 0.1452235294117650,
            "x_max_poly": width * 0.9152909090909090,
            "y_max_poly": height * 0.1715058823529410,
            "outline": 0.5
        },{
            "polygon_name": "Location Address", 
            "x_min_poly": width * 0.8410363636363640,
            "y_min_poly": height* 0.1133294117647060,
            "x_max_poly": width * 0.9152909090909090,
            "y_max_poly": height * 0.1452235294117650,
            "outline": 0.5
        },{
            "polygon_name": "Client", 
            "x_min_poly": width * 0.8410363636363640,
            "y_min_poly": height * 0.0809058823529412,
            "x_max_poly": width * 0.9152909090909090,
            "y_max_poly": height * 0.1133294117647060,
            "outline": 0.5
        },{
            "polygon_name": "Notes", 
            "x_min_poly": width * 0.8410363636363640,
            "y_min_poly": 0,
            "x_max_poly": width * 0.9152909090909090,
            "y_max_poly": height * 0.0809058823529412,
            "outline": 0.5
        },{
            "polygon_name": "Insert Logo", 
            "x_min_poly": width * 0.9152909090909090,
            "y_min_poly": height * 0.1452235294117650,
            "x_max_poly": width, 
            "y_max_poly": height * 0.1977764705882350,
            "outline": 0.5
        },{
            "polygon_name": "Names", 
            "x_min_poly": width * 0.9152909090909090,
            "y_min_poly": height * 0.0943058823529412,
            "x_max_poly": width, 
            "y_max_poly": height * 0.1452235294117650,
            "outline": 0.5
        },{
            "polygon_name": "Names", 
            "x_min_poly": width * 0.9152909090909090,
            "y_min_poly": height * 0.0230588235294118,
            "x_max_poly": width, 
            "y_max_poly": height * 0.0943058823529412,
            "outline": 0.5
        },{
            "polygon_name": "Date", 
            "x_min_poly": width * 0.9152909090909090,
            "y_min_poly": 0,
            "x_max_poly": width * 0.9589090909090910,
            "y_max_poly": height * 0.0230470588235294,
            "outline": 0.5
        },{
            "polygon_name": "Page", 
            "x_min_poly": width * 0.9589090909090910,
            "y_min_poly": 0,
            "x_max_poly": width,
            "y_max_poly": height * 0.0230470588235294,
            "outline": 0.5
        },{
            "polygon_name": "Stationing Bar 1", 
            "x_min_poly": width * 0.0113909090909091,
            "y_min_poly": height * 0.9796117647058820,
            "x_max_poly": width,
            "y_max_poly": height,
            "outline": 0.25
        },{
            "polygon_name": "Stationing Bar 2", 
            "x_min_poly": width * 0.0113909090909091,
            "y_min_poly": height * 0.9398470588235290,
            "x_max_poly": width,
            "y_max_poly": height * 0.9597294117647060,
            "outline": 0.25
        },{
            "polygon_name": "Stationing Bar 3", 
            "x_min_poly": width * 0.0113909090909091,
            "y_min_poly": height * 0.9000823529411760,
            "x_max_poly": width,
            "y_max_poly": height * 0.9199647058823530,
            "outline": 0.25
        },{
            "polygon_name": "Stationing Bar 4", 
            "x_min_poly": width * 0.0113909090909091,
            "y_min_poly": height * 0.8603176470588240,
            "x_max_poly": width,
            "y_max_poly": height * 0.8802000000000000,
            "outline": 0.25
        },{
            "polygon_name": "Stationing Bar 5", 
            "x_min_poly": width * 0.0113909090909091,
            "y_min_poly": height * 0.8205529411764710,
            "x_max_poly": width,
            "y_max_poly": height * 0.8404352941176470,
            "outline": 0.25
        },{
            "polygon_name": "Stationing Bar Border", 
            "x_min_poly": width * 0.0113909090909091,
            "y_min_poly": height * 0.8006705882352940,
            "x_max_poly": width,
            "y_max_poly": height,
            "outline": 0.5
        }
        ]
        
        for boundary in boundaries:
            boundary_properties(boundary)

        #STATIONING
        


        #Map Series
        if mp_series == True:
            strip_output = os.path.join(gdb_path, "name")

            arcpy.cartography.StripMapIndexFeatures(mp_series_data, 
                                                    strip_output, 
                                                    "USEPAGEUNIT", 
                                                    mp_series_scale) 
             
            layout.createSpatialMapSeries(mp_frame_main_extent, 
                                          strip_output, 
                                          "PageNumber") 


#        
    # def postExecute():
    #     sdfsdf

# '''
# References
# 1. Esri arcpy guides (ALOT OF GUIDES).
# 2. This video helped with the geoprocessing tool: https://www.youtube.com/watch?v=nPUkTyDaIhg
# 3. https://www.w3schools.com/python/ref_dictionary_get.asp
# 4. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/layout-class.htm 
# 5. https://pro.arcgis.com/en/pro-app/3.5/arcpy/mapping/legendelement-class.htm 
# 6. https://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-mapping/legendelement-class.htm 
# 7. https://pro.arcgis.com/en/pro-app/3.4/arcpy/mapping/python-cim-access.htm 
# 8. https://github.com/Esri/cim-spec?tab=readme-ov-file 
# 9. https://community.esri.com/t5/python-questions/modifying-scale-bar-with-cim/td-p/1614800 
# 10. https://github.com/Esri/cim-spec/blob/809fb365d8d204d1fbdc51b3fab5bd17d88de2d1/docs/v3/CIMLayout.md#cimscalebar 
# 11. https://community.esri.com/t5/arcgis-pro-questions/adjusting-units-of-a-scale-bar-with-arcpy/td-p/1351689 
# 12. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/textelement-class.htm
# 13. https://pro.arcgis.com/en/pro-app/latest/help/layouts/add-and-modify-dynamic-text.htm
# 14. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/graphicelement-class.htm  
# 15. https://pro.arcgis.com/en/pro-app/latest/tool-reference/cartography/strip-map-index-features.htm 
# 16. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/mapseries-class.htm 
# 17. https://pro.arcgis.com/en/pro-app/latest/help/layouts/add-and-modify-dynamic-text.htm  
# 18. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/arcgisproject-class.htm
# 19. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/python-cim-access.htm
# 20. https://pro.arcgis.com/en/pro-app/3.4/arcpy/mapping/textelement-class.htm
# 21. https://www.w3schools.com/python/ref_module_time.asp
# 22. https://www.w3schools.com/python/python_try_except.asp
# 60. GEMINI HELPED WITH TROUBLESHOOTING
# '''

        





































































































































































































































































































































































































































































































































































































































































































































































































































