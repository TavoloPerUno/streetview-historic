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
import getopt

def panoids_with_timeout(lst_result, lat, lon):
    lst_result.extend(streetview.panoids(lat, lon))

DATA_FOLDER = '../data'
apicallbase = 'https://maps.googleapis.com/maps/api/streetview/metadata?&pano='
apikey = 'AIzaSyDiyJQYyVPaQ_GAamLY_AXmLiJBDo0Lyk4'


results = []

pts = pd.read_csv(os.path.join(os.path.join(DATA_FOLDER, 'preston_PUA_random_points_2000.csv')))



class TimeOutException(Exception):
    def __init__(self, message, errors):
        super(TimeOutException, self).__init__(message)
        self.errors = errors

def signal_handler(signum, frame):
    raise TimeOutException("Timeout!")


def write_historic_panoids(input_file, apikey, timeout_s):
    pts = pd.read_csv(input_file)
    results = []
    for index, row in pts.iterrows():
        lst_result = []

        signal.alarm(timeout_s) #Edit this to change the timeout seconds
        try:
            panoids_with_timeout(lst_result, row['Y'], row['X'])
        except TimeOutException:
            continue
        signal.alarm(0)
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
    try:
        opts, args = getopt.getopt(argv, "hi:k::t", ["ifile=", "ofile=", "timeout="])
    except getopt.GetoptError:
        print 'test.py -i <inputfile> -o <outputfile>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'timeout_with_alarm.py -i <inputfile> -k <google api key>'
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputfile = os.path.join(DATA_FOLDER, arg)
        elif opt in ("-k", "--apikey"):
            apikey = arg
        elif opt in ("-t", "--timeout"):
            timeout_s = arg
    write_historic_panoids(inputfile, apikey, timeout_s)

if __name__ == "__main__":
    main(sys.argv[1:])
