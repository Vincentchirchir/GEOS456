'''
Project: Alignment Sheet Automation Using Python (GEOS459 - Capstone)
Purpose: Generate a script to automate a procedure to creating alignment sheets in ArcGIS Pro
Creators: Nail Murshudov, Vincent Chirchir, Siqin Xiong
Client: Associated Environmental (Tiffany Gauce, Wallace La)
Date Created: January 26th, 2026
'''

#Getting things set up
import arcpy, os
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
            displayName = "Input Linear Feature",
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

        #Select your map scale
        map_series_scale = arcpy.Parameter(
            displayName = "Map Series Scale",
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
                      map_series_scale #9
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
            for mapseries in [9]:
                parameters[mapseries].enabled = True         

        else:
            for mapseries in [9]:
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
            for ms in [9]:
                parameters[ms].parameterType = "Required"
                if not parameters[ms].value:
                    parameters[ms].setErrorMessage("This parameter is required!")
                
        else: 
            for ms in [9]:
                parameters[ms].parameterType = "Optional"
                parameters[ms].clearMessage()
  
        return 
    
    def execute(self, parameters, messages):
        #Defining Variables
        lyt_name = parameters[0].valueAsText
        lyt_size = parameters[1].value
        lyt_main_map_frame = parameters[2].valueAsText
        lyt_mini_map_frame = parameters[3].valueAsText
        st_data = parameters[5].valueAsText
        st_interval = parameters[6].value
        st_data_exclude = parameters[7].valueAsText
        mp_series_scale = parameters[9].value

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
                                            y_max) #This sets the extension for the map frame
        
        mp_frame = layout.createMapFrame(mp_frame_main_extent, 
                                         targeted_main_map, 
                                         "Map Frame") #This creates a mini map frame

        #Creating Mini Map Frame
        mp_frame_main_extent_mini = arcpy.Extent(x_min_mini, 
                                                 y_min_mini, 
                                                 x_max_mini, 
                                                 y_max_mini) #This sets the extension for the map frame
        
        mp_frame_mini = layout.createMapFrame(mp_frame_main_extent_mini, 
                                              targeted_mini_map, 
                                              "Mini Map Frame") #This creates the map frame

        ###MAKING ATTRIBUTES IN THE LAYOUT
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
        legend.elementWidth = 3.314
        legend.elementHeight = 1.5835

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

        legend_cim.fittingStrategy = "AdjustColumnsAndFont"
        legend.setDefinition(legend_cim)

        #NORTH ARROW
        #North Arrow Creation
        north_arrow_x = width * 0.92
        north_arrow_y = height * 0.095294118
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

        #North Arrow Size
        north_arrow.elementWidth = 0.0948
        north_arrow.elementHeight = 0.1972 

        #SCALE BAR
        #Scale Bar Creation
        scale_bar_x = width * 0.932727272727273
        scale_bar_y = height * 0.102352941176471
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
        scale_bar.elementWidth = 0.7902
        scale_bar.elementHeight = 0.3218 
        
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
        map_scale_x = width * 0.948181818181818
        map_scale_y = height * 0.056470588235294
        map_scale_location = arcpy.Point(map_scale_x, 
                                         map_scale_y)
        map_scale = arcgispro_project.createTextElement(layout, map_scale_location, 
                                                        "POINT", 
                                                        '<dyn type="mapFrame" name="Map Frame" property="scale" preStr="1:"/>', 
                                                        original_size) #https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/textelement-class.htm
        map_scale.name = "Map Scale"

        #Map Scale Properties
        map_scale_cim = map_scale.getDefinition("V3")
        map_scale_cim.textSymbol = "Tahoma"
        map_scale_cim.graphic.symbol.symbol.height = dynamic_size
        map_scale.setDefinition(map_scale_cim)

        #MAKING TEXTS
        #Legend Title Tab
        original_size1 = 4
        dynamic_size1 = original_size1 * (height / 8.5)
        legend_title_x = width * 0.008172727272727
        legend_title_y = height * 0.088352941176471
        legend_title_location = arcpy.Point(legend_title_x, 
                                            legend_title_y)
        legend_title = arcgispro_project.createTextElement(layout, 
                                                           legend_title_location, 
                                                           "POINT", 
                                                           "Legend", 
                                                           original_size1)
        legend_title.elementRotation = 90
        legend_title.name = "Legend View"

        #Legend Title Tab Properties
        legend_title_cim = legend_title.getDefinition("V3")
        legend_title_cim.textSymbol = "Tahoma"
        legend_title_cim.graphic.symbol.symbol.height = dynamic_size1
        legend_title.setDefinition(legend_title_cim)

        #Plan View Tab
        original_size2 = 4
        dynamic_size2 = original_size2 * (height / 8.5)
        plan_view__x = width * 0.008627272727273
        plan_view__y = height * 0.485388235294118
        plan_view_location = arcpy.Point(plan_view__x, 
                                         plan_view__y)
        plan_view = arcgispro_project.createTextElement(layout, 
                                                        plan_view_location, 
                                                        "POINT", 
                                                        "Plan View", 
                                                        original_size2)
        plan_view.elementRotation = 90
        plan_view.name = "Plan View"

        #Plan View Tab Properties
        plan_view_cim = plan_view.getDefinition("V3")
        plan_view_cim.textSymbol = "Tahoma"
        plan_view_cim.graphic.symbol.symbol.height = dynamic_size2
        plan_view.setDefinition(plan_view_cim)

        #Stationing Tab
        original_size3 = 4
        dynamic_size3 = original_size3 * (height / 8.5)
        stationing_tab_x = width * 0.008136363636364
        stationing_tab_y = height * 0.885976470588235
        stationing_tab_location = arcpy.Point(stationing_tab_x, 
                                              stationing_tab_y)
        stationing_tab = arcgispro_project.createTextElement(layout, 
                                                             stationing_tab_location, 
                                                             "POINT", 
                                                             "Stationing", 
                                                             original_size3)
        stationing_tab.elementRotation = 90
        stationing_tab.name = "Stationing"

        #Stationing Properties
        stationing_tab_cim = stationing_tab.getDefinition("V3")
        stationing_tab_cim.textSymbol = "Tahoma"
        stationing_tab_cim.graphic.symbol.symbol.height = dynamic_size3
        stationing_tab.setDefinition(stationing_tab_cim)

        #Site Area Title
        original_size4 = 4
        dynamic_size4 = original_size4 * (height / 8.5)
        site_area_title_x = width * 0.393145454545455
        site_area_title_y = height * 0.187129411764706
        site_area_location = arcpy.Point(site_area_title_x, 
                                         site_area_title_y)
        site_area = arcgispro_project.createTextElement(layout, site_area_location, 
                                                        "POINT", 
                                                        "Site Location", 
                                                        original_size4)
        site_area.name = "Site Area"

        #Site Area Title Properties
        site_area_cim = site_area.getDefinition("V3")
        site_area_cim.textSymbol = "Tahoma"
        site_area_cim.graphic.symbol.symbol.height = dynamic_size4
        site_area.setDefinition(site_area_cim)

        #Summmary Table 
        original_size5 = 4
        dynamic_size5 = original_size5 * (height / 8.5)
        summary_table_x = width * 0.392727272727273
        summary_table_y = height * 0.187058823529412
        summary_table_location = arcpy.Point(summary_table_x, 
                                             summary_table_y)
        summary_table = arcgispro_project.createTextElement(layout, 
                                                            summary_table_location, 
                                                            "POINT", 
                                                            "Site Location", 
                                                            original_size5)
        summary_table.name = "Summary Table"

        #Summmary Table Properties
        summary_table_cim = summary_table.getDefinition("V3")
        summary_table_cim.textSymbol = "Tahoma"
        summary_table_cim.graphic.symbol.symbol.height = dynamic_size5
        summary_table.setDefinition(summary_table_cim)

        #Intersection Table
        original_size6 = 4
        dynamic_size6 = original_size6 * (height / 8.5)
        intersection_table_title_x = width * 0.665454545454546
        intersection_table_title_y = height * 0.187058823529412
        intersection_table_location = arcpy.Point(intersection_table_title_x, 
                                                  intersection_table_title_y)
        intersection_table = arcgispro_project.createTextElement(layout, 
                                                                 intersection_table_location, 
                                                                 "POINT", 
                                                                 "Site Location", 
                                                                 original_size5)
        intersection_table.name = "Intersection Table"

        #Intersection Table Properties
        intersection_table_cim = intersection_table.getDefinition("V3")
        intersection_table_cim.textSymbol = "Tahoma"
        intersection_table_cim.graphic.symbol.symbol.height = dynamic_size6
        intersection_table.setDefinition(intersection_table_cim)

        #Intersection Summary
        original_size7 = 4
        dynamic_size7 = original_size7 * (height / 8.5)
        intersection_summary_title_x = width * 0.778181818181818
        intersection_summary_title_y = height * 0.187058823529412
        intersection_summary_location = arcpy.Point(intersection_summary_title_x, 
                                                    intersection_summary_title_y)
        intersection_summary = arcgispro_project.createTextElement(layout, 
                                                                   intersection_summary_location, 
                                                                   "POINT", 
                                                                   "Site Location", 
                                                                   original_size5)
        intersection_summary.name = "Intersection Summary"

        #Intersection Summary Properties
        intersection_summary_cim = intersection_summary.getDefinition("V3")
        intersection_summary_cim.textSymbol = "Tahoma"
        intersection_summary_cim.graphic.symbol.symbol.height = dynamic_size7
        intersection_summary.setDefinition(intersection_summary_cim)

        #Project Name
        original_size8 = 4
        dynamic_size8 = original_size8 * (height / 8.5)
        project_name_title_x = width * 0.860909090909091
        project_name_title_y = height * 0.187058823529412
        project_name_location = arcpy.Point(project_name_title_x, 
                                            project_name_title_y)
        project_name = arcgispro_project.createTextElement(layout, 
                                                           project_name_location, 
                                                           "POINT", 
                                                           "Site Location", 
                                                           original_size5)
        project_name.name = "Project Name"

        #Project Name Properties
        project_name_cim = project_name.getDefinition("V3")
        project_name_cim.textSymbol = "Tahoma"
        project_name_cim.graphic.symbol.symbol.height = dynamic_size8
        project_name.setDefinition(project_name_cim)

































        #MAKING POLYGON BOUNDARIES
        #Legend Element
        x_min_poly1 = width * 0.011818181818182
        y_min_poly1 = 0
        x_max_poly1 = width * 0.325454545454545
        y_max_poly1 = height * 0.197647058823529
        
        poly1_1 = arcpy.Point(x_min_poly1, 
                              y_min_poly1) 
                              
        poly2_1 = arcpy.Point(x_min_poly1, 
                              y_max_poly1) 
        
        poly3_1 = arcpy.Point(x_max_poly1, 
                              y_max_poly1) 
        
        poly4_1 = arcpy.Point(x_max_poly1, 
                              y_min_poly1) 

        poly1_array = arcpy.Array([poly1_1, 
                                   poly2_1, 
                                   poly3_1, 
                                   poly4_1, 
                                   poly1_1])
                                   
        poly1_extent = arcpy.Polygon(poly1_array)

        poly1_type = arcgispro_project.listStyleItems("ArcGIS 2D", 
                                                      "Polygon", 
                                                      "Black Outline (1pt)")[0]
        poly1 = arcgispro_project.createGraphicElement(layout, 
                                                       poly1_extent, 
                                                       poly1_type, 
                                                       name="Legend Border")

        poly1_cim = poly1.getDefinition("V3")
        poly1_cim.preserveRatioLocked = False #GEMINI helped with this
        poly1.setDefinition(poly1_cim)

        #Legend Title
        x_min_poly2 = 0
        y_min_poly2 = 0
        x_max_poly2 = width * 0.011818181818182
        y_max_poly2 = height * 0.197647058823529
        
        poly1_2 = arcpy.Point(x_min_poly2, y_min_poly2) 
        poly2_2 = arcpy.Point(x_min_poly2, y_max_poly2) 
        poly3_2 = arcpy.Point(x_max_poly2, y_max_poly2) 
        poly4_2 = arcpy.Point(x_max_poly2, y_min_poly2) 

        poly2_array = arcpy.Array([poly1_2, poly2_2, poly3_2, poly4_2, poly1_2])
        poly2_extent = arcpy.Polygon(poly2_array)

        poly2_type = arcgispro_project.listStyleItems("ArcGIS 2D", "Polygon", "Black Outline (1pt)")[0]
        poly2 = arcgispro_project.createGraphicElement(layout, poly2_extent, poly2_type, name="Legend Title Border")

        #Plan View 
        x_min_poly3 = 0
        y_min_poly3 = height * 0.197647058823529
        x_max_poly3 = width * 0.011818181818182
        y_max_poly3 = height * 0.801176470588235
        
        poly1_3 = arcpy.Point(x_min_poly3, y_min_poly3) 
        poly2_3 = arcpy.Point(x_min_poly3, y_max_poly3) 
        poly3_3 = arcpy.Point(x_max_poly3, y_max_poly3) 
        poly4_3 = arcpy.Point(x_max_poly3, y_min_poly3) 

        poly3_array = arcpy.Array([poly1_3, poly2_3, poly3_3, poly4_3, poly1_3])
        poly3_extent = arcpy.Polygon(poly3_array)

        poly3_type = arcgispro_project.listStyleItems("ArcGIS 2D", "Polygon", "Black Outline (1pt)")[0]
        poly3 = arcgispro_project.createGraphicElement(layout, poly3_extent, poly3_type, name="Plan View Border")

        #Stationing  
        x_min_poly4 = width * 0
        y_min_poly4 = height * 0.801176470588235
        x_max_poly4 = width * 0.011818181818182
        y_max_poly4 = height * 1
        
        poly1_4 = arcpy.Point(x_min_poly4, y_min_poly4) 
        poly2_4 = arcpy.Point(x_min_poly4, y_max_poly4) 
        poly3_4 = arcpy.Point(x_max_poly4, y_max_poly4) 
        poly4_4 = arcpy.Point(x_max_poly4, y_min_poly4) 

        poly4_array = arcpy.Array([poly1_4, poly2_4, poly3_4, poly4_4, poly1_4])
        poly4_extent = arcpy.Polygon(poly4_array)

        poly4_type = arcgispro_project.listStyleItems("ArcGIS 2D", "Polygon", "Black Outline (1pt)")[0]
        poly4 = arcgispro_project.createGraphicElement(layout, poly4_extent, poly4_type, name="Stationing Border")

        #Site Area
        x_min_poly5 = width * 0.325454545454545
        y_min_poly5 = 0
        x_max_poly5 = width * 0.480909090909091
        y_max_poly5 = height * 0.184705882352941
        
        poly1_5 = arcpy.Point(x_min_poly5, y_min_poly5) 
        poly2_5 = arcpy.Point(x_min_poly5, y_max_poly5) 
        poly3_5 = arcpy.Point(x_max_poly5, y_max_poly5) 
        poly4_5 = arcpy.Point(x_max_poly5, y_min_poly5) 

        poly5_array = arcpy.Array([poly1_5, poly2_5, poly3_5, poly4_5, poly1_5])
        poly5_extent = arcpy.Polygon(poly5_array)

        poly5_type = arcgispro_project.listStyleItems("ArcGIS 2D", "Polygon", "Black Outline (1pt)")[0]
        poly5 = arcgispro_project.createGraphicElement(layout, poly5_extent, poly5_type, name="Stationing Border")

        # #Summary Table
        # x_min_poly5 = width * 0.325454545454545
        # y_min_poly5 = 0
        # x_max_poly5 = width * 0.480909090909091
        # y_max_poly5 = height * 0.184705882352941
        
        # poly1_5 = arcpy.Point(x_min_poly5, y_min_poly5) 
        # poly2_5 = arcpy.Point(x_min_poly5, y_max_poly5) 
        # poly3_5 = arcpy.Point(x_max_poly5, y_max_poly5) 
        # poly4_5 = arcpy.Point(x_max_poly5, y_min_poly5) 

        # poly5_array = arcpy.Array([poly1_5, poly2_5, poly3_5, poly4_5, poly1_5])
        # poly5_extent = arcpy.Polygon(poly5_array)

        # poly5_type = arcgispro_project.listStyleItems("ArcGIS 2D", "Polygon", "Black Outline (1pt)")[0]
        # poly5 = arcgispro_project.createGraphicElement(layout, poly5_extent, poly5_type, name="Stationing Border")

        # #Project Name
        # x_min_poly5 = width * 0.325454545454545
        # y_min_poly5 = 0
        # x_max_poly5 = width * 0.480909090909091
        # y_max_poly5 = height * 0.184705882352941
        
        # poly1_5 = arcpy.Point(x_min_poly5, y_min_poly5) 
        # poly2_5 = arcpy.Point(x_min_poly5, y_max_poly5) 
        # poly3_5 = arcpy.Point(x_max_poly5, y_max_poly5) 
        # poly4_5 = arcpy.Point(x_max_poly5, y_min_poly5) 

        # poly5_array = arcpy.Array([poly1_5, poly2_5, poly3_5, poly4_5, poly1_5])
        # poly5_extent = arcpy.Polygon(poly5_array)

        # poly5_type = arcgispro_project.listStyleItems("ArcGIS 2D", "Polygon", "Black Outline (1pt)")[0]
        # poly5 = arcgispro_project.createGraphicElement(layout, poly5_extent, poly5_type, name="Stationing Border")



        #STATIONING

#       #Map Series
        # strip_output = r"memory\\index_strip"
        # map_series_strip = arcpy.cartography.StripMapIndexFeatures(mp_series_data, strip_output, "USEPAGEUNIT", mp_series_scale)  
        # layout.createSpatialMapSeries(mp_frame_main_extent, strip_output, "PageNumber")
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
# 60. GEMINI HELPED WITH TROUBLESHOOTING
# '''

        