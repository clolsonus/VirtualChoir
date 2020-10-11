import csv
from datetime import datetime
import json
import os
import time

from . import common
from . import gdrive

def fetch( response_url ):
    csv_data = common.urlread(response_url)
    print(str(csv_data).encode('utf8').decode('unicode_escape'))
    # x = csv.reader(csv_data)
    # for row in x:
    #     print("row:", row)
    csvfile = os.path.join(common.vcdir, "responses.csv")
    with open(csvfile, 'wb') as f:
        f.write(csv_data)
        f.close()

def process():
    last_time = get_last_time()
    new_time = 0
    dirty = False
    csvfile = os.path.join(common.vcdir, "responses.csv")
    with open(csvfile, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            timestamp = row['Timestamp']
            dt = datetime.strptime(timestamp, '%m/%d/%Y %H:%M:%S')
            ts = time.mktime(dt.timetuple())
            print("row:", ts, row)
            if ts > last_time:
                dirty = True
                if ts > new_time:
                    new_time = ts
                run_job(row)
    if dirty:
        save_last_time(new_time)        

def run_job(request):
    # extract google folder id
    url = request['Public google drive folder share link']
    gdrive.sync_folder(url)

# read the saved time
def get_last_time():
    last_time = 0
    last_file = os.path.join(common.vcdir, "last_time.json")
    if os.path.exists(last_file):
        with open(last_file, "r") as fp:
            data = json.load(fp)
            last_time = data["last_time"]
    print("last processed request at time:", last_time)
    return last_time

# update the saved time
def save_last_time(last_time):
    print("updating last processed request time:", last_time)
    data = { "last_time": last_time }
    last_file = os.path.join(common.vcdir, "last_time.json")
    print(data)
    with open(last_file, "w") as fp:
        json.dump(data, fp, indent=4)
