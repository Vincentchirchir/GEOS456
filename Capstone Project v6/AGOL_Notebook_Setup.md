**Overview**
Use [AGOL_Notebook_WebTool_v6.py](/c:/GIS%20SCRIPTS/GEOS456/Capstone%20Project%20v6/AGOL_Notebook_WebTool_v6.py) as the main code cell in an ArcGIS Online notebook. Instead of publishing the `.pyt`, you upload the helper `.py` files and publish the notebook as the web tool.

**Upload These Local Files To The Notebook Workspace**
- [workflow.py](/c:/GIS%20SCRIPTS/GEOS456/Capstone%20Project%20v6/workflow.py)
- [route_tools.py](/c:/GIS%20SCRIPTS/GEOS456/Capstone%20Project%20v6/route_tools.py)
- [stationing_tools.py](/c:/GIS%20SCRIPTS/GEOS456/Capstone%20Project%20v6/stationing_tools.py)
- [events_tools.py](/c:/GIS%20SCRIPTS/GEOS456/Capstone%20Project%20v6/events_tools.py)
- [map_tools.py](/c:/GIS%20SCRIPTS/GEOS456/Capstone%20Project%20v6/map_tools.py)

Do not upload the `.pyt` for the ArcGIS Online notebook path.

**Before You Start**
- Create the notebook with `Advanced` runtime because this workflow uses ArcPy.
- You need the `Publish web tools` privilege.
- ArcGIS Online custom web tools cannot be shared publicly.

**Notebook Layout**
1. Create and save a new ArcGIS Online notebook.
2. Upload the five helper `.py` files listed above into the notebook workspace.
3. Use the notebook `Parameters` pane to add input parameters.
4. Click `Insert as variables` to generate the input-variable cell.
5. Paste the contents of [AGOL_Notebook_WebTool_v6.py](/c:/GIS%20SCRIPTS/GEOS456/Capstone%20Project%20v6/AGOL_Notebook_WebTool_v6.py) into a code cell below the input-variable cell.
6. Add output parameters in the `Parameters` pane.
7. For each output parameter, click `Add` so ArcGIS Online inserts its output-snippet cell near the bottom of the notebook.
8. Keep the generated output cells below the main script cell.

**Recommended Input Parameters**
- `input_line`
  Display name: `Input Linear Feature`
  Type: `Feature set`
  Parameter type: `Required`
- `station_interval`
  Display name: `Station Interval`
  Type: `Linear unit`
  Parameter type: `Required`
- `start_measure`
  Display name: `Start Measure`
  Type: `Double`
  Parameter type: `Optional`
- `end_measure`
  Display name: `End Measure`
  Type: `Double`
  Parameter type: `Optional`
- `tolerance`
  Display name: `Search Tolerance`
  Type: `Linear unit`
  Parameter type: `Optional`
- `analysis_layer`
  Display name: `Analysis Layer`
  Type: `Feature set`
  Parameter type: `Optional`

**Optional Extra Analysis Layers**
- `analysis_layer_2`
  Display name: `Analysis Layer 2`
  Type: `Feature set`
  Parameter type: `Optional`
- `analysis_layer_3`
  Display name: `Analysis Layer 3`
  Type: `Feature set`
  Parameter type: `Optional`

The wrapper already looks for all three names. If you only need one, define only `analysis_layer`.

**Recommended Output Parameters**
- `out_route`
  Display name: `Output Route`
  Type: `Feature set`
  Parameter type: `Optional`
- `out_stations`
  Display name: `Output Station Points`
  Type: `Feature set`
  Parameter type: `Optional`
- `out_intersections`
  Display name: `Output Intersections`
  Type: `Feature set`
  Parameter type: `Optional`
- `out_overlaps`
  Display name: `Output Overlaps`
  Type: `Feature set`
  Parameter type: `Optional`
- `out_segment`
  Display name: `Output Segment`
  Type: `Feature set`
  Parameter type: `Optional`

**How To Test Before Publishing**
1. Save the notebook.
2. Run the generated input-parameter cell.
3. Run the main wrapper cell.
4. Skip the generated output-snippet cells during interactive testing.
5. Fix any notebook errors before publishing.

**Publish**
1. Click `Publish`.
2. Give the web tool a title and summary.
3. Start with a max usage time of `15` or `20` minutes unless you know it needs longer.
4. Publish the web tool.
5. Share it with your organization or the group that owns the Experience Builder app.

**Experience Builder**
1. Open the app in Experience Builder.
2. Add an `Analysis` widget.
3. Add a `Custom web tool`.
4. Select the published notebook web tool.
5. Configure which outputs should auto-add to the map.

**Notes**
- The wrapper converts incoming feature sets into scratch feature classes, runs the v6 workflow, then converts outputs back to feature sets.
- If you define more than one analysis layer parameter, the workflow merges all point intersection outputs into one returned layer and all overlap outputs into one returned layer.
- The wrapper applies `context` when ArcGIS Online passes processing extent and output spatial reference.

**Official Docs**
- [Publish a notebook as a web tool](https://doc.arcgis.com/en/arcgis-online/create-maps/publish-a-notebook-as-a-web-tool.htm)
- [Use ArcPy in a notebook](https://doc.arcgis.com/en/arcgis-online/reference/use-arcpy-in-your-notebook.htm)
- [Specify the runtime of a notebook](https://doc.arcgis.com/en/arcgis-online/create-maps/specify-the-runtime-of-a-notebook.htm)
- [Analysis widget](https://doc.arcgis.com/en/experience-builder/11.5/configure-widgets/analysis-widget.htm)
