import sys
import os
import streetview_edited as streetview
import pandas as pd
import json
import requests
import multiprocessing as mproc
import time
import urllib
import signal
from urllib2 import urlopen

def panoids_with_timeout(lst_result, lat, lon):
    lst_result.extend(streetview.panoids(lat, lon))

DATA_FOLDER = '../data'
apicallbase = 'https://maps.googleapis.com/maps/api/streetview/metadata?&pano='
mykey = 'AIzaSyDiyJQYyVPaQ_GAamLY_AXmLiJBDo0Lyk4'

columns = ['pt_lat','pt_lng', 'pano_id', 'r_lat', 'r_lng', 'year', 'month']
results = pd.DataFrame(columns=columns)

columns = ['id', 'pt_lat', 'pt_lng', 'pano_id', 'r_lat', 'r_lng', 'year', 'month']
results = pd.DataFrame(columns=columns)

pts = pd.read_csv(os.path.join(os.path.join(DATA_FOLDER, 'preston_PUA_random_points_2000.csv')))



class TimeOutException(Exception):
    def __init__(self, message, errors):
        super(TimeOutException, self).__init__(message)
        self.errors = errors

def signal_handler(signum, frame):
    raise TimeOutException("Timeout!")



for index, row in pts.iterrows():
    lst_result = []

    # This try/except loop ensures that
    #   you'll catch TimeoutException when it's sent.
    signal.alarm(3)
    try:
        panoids_with_timeout(lst_result, row['Y'], row['X'])  # Whatever your function that might hang
    except TimeOutException:
        continue
    signal.alarm(0)# continue the for loop if function A takes more than 5 second
    for record in lst_result:
        metadata = json.load(urlopen(apicallbase + record['panoid'] + '&key=' + mykey))
        year = (metadata['date'])[:4]
        month = (metadata['date'])[5:]
        results = results.append({'id': row['id'],
                                  'pt_lat': row['Y'],
                                  'pt_lng': row['X'],
                                  'pano_id': record['panoid'],
                                  'r_lat': record['lat'],
                                  'r_lng': record['lon'],
                                  'year': record['year'] if 'year' in record else year,
                                  'month': record['month'] if 'month' in record else month}, ignore_index=True)

results.to_csv(os.path.join(DATA_FOLDER, 'results_preston.csv'))