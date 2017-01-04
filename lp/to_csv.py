#!/usr/bin/python3

import json
import csv
import itertools

OVERLAYS = ['viirs_2015', 'viirs_2016']
KMS = ['1', '2', '5', '10', '20', '50', '100']
FIELDS = ['count', 'sum', 'mean', 'stddev', 'min', 'max']

fields = ['gid', 'lat', 'lon']
prop_fields = ['sqm', 'sqm_l', 'timemeasure', 'timemeasuretext', 'name', 'comment']
data_fields = ['_'.join(field) for field in itertools.product(OVERLAYS, KMS, FIELDS)]

db = json.load(open("db.json"))

writer = csv.writer(open("db.csv", 'w', newline = ''), delimiter = ';')
writer.writerow(fields + prop_fields + data_fields)

for gid in db:
    lon, lat = db[gid]['coordinates']
    row = [gid, lat, lon]
    prop_row = [db[gid]['properties'][field] for field in prop_fields]
    for i, prop in enumerate(prop_row):
        if isinstance(prop, str):
            prop_row[i] = prop.replace('\n', ' ').replace('\r', ' ')
    data_row = []
    for overlay in OVERLAYS:
        for km in KMS:
            data_row += db[gid]['data'][overlay][km].split(',')
    writer.writerow(row + prop_row + data_row)
