import arcpy

def add_output_to_current_map(outputs):
    try:
        aprx=arcpy.mp.ArcGISProject("CURRENT")
        active_map=aprx.activeMap

        if not active_map:
            return
        
        route_layer=active_map.addDataFromPath(outputs["route_fc"])
        station_layer=active_map.addDataFromPath(outputs["station_points"])
        events_layer=active_map.addDataFromPath(outputs["out_fc"])

        sym=route_layer.symbology
        if sym.renderer.type=="SimpleRenderer":
            sym.renderer.symbol.color={'RGB': [255, 0, 0, 100]}
            sym.renderer.symbol.width=4
        route_layer.symbology=sym

        sym=station_layer.symbology
        if sym.renderer.type=="SimpleRenderer":
            sym.renderer.symbol.color={'RGB': [0, 0, 255, 100]}
            sym.renderer.symbol.size =6
        station_layer.symbology =sym

        view=aprx.activeView
        if hasattr(view, "camera"):
            extent=arcpy.Describe(outputs["route_fc"]).extent
            view.camera.setExtent(extent)

        station_layer.showLabels=True
        for label in station_layer.ListLabelClasses():
            label.expression = "$feature.Chainage"

    except Exception as e:
        arcpy.AddWarning(f"Could not update map display: {e}")