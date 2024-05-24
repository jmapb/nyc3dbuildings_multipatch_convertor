import json
import geopandas as gpd
from shapely.geometry import Polygon 

def multipatch_convertor(geodataframe, z_unit_in='m', relative_h=False, save=False, path='./', filename='output', out_format='geojson'):
    
    """Function converting ESRI Multipatch file into single polygons with 
    assigned height attribute using GeoPandas. It supports input in either 
    meters ('m') and feet ('ft'), as well as assigining relative height.
    Output height values are always meters to comply with GeoJSON Format
    RFC 7946.
    
    Dependencies:
        geopandas==0.3.0
        json==2.0.9
        shapely==1.5.16

    Keyword arguments:
    geodataframe: geopandas.GeoDataFrame() object
            GeoDataFrame to be converted;
    z_unit_in: str, {‘m’, ‘ft’}, default ‘m’
            height units of the input GeoDataFrame;
    relative_h: bool, default False
            If the output GeoDataFrame should present relative height (Applies 
            when minimum height value is not equal to 0). All height values will 
            be subtructed minimum height of the feature.
    save: bool, default False
            whether the function should create an object in memory or save it 
            to file.
    path: str, default ‘./’
            if ‘save’ is set to True, defines directory where to save the output
    filename: str, default ‘output’
            if ‘save’ is set to True, defines the output name of the file
    out_format: str, {‘geojson’, ‘shp’}, default ‘geojson’
            if ‘save’ is set to True, defines the output file format between
            GeoJSON and ESRI Shapefile
    """   
    
    # Extract Coordinate Reference System (CRS) of the GeoDataFrame
    crs = geodataframe.crs
    
    # Convert GeoDataFrame into JSON structure
    gdf_gj = json.loads(geodataframe.to_json())
    
    # Initiate list of features
    feature_list = []

    # Iterate through features of GeoDataFrame
    for feature in gdf_gj['features']:
        # Extract properties of each feature
        properties = feature['properties']

        # Define minimum height
        if z_unit_in == 'm':
            min_h = 9000
        else:
            min_h = 30000
        
        # Initialize empty building parts height dictionary. For each entry, the key will be a tuple of the
        # sequential coordinate pairs (X and Y only, omitting Z) that define the building part polygon, and
        # the value will be a list of all the Z coordinates for these coordinates pairs, from which we can
        # find max and min height. (The multipatch data encodes building part tops and bottoms and seperate
        # polygons with different Z coordinates. It also includes polygons for the walls of buildings, which
        # we'll filter out below.)
        building_parts = {};

        # Loop through multipatch data and populate the building_parts dictionary. Skip any polygons with < 4 points 
        # (first and last point are the same, so 4 will make a triangle, the smallest valid polygon).
        # Also skip any polygon that includes multiple differring Z coordinates, since these are vertical
        # building walls.
        for multipatch_polygon in feature['geometry']['coordinates']:
            if len(multipatch_polygon[0]) > 3 and len(set([c[2] for c in multipatch_polygon[0]])) == 1:
                z_coordinate = multipatch_polygon[0][0][2]
                min_h = min(min_h, z_coordinate)
                xy_coordinates = tuple((c[0],c[1]) for c in multipatch_polygon[0])
                if xy_coordinates in building_parts:
                    building_parts[xy_coordinates].append(z_coordinate)
                else:
                    building_parts[xy_coordinates] = [z_coordinate]        
        
        # Initiate Polygon list for the feature
        splitted_feature_list = []
        
        # Iterate through building_parts dictionary
        for xy_coords, z_coords in building_parts.items():
        
            # Create new feature and assign properties to each Polygon
            new_feature = properties.copy()
            
            # Extract new feature height
            height = max(z_coords)
            
            # Assign new feature's height and vertices
            new_feature['height'] = height
            new_feature['geometry'] = Polygon(xy_coords)

            # Populate polygon list
            splitted_feature_list.append(new_feature)
            
        # Adjust height if relative
        if relative_h:
            for f in splitted_feature_list:
                f['height']=f['height'] - min_h
             
        # Convert height units
        if z_unit_in == 'ft':
            for f in splitted_feature_list:
                f['height']=f['height'] * 0.3048
        elif z_unit_in == 'm':
            pass
        else:
            raise NameError('wrongUnits')
            print('Wrong height units given! Please, choose either ‘m’ for meters or ‘ft’ for feet')            
                
        # Add extracted new features to global feature list
        feature_list = feature_list + splitted_feature_list

    # Create a GeoDataFrame from new features
    new_gdf_gj = gpd.GeoDataFrame(
        feature_list, 
        index=range(len(feature_list)), 
        crs=crs)
    
    # Convert CRS to WGS 84 (lat and long in degrees)
    new_gdf_gj.to_crs({'init':'epsg:4326'}, inplace=True)
    
    # save file in desired location and format or return a GeoDataFrame
    if save:
        if out_format == 'geojson':
            new_gdf_gj.to_file(
                '{}{}.geojson'.format(path, filename), 
                driver='GeoJSON')
        elif out_format == 'shp':
            new_gdf_gj.to_file('{}{}.shp'.format(path, filename))
        else:
            raise NameError('wrongFormat')
            print('Wrong output file format given! Please, choose either ‘geojson’ or ‘shp’')
    else:
        return new_gdf_gj
