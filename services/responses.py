import csv
from datetime import datetime
import json
import os
import subprocess
import tempfile
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
            print("row:", row)
            timestamp = row['Timestamp']
            dt = datetime.strptime(timestamp, '%m/%d/%Y %H:%M:%S')
            ts = time.mktime(dt.timetuple())
            print("row:", ts, row)
            if ts > last_time:
                dirty = True
                if ts > new_time:
                    new_time = ts
                result = run_job(settings, row)
                if not result:
                    print("Error processing job, sorry ...")
    if dirty:
        save_last_time(new_time)        

def send_results(settings, request, subject, file_list):
    # send the results
    command = [ "./bin/FilemailCli",
                "--username=%s" % settings["filemail_email"],
                "--userpassword=%s" % settings["filemail_password"],
                "--files=%s" % ",".join(file_list),
                "--to=%s" % request["Email Address"],
                "--from=noreply-virtualchoir@flightgear.org",
                "--subject=%s" % subject,
                "--days=7",
                "--verbose=true" ]
    print("Running command:", command)
    result = subprocess.run(command)
    if result.returncode != 0:
        print("Something failed sending the results.")
        return False
    return True
    
# return a folder sync error
def gen_sync_error(settings, request):
    (fd, name) = tempfile.mkstemp(suffix=".txt", prefix="error-report-")
    with os.fdopen(fd, 'w') as tmp:
        tmp.write("Virtual Choir Maker ran into a problem with your request.\n")
        tmp.write("We could not sync the shared google folder you listed:\n")
        tmp.write("\n")
        tmp.write("    " + request['Public google drive folder share link'] + "\n")
        tmp.write("\n")
        tmp.write("Please check that you created a shared link to this folder\n")
        tmp.write("and that you shared the folder outside your organization (if applicable.)\n")
        tmp.write("\n")
        tmp.write("Then go ahead and resubmit your request.\n")
        tmp.write("\n")
    subject = "'Your virtual choir maker request ran into a problem.  Please download the error report for more details.'"
    result = send_results(settings, request, subject, [name])
    os.unlink(name)
    if not result:
        return False
    return True

def gen_form_error(settings, request):
    (fd, name) = tempfile.mkstemp(suffix=".txt", prefix="error-report-")
    with os.fdopen(fd, 'w') as tmp:
        tmp.write("Virtual Choir Maker ran into a problem with your request.\n")
        tmp.write("The google folder link you shared does not appear to be a valid google drive link:\n")
        tmp.write("\n")
        tmp.write("    " + request['Public google drive folder share link'] + "\n")
        tmp.write("\n")
        tmp.write("Please check that you created a shared link to this folder\n")
        tmp.write("and that you shared the folder outside your organization (if applicable.)\n")
        tmp.write("Please double check you have copied the link correctly.\n")
        tmp.write("\n")
        tmp.write("Then go ahead and resubmit your request.\n")
        tmp.write("\n")
    subject = "'Your virtual choir maker request ran into a problem.  Please download the error report for more details.'"
    result = send_results(settings, request, subject, [name])
    os.unlink(name)
    if not result:
        return False
    return True

def run_job(settings, request):
    # sync the shared google drive folder (create a local copy)
    url = request['Public google drive folder share link']
    if not "google.com" in url:
        print("this doesn't look like a google drive url.")
        print("aborting...")
        gen_form_error(settings, request)
        return False
    
    gd = gdrive.gdrive()
    result = gd.sync_folder(url)
    if not result:
        print("sync failed, permissions or url?")
        gen_sync_error(settings, request)
        return False

    # paths management
    folder_id = gd.get_folder_id(url)
    work_dir = os.path.join(common.vcdir, "projects", folder_id)
    results_dir = os.path.join(work_dir, "results")
    if not os.path.exists(results_dir):
        print("Creating:", results_dir)
        os.makedirs(results_dir)
    
    audio_only = False
    aligned_tracks = False
    command = [ "./sync-tracks.py", work_dir ]
    if request['Synchronization Strategy'] == "Claps":
        command.append( "--sync" )
        command.append( "clap" )
    if len(request['Additional Options']):
        options = request['Additional Options'].split(", ")
        for o in options:
            if o.lower().startswith("only audio"):
                audio_only = True
                command.append("--no-video")
            elif o.lower().startswith("suppress noise"):
                command.append("--suppress-noise")
            elif o.lower().startswith("mute videos"):
                command.append("--mute-videos")
            elif o.lower().startswith("make individual time aligned tracks"):
                aligned_tracks = True
                command.append("--write-aligned-tracks")
    print("Running command:", command)
    result = subprocess.run(command)
    if result.returncode != 0:
        print("Something failed processing the job.")
        return False

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
    file_list = []
    for file in sorted(os.listdir(results_dir)):
        if not aligned_tracks and file.startswith("aligned_"):
            pass
        elif file == "silent_video.mp4":
            pass
        elif audio_only and file == "gridded_video.mp4":
            pass
        else:
            file_list.append( os.path.join(results_dir, file) )
    print("sending files:", file_list)
    if "Song Name" in request and len(request["Song Name"]):
        song_name = request["Song Name"]
    else:
        song_name = gd.folder_name
    subject = "'Your virtual choir song: " + song_name + " is ready!'"
    result = send_results(settings, request, subject, file_list)
    if not result:
        return False
    
    # all good if we made it here
    print("Success!")
    return True

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
