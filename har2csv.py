# Author: Jérémy Kalsron
# License: AGPLv3

# Convert an HAR file with map (OSM, IGN) datas to csv with all tiles bbox as wkt
# Usage example
# python har2csv.py example.har --filter wxs.ign.fr --output example.csv

import argparse
import math
import json
import csv

# parse arguments
parser = argparse.ArgumentParser(description='Parse HAR file')
parser.add_argument('har', help='HAR file to parse')
parser.add_argument('--filter', help='Filter requests', type=str)
parser.add_argument('--output', help='Output csv file', type=str)
args = parser.parse_args()

# load har file
with open(args.har) as f:
    har = json.load(f)['log']

# convert tile coordinates to lat/lon
def tile_to_lat_lon(x, y, z):
    n = 2.0 ** z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

# get tile bounds
def get_tile_bounds(x, y, z):
    lat1, lon1 = tile_to_lat_lon(x, y, z)
    lat2, lon2 = tile_to_lat_lon(x + 1, y + 1, z)
    return (lat1, lon1, lat2, lon2)

# handle params for each map type (osm, ign, ect.)
def handle_url_parameters(url, query_params):
    # if IGN
    if 'wxs.ign.fr' in url or 'geopf.fr' in url:
        tile_x = int(query_params['TileCol'])
        tile_y = int(query_params['TileRow'])
        tile_z = int(query_params['TileMatrix'])
        layer = query_params['layer']
        return (tile_x, tile_y, tile_z, layer)
    # Default
    tile_x = int(url.split('/')[-2])
    tile_y = int(url.split('/')[-1].split('.')[0])
    tile_z = int(url.split('/')[-3])
    return (tile_x, tile_y, tile_z, None)

# get all requests
requests = har['entries']

# filter requests
if args.filter:
    requests = [request for request in requests if args.filter in request['request']['url']]

with open(args.output, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)

    # write header
    writer.writerow(['date', 'url', 'layer', 'size', 'cache', 'tile_x', 'tile_y', 'tile_z', 'bbox_wkt'])

    # iterate over each request
    for request in requests:
        date = request['startedDateTime']
        url = request['request']['url']
        query_params = {}
        for param in request['request']['queryString']: query_params[param['name']] = param['value']
        cache = True if request['cache'] else False
        size = request['response']['content']['size']
        response_status = request['response']['status']

        # if response status is not 200 (OK), skip
        if response_status != 200:
            continue

        # compute bounding box as wkt
        tile_x, tile_y, tile_z, layer = handle_url_parameters(url, query_params)
        lat1, lon1, lat2, lon2 = get_tile_bounds(tile_x, tile_y, tile_z)
        bbox_wkt = f"POLYGON(({lon1} {lat1}, {lon2} {lat1}, {lon2} {lat2}, {lon1} {lat2}, {lon1} {lat1}))"

        # write row for each request
        writer.writerow([date, url, layer, size, cache, tile_x, tile_y, tile_z, bbox_wkt])
