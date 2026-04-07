# Set workspace to C:\GEOS456\FinalProject\
# Check if KananaskisWildlife.gdb exists → delete if yes
# Create new KananaskisWildlife.gdb
# Set up spatial reference (UTM Zone 11, NAD83)
# Set environment settings (cell size = 25m, coordinate system)

#Data Clipping & Organization
# Clip all input datasets to Kananaskis Park Boundary:
# - Roads
# - Trails  
# - Hydrology
# - Habitat locations
# - ESA
# - DEM (Digital Elevation Model)
# - Landcover
# - Townships
# - NTS map sheets

# Save clipped versions to the geodatabase

#Terrain Cost Surface
# Calculate terrain ruggedness from DEM
#    (probably using Slope tool or similar)
# Rescale terrain ruggedness (0-10 scale)
#    - Higher values = more rugged = less desirable

#Land Cover Cost Surface
# 1. Reclassify landcover using the provided table:
#    - Forests (Coniferous/Broadleaf/Mixed) = 1 (best)
#    - Grassland = 2
#    - Shrubland = 3
#    - Exposed Land = 6
#    - Rock/Rubble = 7
#    - Snow/Ice = 8
#    - Agriculture = 9
#    - Water = 10 (worst)
#    - Developed = 10 (worst)

# Proximity Cost Surfaces
# Distance Accumulation for Hydrology
#    Rescale (0-10): closer to water = better (lower cost)

# Distance Accumulation for Trails  
#     Rescale (0-10): farther from trails = better (lower cost)

# Distance Accumulation for Roads
#    Rescale (0-10): farther from roads = better (lower cost)

#Combine Cost Surfaces
# Use Weighted Sum tool to combine all cost surfaces:
# - Terrain ruggedness (rescaled)
# - Landcover (reclassified)
# - Hydrology proximity (rescaled)
# - Trails proximity (rescaled)  
# - Roads proximity (rescaled)

# All weights = 1 (equal importance)

# Result = Single combined cost raster

# Calculate Optimal Routes
#  Convert habitat polygons to points (centroids)
#  Use Cost Distance or Cost Path analysis
#  Calculate least-cost paths between all habitat patches
#  Ensure routes stay within park boundary
#  Convert raster routes to vector (polylines)

#Calculate Statistics
# Average elevation of Kananaskis Country
#    - Use Zonal Statistics on DEM
   
# Area of each landcover type within park
#    - Use Tabulate Area or Zonal Statistics as Table
   
# Total length of optimal routes
#    - Use geometry token on route polylines
   
# Identify NTS map sheets covering park
#    - Spatial selection/intersection
   
# Identify Townships (TWP-RGE-MER) covering park
#    - Spatial selection/intersection

# Store all tables in geodatabase
# Print results to interpreter

#Map Production
# Open existing .aprx template
# Add layers using arcpy.mp:
#    - Park Boundary (polygon)
#    - Habitat locations (points)
#    - Proposed optimal routes (polylines)
   
# Set proper layer order (points → lines → polygons)
# Adjust legend to fit template
# Export to PDF: GEOS456_FP_LastName_FirstName.pdf
