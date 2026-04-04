import os
import os.path
import json
import geopandas as gpd
import numpy as np

from shapely.ops import unary_union
from shapely import Polygon, Point, box
from multiprocessing import Pool, cpu_count
from typing import Optional, Iterable, Tuple

from . import enu_to_latlon, latlon_to_enu
from .welzl import welzl

s57_source = None
s57_dict = None


def init_s57_config(s57_dir: str, coverage_path: str):
    global s57_source
    global s57_dict

    s57_source = s57_dir
    with open(coverage_path, "r") as fd:
        s57_dict = json.loads(fd.read())
    


def find_s57_within_range(
        longi: float,
        lati: float,
        radius_in_degrees: float,
) -> Iterable[str]:
    """
    this func computes, with the given range (circle), the names of the ENCs that involves
    this func uses a "coverage json", and is more efficient that the native func
    inputs:
        longitude and latitude for center
        radius in degrees
    returns:
        a list of all involved S-57 ENCs
    warning:
        the returned list is promised to contain all ENCs involved, but may include exceed ENCs
    """
    s57_candidates = []

    os_r = radius_in_degrees * np.sqrt(2)

    for s57_id in s57_dict.keys():
        area_longi, area_lati, r = s57_dict[s57_id]

        dist = np.hypot(longi-area_longi, lati-area_lati)
        if dist <= (os_r + r):
            s57_candidates.append(s57_id)
    return s57_candidates



def find_s57_within_range_native(
        longi: float,
        lati: float,
        radius_in_degrees: float,
) -> Iterable[str]:
    """
    this func computes, with the given range (square), the names of the ENCs that involves
    this func traverses all ENCs, using intersection to judge
    inputs:
        longitude and latitude for center
        radius (half of the edge length) in degrees
    returns:
        a list of all involved S-57 ENCs
    """
    s57_candidates = []
    # create shape for OS coverage
    os_coverage = Polygon(
        [
            (longi+radius_in_degrees, lati+radius_in_degrees), (longi-radius_in_degrees, lati+radius_in_degrees),
            (longi-radius_in_degrees, lati-radius_in_degrees), (longi+radius_in_degrees, lati-radius_in_degrees),
        ]
    )

    s57_file_paths = os.listdir(s57_source)
    s57_ids = [file_name[:-4] for file_name in s57_file_paths if file_name[-4:] == ".000"]
    s57_file_paths = [os.path.join(s57_source, file_name) for file_name in s57_file_paths]

    # traverse all ENCs' coverage layer and checks intersactions
    for s57_id, file_name in zip(s57_ids, s57_file_paths):
        gdf = gpd.read_file(file_name, layer="M_COVR")
        union_geom = unary_union(gdf.geometry)
        convex_hull = union_geom.convex_hull

        if convex_hull.intersects(os_coverage):
            s57_candidates.append(s57_id)

    return s57_candidates


def convert_geometry_to_enu(geometry, ref_lon, ref_lat):
    """
    given a geometry in longitude and latitude, transfer it into the ENU coords
    """
    if geometry.geom_type == "Polygon":
        new_coords = [latlon_to_enu(ref_lon, ref_lat, x, y) for x, y in geometry.exterior.coords]
        return Polygon(new_coords)
    else:
        return geometry


def convert_geometry_to_enu_wrapped(args):
    """
    a wrapped version for convert_geometry_to_enu, to be called in multi-processing pool
    """
    geometry, ref_lon, ref_lat = args
    return convert_geometry_to_enu(geometry, ref_lon, ref_lat)


def parellel_convert_geometry_to_enu(
        geoms: Iterable,
        ref_lon,
        ref_lat,
        convert_func,
):
    """
    uses multi-processing pool to convert a list of geometries
    in testing, this function is not as effective as the single-process version
    due to its resource consumption in process communication
    """
    with Pool(processes=cpu_count()) as pool:
        converted = pool.map(convert_func, [(geom, ref_lon, ref_lat) for geom in geoms])
    return converted


def combine_and_crop(
        longi: float,
        lati: float,
        size: int,  # in meters
        buffer_size: int=5, # buffer raidus for Points and buoy
) -> Optional[Tuple[gpd.GeoDataFrame, Polygon]]:
    """
    this func takes a desired area, and returns the vector map of obstacles within that area
    using information derived from ENCs
    inputs:
        longitude and latitude of the area center
        area size, the area will be a square with edge length == 2*size
        buffer size, point geometries will be buffered to circles with radius of buffer_size
    returns:
        None if no information, a geopandas.GeoSeries if any
        the returned geometries will be in ENU coords, with input longi and lati as (0, 0) point
    """
    # approx buffer size from m to degrees
    buffer_size = buffer_size / 111000
    # find size
    los_in_meters = [
        (size, size),
        (-size, size),
        (-size, -size),
        (size, -size),
    ]
    los_in_ll = [enu_to_latlon(longi, lati, x, y) for x, y in los_in_meters]
    longi_c, lati_c, radius = welzl(los_in_ll)

    s57_candidates = find_s57_within_range(
        longi=longi_c, lati=lati_c, radius_in_degrees=radius,
    )

    # get candicate geoms
    geoms = []
    s57_candidates_path = [s57_source+"/"+c+".000" for c in s57_candidates]
    for path in s57_candidates_path:
        # read landmark
        try:
            gdf = gpd.read_file(path, layer="LNDARE")
            for g in gdf.geometry:
                if type(g) is Point:
                    g = g.buffer(buffer_size)
                geoms.append(g)

        except:
            print("{} does not have LNDARE.".format(path))
        # read buoy
        try:
            gdf = gpd.read_file(path, layer="BOYISD")
            for g in gdf.geometry:
                geoms.append(g.buffer(buffer_size, quad_segs=4))
        except:
            print("{} does not have BOYISD.".format(path))
    
    # returns empty gdf if no geometries found
    if len(geoms) == 0:
        vec_obs_gdf = gpd.GeoDataFrame(columns=["geometry", "occupied"])

    # crop candidate geoms
    clip_polygon = Polygon(los_in_ll)
    gdf_clipped = gpd.overlay(gpd.GeoDataFrame(geometry=geoms),
                              gpd.GeoDataFrame(geometry=[clip_polygon]), how="intersection")

    # convert candidates to ENU coord
    gs_enu = gdf_clipped.geometry.apply(lambda geom: convert_geometry_to_enu(geom, longi, lati))
    # multi-process solution
    #print(parellel_convert_geometry_to_enu(gdf_clipped.geometry, longi, lati, convert_geometry_to_enu_wrapped))

    #return geo dataframe
    vec_obs_gdf = gpd.GeoDataFrame(geometry=gs_enu)
    vec_obs_gdf["occupied"] = 100.0
    # append M_COVR to the tail
    #vec_obs_gdf.loc[len(vec_obs_gdf)] = [Polygon(los_in_meters), 0]
    # fake crs for flat rasterization
    vec_obs_gdf = vec_obs_gdf.set_crs(epsg=4674, inplace=True)
    #vec_obs_gdf = vec_obs_gdf.set_crs(epsg=32650, inplace=True)

    return vec_obs_gdf, box(-size, -size, size, size)