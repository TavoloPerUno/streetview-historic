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
import argparse

parser = argparse.ArgumentParser(description='Generate historic panoids')

# Required positional argument
parser.add_argument('input_file', type=str,
                    help='Input file')

# Optional positional argument
parser.add_argument('-k', type=str,
                    help='API key')

# Optional argument
parser.add_argument('-t', type=int,
                    help='timeout seconds')


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



def write_historic_panoids(input_file, apikey, timeout_s):

    results = []

    pts = pd.read_csv(input_file)

    for index, row in pts.iterrows():
        lst_result = []
        manager = mp.Manager()
        lst_result = manager.list()
        timeout(panoids_with_timeout, args=(lst_result, row['Y'], row['X']),  timeout=timeout_s, default=None)

        results.extend([{'id': row['id'],
                                      'pt_lat': row['Y'],
                                      'pt_lng': row['X'],
                                      'pano_id': record['panoid'],
                                      'r_lat': record['lat'],
                                      'r_lng': record['lon'],
                                      'year': record['year'] if 'year' in record else '',
                                      'month': record['month'] if 'month' in record else ''} for record in lst_result])

    results = pd.DataFrame(results)

    results.to_csv(os.path.join(DATA_FOLDER, 'panoids_' + os.path.basename(input_file)))

    for index, row in results.iterrows():
        if row['year'] == '' or row['month'] == '':
            metadata = json.load(urlopen(apicallbase + row['pano_id'] + '&key=' + apikey))
            results.loc[index, 'year'] = (metadata['date'])[:4]
            results.loc[index, 'month'] = (metadata['date'])[:5]

    results.to_csv(os.path.join(DATA_FOLDER, 'panoids_final_' + os.path.basename(input_file)))

def main(argv):
    apikey = ''
    inputfile = ''
    timeout_s = 10

    args = parser.parse_args()
    inputfile = os.path.join(DATA_FOLDER, args.input_file)
    apikey = args.k
    timeout_s = args.t
    write_historic_panoids(inputfile, apikey, timeout_s)

if __name__ == "__main__":
    main(sys.argv[1:])
