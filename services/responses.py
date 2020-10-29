import csv
from datetime import datetime
import json
import os
import subprocess
import time
from zipfile import ZipFile

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

def process( settings ):
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
                run_job(settings, row)
    if dirty:
        save_last_time(new_time)        

def run_job(settings, request):
    # sync the shared google drive folder (create a local copy)
    url = request['Public google drive folder share link']
    gd = gdrive.gdrive()
    if "google.com" in url:
        gd.sync_folder(url)
    else:
        print("this doesn't look like a google drive url.")
        print("aborting...")
        return

    # paths management
    folder_id = gd.get_folder_id(url)
    work_dir = os.path.join(common.vcdir, "projects", folder_id)
    results_dir = os.path.join(work_dir, "results")
    if not os.path.exists(results_dir):
        print("Creating:", results_dir)
        os.makedirs(results_dir)
    
    audio_only = False
    aligned_audio = False
    command = [ "./sync-tracks.py", work_dir ]
    if request['Synchronization Strategy'] == "Claps":
        command.append( "--sync" )
        command.append( "clap" )
    if len(request['Additional Options']):
        options = request['Additional Options'].split(", ")
        for o in options:
            if o.startswith("Mute videos"):
                command.append("--mute-videos")
            elif o.startswith("Generate time aligned individual audio tracks"):
                aligned_audio = True
                command.append("--write-aligned-audio")
            elif o.startswith("Only audio"):
                audio_only = True
                command.append("--no-video")
    print("Running command:", command)
    result = subprocess.run(command)
    if result.returncode != 0:
        print("Something failed processing the job.")
        return

    if False:
        # zip the results
        zip_file = os.path.join(work_dir, gd.folder_name + ".zip")
        result_files = [ "mixed_audio.mp3",
                         "gridded_video.mp4",
                         "audacity_import.lof" ]
        with ZipFile(zip_file, "w") as zip:
            for file in result_files:
                print("  adding:", file)
                full_name = os.path.join(work_dir, file)
                if os.path.exists(full_name):
                    zip.write(full_name, arcname=file)

    # generate list of files
    send_files = []
    for file in sorted(os.listdir(results_dir)):
        if not aligned_audio and file.startswith("aligned_"):
            pass
        elif file == "silent_video.mp4":
            pass
        elif audio_only and file == "gridded_video.mp4":
            pass
        else:
            send_files.append( os.path.join(results_dir, file) )
    print("sending files:", send_files)
    # send the results
    command = [ "./FilemailCli",
                "--username=%s" % settings["filemail_email"],
                "--userpassword=%s" % settings["filemail_password"],
                "--files=%s" % ",".join(send_files),
                "--to=%s" % request["Email Address"],
                "--from=noreply-virtualchoir@flightgear.org",
                "--subject='Your virtual choir song: " + gd.folder_name + " is ready!'",
                "--days=7",
                "--verbose=true" ]
    print("Running command:", command)
    result = subprocess.run(command)
    if result.returncode != 0:
        print("Something failed sending the results.")
        return

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
