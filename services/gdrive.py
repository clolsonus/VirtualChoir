#!/usr/bin/env python3

from datetime import datetime
from dateutil import parser
import io
import os
import pickle
import sys
import time

# great info here, including setting yourself up with a credentials.json file:
# https://developers.google.com/drive/api/v3/quickstart/python

# pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload

from . import common

class gdrive():
    # If modifying these scopes, delete the file token.pickle.
    #SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']
    #SCOPES = ['https://www.googleapis.com/auth/drive']
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

    def __init__(self):
        self.folder_name = None
        
        creds = None
        # The file token.pickle stores the user's access and refresh
        # tokens, and is created automatically when the authorization
        # flow completes for the first time.
        tp_file = os.path.join(common.vcdir, "token.pickle")
        if os.path.exists(tp_file):
            with open(tp_file, 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                creds_file = os.path.join(common.vcdir, "credentials.json")
                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(tp_file, 'wb') as token:
                pickle.dump(creds, token)
        self.service = build('drive', 'v3', credentials=creds)

    def get_folder_id(self, url):
        tmp1 = url.split('/')
        parts = tmp1[-1].split('?')
        folder_id = None
        for p in parts:
            if p.startswith("usp=") or p == "folderview":
                pass
            elif p.startswith("id="):
                folder_id = p[3:]
                break
            else:
                folder_id = p
                break
        print('folder id (parsed from url):', folder_id)
        return folder_id

    def fix_extension(self, name, mimeType):
        basename, ext = os.path.splitext(name)
        if len(ext):
            return name
        else:
            # add an extension based on mimeType
            if mimeType.startswith("audio/"):
                ext = mimeType[6:]
                if ext.startswith("x-"):
                    ext = ext[2:]
                elif ext == "mpeg":
                    # rewrite this as an unambiguous audio extension
                    ext = "mp3"
                if len(ext) < 2:
                    # fall back guess, sorry
                    ext = "mp3"
            elif mimeType.startswith("video/"):
                ext = mimeType[6:]
                if ext == "quicktime":
                    ext = "mov"
                if len(ext) < 2:
                    # fall back guess, sorry
                    ext = "mp4"
            else:
                return name
            print("Fix file extension:", name, "adding:", ext)
            return basename + "." + ext
            
    def sync_folder(self, url, subpath=None):
        folder_id = self.get_folder_id(url)
        
        project_dir = os.path.join(common.vcdir, "projects")
        # create if needed
        if not os.path.exists(project_dir):
            print("Creating:", project_dir)
            os.makedirs(project_dir)

        # Get shared folder details
        try:
            results = self.service.files().get(fileId=folder_id, supportsAllDrives=True, fields='*').execute()
        except:
            print("Unexpected error:", sys.exc_info())
            print("Folder not found, check path and check it is shared outside your organization")
            return False
        # print("results:", results)
        if "name" in results and not self.folder_name:
            self.folder_name = results["name"]
        else:
            self.folder_name = folder_id
        print("Found folder name:", self.folder_name)
        
        # Call the Drive v3 API
        results = self.service.files().list(
            q="'" + folder_id + "' in parents",
            pageSize=1000,
            fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, size, trashed)").execute()
        items = results.get('files', [])
        if not items:
            print('No files found.')
            return False

        # work_dir
        if subpath:
            work_dir = subpath
        else:
            work_dir = os.path.join(project_dir, folder_id)
        # create new folder if needed
        if not os.path.exists(work_dir):
            print("Creating:", work_dir)
            os.makedirs(work_dir)

        # find/remove existing files that no longer exist on the remote side
        remote_names = []
        for item in items:
            if not item['trashed']:
                 name = self.fix_extension(item['name'], item['mimeType'])
                 remote_names.append(name)
        for file in sorted(os.listdir(work_dir)):
            basename, ext = os.path.splitext(file)
            # protect some files
            if file == "cache" or file == "results":
                print("INFO: Preserving local work directory:", file)
            elif ext == ".lof":
                print("INFO: Preserving local .lof file:", file)
            elif ext == ".txt":
                # maybe I created a hints.txt locally that I'd like to
                # preserve
                print("INFO: Preserving local file:", file)
            elif ext == ".aup" or (file.endswith("_data") and os.path.isdir(os.path.join(work_dir, file))):
                print("INFO: Preserving audacity project:", file)
            elif not file in remote_names:
                trashed_file = os.path.join(work_dir, file)
                print("NOTICE: deleting local file:", trashed_file)
                os.unlink(trashed_file)

        # download / update folder items and recurse to subfolders
        for item in items:
            if item['trashed']:
                continue

            print(item)
            #dt = datetime.strptime(item['createdTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            # created = time.mktime(dt.timetuple())
            dt = parser.isoparse(item['createdTime'])
            created = dt.timestamp()
            # dt = datetime.strptime(item['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            #modified = time.mktime(dt.timetuple())
            dt = parser.isoparse(item['modifiedTime'])
            modified = dt.timestamp()
            print("  ts:", created, modified)                                   

            if item['mimeType'].endswith("folder"):
                # recurse folders
                newurl = "https://drive.google.com/drive/folders/" + item['id']
                newpath = os.path.join(work_dir, item['name'])
                self.sync_folder(newurl, newpath)
            elif item["mimeType"].endswith("shortcut"):
                print("Shortcut encountered, don't know how to deal with this file:", item["name"])
            elif "google-apps." in item["mimeType"]:
                print("skipping google app file")
            else:
                # fetch file
                print("%s (%s) %.0f Kb" % (item["name"], item["mimeType"], int(item["size"]) / 1024 ))
                name = self.fix_extension(item['name'], item['mimeType'])
                dest_file = os.path.join(work_dir, name)
                if os.path.exists(dest_file):
                    statinfo = os.stat(dest_file)
                    mtime = statinfo.st_mtime
                    if modified <= mtime or item['size'] != statinfo.st_size:
                        print("  Skipping, already downloaded")
                        continue
                print("  Downloading to:", dest_file)
                request = self.service.files().get_media(fileId=item['id'])
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    print("  Download %d%%." % int(status.progress() * 100))
                print("  downloaded bytes:", len(fh.getvalue()))
                with open(dest_file, 'wb') as f:
                    f.write(fh.getvalue())
                    f.close()
                os.utime(dest_file, times=(created, modified))
        return True
