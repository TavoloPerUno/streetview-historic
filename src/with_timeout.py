import sys
import os
import streetview_edited as streetview
import pandas as pd
import json
import requests
import urllib
import signal
from urllib2 import urlopen

import time
import multiprocessing as mp


def timeout(func, args = (), kwds = {}, timeout = 3, default = None):
    pool = mp.Pool(processes = 1)
    result = pool.apply_async(func, args = args, kwds = kwds)
    try:
        val = result.get(timeout = timeout)
    except mp.TimeoutError:
        pool.terminate()
        return default
    else:
        pool.close()
        pool.join()
        return val

def panoids_with_timeout(lst_result, lat, lon):
    lst_result.extend(streetview.panoids(lat, lon))

DATA_FOLDER = '../data'
apicallbase = 'https://maps.googleapis.com/maps/api/streetview/metadata?&pano='
mykey = 'AIzaSyDiyJQYyVPaQ_GAamLY_AXmLiJBDo0Lyk4'

columns = ['pt_lat','pt_lng', 'pano_id', 'r_lat', 'r_lng', 'year', 'month']
results = pd.DataFrame(columns=columns)

# columns = ['id', 'pt_lat', 'pt_lng', 'pano_id', 'r_lat', 'r_lng', 'year', 'month']
# results = pd.DataFrame(columns=columns)

results = []

pts = pd.read_csv(os.path.join(os.path.join(DATA_FOLDER, 'preston_PUA_random_points_2000.csv')))

for index, row in pts.iterrows():
    lst_result = []
    manager = mp.Manager()
    lst_result = manager.list()
    timeout(panoids_with_timeout, args=(lst_result, row['Y'], row['X']),  timeout=3, default=None)

    results.extend([{'id': row['id'],
                                  'pt_lat': row['Y'],
                                  'pt_lng': row['X'],
                                  'pano_id': record['panoid'],
                                  'r_lat': record['lat'],
                                  'r_lng': record['lon'],
                                  'year': record['year'] if 'year' in record else '',
                                  'month': record['month'] if 'month' in record else ''} for record in lst_result])
        # metadata = json.load(urlopen(apicallbase + record['panoid'] + '&key=' + mykey))
        # year = (metadata['date'])[:4]
        # month = (metadata['date'])[5:]
        # results = results.append({'id': row['id'],
        #                           'pt_lat': row['Y'],
        #                           'pt_lng': row['X'],
        #                           'pano_id': record['panoid'],
        #                           'r_lat': record['lat'],
        #                           'r_lng': record['lon'],
        #                           'year': record['year'] if 'year' in record else year,
        #                           'month': record['month'] if 'month' in record else month}, ignore_index=True)
results = pd.DataFrame(results)

results.to_csv(os.path.join(DATA_FOLDER, 'results_preston.csv'))

for index, row in results.iterrows():
    if row['year'] == '' or row['month'] == '':
        metadata = json.load(urlopen(apicallbase + row['panoid'] + '&key=' + mykey))
        results.loc[index, 'year'] = (metadata['date'])[:4]
        results.loc[index, 'month'] = (metadata['date'])[:5]