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
import numpy as np
import argparse

parser = argparse.ArgumentParser(description='Generate historic panoids')

# Required positional argument
parser.add_argument('input_file', type=str,
                    help='Input file')

parser.add_argument('-m', type=str,
                    help='Mode')

# Optional positional argument
parser.add_argument('-k', type=str,
                    help='API key')

parser.add_argument('-p', type=int,
                    help='Num cores')

# Optional argument
parser.add_argument('-t', type=int,
                    help='timeout seconds')



def panoids_with_timeout(lst_result, lat, lon):
    lst_result.extend(streetview.panoids(lat, lon))

DATA_FOLDER = '../data'
apicallbase = 'https://maps.googleapis.com/maps/api/streetview/metadata?&pano='
apikey = ''


results = []

pts = pd.read_csv(os.path.join(os.path.join(DATA_FOLDER, 'preston_PUA_random_points_2000.csv')))



class TimeOutException(Exception):
    def __init__(self, message, errors):
        super(TimeOutException, self).__init__(message)
        self.errors = errors

def signal_handler(signum, frame):
    raise TimeOutException("Timeout!", frame)

signal.signal(signal.SIGALRM, signal_handler)


def get_historic_panoids(res, apikey, timeout_s, filename):

    results = []
    for index, row in res.iterrows():
        lst_result = []

        signal.alarm(timeout_s) #Edit this to change the timeout seconds
        try:
            panoids_with_timeout(lst_result, row['Y'], row['X'])
        except TimeOutException as exc:
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

    if len(results) > 0:
        results = pd.DataFrame(results)

        results.to_csv(os.path.join(DATA_FOLDER, filename), index=False, header=True)




def get_month_and_year_from_api(res, apikey, file_name):
    for index, row in res.iterrows():
        if row['year'] == '' or row['month'] == '' or pd.isnull(row['year']) or pd.isnull(row['month']):
            i = 0
            while True:

                requesturl = apicallbase + row['pano_id'] + '&key=' + apikey
                if i != 0 :
                    print ("Timed out : " + apicallbase + row['pano_id'] + '&key=' + apikey)
                    i += 1
                try:
                    i -= 1
                    metadata = json.load(urlopen(requesturl))
                    i += 1
                    if 'date' in metadata:
                        res.loc[index, 'year'] = (metadata['date'])[:4]
                        res.loc[index, 'month'] = (metadata['date'])[-2:]
                    break
                except Exception:
                    continue
    res.to_csv(os.path.join(DATA_FOLDER, file_name), index= False, header=True)

def write_historic_panoids(inputfile, apikey, timeout_s, cores):
    results = pd.read_csv(os.path.join(DATA_FOLDER,  inputfile), index_col=None, header=0)
    i = 0
    lst_subfile = []
    procs = []
    for res in np.array_split(results, cores):
        lst_subfile.append(os.path.join(DATA_FOLDER, 'part_' + str(i) + '_' + os.path.basename(inputfile)))

        proc = mproc.Process(target=get_historic_panoids,
                             args=(res,
                                   apikey,
                                   timeout_s,
                                   os.path.join(DATA_FOLDER,
                                                'part_' + str(i) + '_' + os.path.basename(inputfile)),
                                   )
                             )
        procs.append(proc)
        proc.start()
        i += 1
    for proc in procs:
        proc.join()

    lst_result = []
    for file in lst_subfile:
        if os.path.isfile(file):
            try:
                result = pd.read_csv(file, index_col=None, header=0)
                lst_result.append(result)
            except pd.errors.EmptyDataError:
                continue
    result = pd.concat(lst_result)

    result.to_csv(os.path.join(DATA_FOLDER, 'panoids_' + os.path.basename(inputfile)), index=False, header=True)

    for file in lst_subfile:
        os.remove(file)

    fill_year_month(inputfile, apikey, cores)

def fill_year_month(inputfile, apikey, cores):
    results = pd.read_csv(os.path.join(DATA_FOLDER, 'panoids_' + os.path.basename(inputfile)), index_col=None, header=0)
    i = 0
    lst_subfile = []
    procs = []
    for res in np.array_split(results, cores):
        lst_subfile.append(os.path.join(DATA_FOLDER, 'part_' + str(i) + '_' + os.path.basename(inputfile)))

        if i not in [3,12,20,24,27]:
            proc = mproc.Process(target=get_month_and_year_from_api,
                                 args=(res,
                                       apikey,
                                       os.path.join(DATA_FOLDER,
                                                'part_' + str(i) + '_' + os.path.basename(inputfile)),
                                                 )
                                 )
            procs.append(proc)
            proc.start()
        i += 1
    for proc in procs:
        proc.join()

    lst_result = []
    for file in lst_subfile:
        if os.path.isfile(file):
            try:
                result = pd.read_csv(file, index_col=None, header=0)
                lst_result.append(result)
            except pd.errors.EmptyDataError:
                continue
    result = pd.concat(lst_result)


    result.to_csv(os.path.join(DATA_FOLDER, 'panoids_final_' + os.path.basename(inputfile)), header=True)

    for file in lst_subfile:
        os.remove(file)

def main(argv):
    apikey = ''
    inputfile = ''
    timeout_s = 10

    args = parser.parse_args()
    inputfile = os.path.join(DATA_FOLDER, args.input_file)
    apikey = args.k
    timeout_s = args.t
    mode = args.m
    cores = args.p
    if mode == 'full':
        write_historic_panoids(inputfile, apikey, timeout_s, cores)
    else:
        fill_year_month(inputfile, apikey, cores)

if __name__ == "__main__":
    main(sys.argv[1:])
