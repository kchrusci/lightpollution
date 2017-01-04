#!/usr/bin/python3

import math
import json
import requests
import re

R = 6371 # Earth radius in km

SESSION_URL = "https://www.lightpollutionmap.info/QueryRaster/Session.aspx"
SQM_URL = "https://www.lightpollutionmap.info/geoserver/PostGIS/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=lightpollutionslo_view&outputFormat=application/json"
STATS_URL = "https://www.lightpollutionmap.info/QueryRaster/"

DB_FILE = "db.json"

OVERLAYS = ['viirs_2015', 'viirs_2016']
KMS = ['1', '2', '5', '10', '20', '50', '100']
K = 36

DATA_PATTERN = re.compile("([-e0-9\.]+),([-e0-9\.]+),([-e0-9\.]+),([-e0-9\.]+),([-e0-9\.]+),([-e0-9\.]+)")

def dd2dms(dd):
    mnt, sec = divmod(dd * 3600, 60)
    deg, mnt = divmod(mnt, 60)
    return deg, mnt, sec

def dest_point_dd(lat1, lon1, bearing, d):
    # http://www.movable-type.co.uk/scripts/latlong.html#destPoint

    lat1, lon1 = math.radians(lat1), math.radians(lon1)
    bearing = math.radians(bearing)

    lat2 = math.asin(math.sin(lat1) * math.cos(d/R) +
                     math.cos(lat1) * math.sin(d/R) * math.cos(bearing))

    lon2 = lon1 + math.atan2(math.sin(bearing) * math.sin(d/R) * math.cos(lat1),
                             math.cos(d/R) - math.sin(lat1) * math.sin(lat2))

    return math.degrees(lat2), math.degrees(lon2)

def circle_points(lat, lon, radius, k):
    points = []
    for n in range(k):
        points.append(dest_point_dd(lat, lon, n * (360 / k), radius))
    return points

def make_linestring(points):
    points = ['%f %f' % (point[1], point[0]) for point in points]
    return "LINESTRING(" + ",".join(points) + "," + points[0] + ")"

def get_area_stats(session, lat, lon, overlay, radius, k):
    points = circle_points(lat, lon, radius, k)
    linestring = make_linestring(points)
    r = session.get(STATS_URL, params = {'ql': overlay, 'qt': 'area', 'qd': linestring})
    return r.text

def get_sqm_data(session):
    r = session.get(SQM_URL)
    db = {}
    for p in r.json()['features']:
        gid = p['properties']['gid']
        db[gid] = {
            'coordinates': p['geometry']['coordinates'],
            'properties': p['properties'],
            'data': {}
        }
    return db

def populate_cache(db):
    cache = {}
    for gid in db:
        lon, lat = db[gid]['coordinates']
        for overlay in db[gid]['data']:
            for km in db[gid]['data'][overlay]:
                if (lat, lon, overlay, km) not in cache:
                    if DATA_PATTERN.fullmatch(db[gid]['data'][overlay][km]):
                        cache[(lat, lon, overlay, km)] = db[gid]['data'][overlay][km]
    return cache

def main():
    session = requests.Session()
    session.get(SESSION_URL)

    try:
        db = json.load(open(DB_FILE))
    except FileNotFoundError:
        db = get_sqm_data(session)
        json.dump(db, open(DB_FILE, 'w'), indent = '\t')

    cache = populate_cache(db)

    downloaded = 0

    for gid in db:
        for overlay in OVERLAYS:
            if overlay not in db[gid]['data']:
                db[gid]['data'][overlay] = {}
            for km in KMS:
                if km not in db[gid]['data'][overlay] or not DATA_PATTERN.fullmatch(db[gid]['data'][overlay][km]):
                    lon, lat = db[gid]['coordinates']
                    try:
                        entry = cache[(lat, lon, overlay, km)]
                        db[gid]['data'][overlay][km] = entry
                        print(lat, lon, overlay, km, "CACHED", entry)
                    except KeyError:
                        entry = get_area_stats(session, lat, lon, overlay, int(km), K)
                        db[gid]['data'][overlay][km] = entry
                        cache[(lat, lon, overlay, km)] = entry
                        print(lat, lon, overlay, km, "DOWNLOADED", entry)
                        downloaded += 1
                        if downloaded % 50 == 0:
                            json.dump(db, open(DB_FILE, 'w'), indent = '\t')

    json.dump(db, open(DB_FILE, 'w'), indent = '\t')

if __name__ == "__main__":
    main()
