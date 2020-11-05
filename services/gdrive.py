#!/usr/bin/env python3

import argparse
from datetime import datetime
import io
import os
import pickle
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
    SCOPES = ['https://www.googleapis.com/auth/drive']

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
        print('folder_id:', folder_id)
        return folder_id

    def fix_extension(self, name, mimeType):
        basename, ext = os.path.splitext(name)
        print("fix_extension:", basename, ":", ext)
        if len(ext):
            return name
        else:
            print("Need to fix extension:", name)
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
                ext = "totally_unknown"
            return basename + "." + ext
            
    def sync_folder(self, url, subpath=None):
        folder_id = self.get_folder_id(url)
        
        project_dir = os.path.join(common.vcdir, "projects")
        # create if needed
        if not os.path.exists(project_dir):
            print("Creating:", project_dir)
            os.makedirs(project_dir)

        # Get shared folder details
        print("folder id:", folder_id)
        try:
            results = self.service.files().get(fileId=folder_id, fields='*').execute()
        except:
            print("Folder not found, check path and check it is shared outside your organization")
            return False
        print("results:", results)
        if "name" in results and not self.folder_name:
            self.folder_name = results["name"]
        else:
            self.folder_name = folder_id
        
        # Call the Drive v3 API
        results = self.service.files().list(
            q="'" + folder_id + "' in parents",
            pageSize=100,
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
        # create if needed
        if not os.path.exists(work_dir):
            print("Creating:", work_dir)
            os.makedirs(work_dir)

        for item in items:
            if item['trashed']:
                continue

            print(item)
            dt = datetime.strptime(item['createdTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            created = time.mktime(dt.timetuple())
            dt = datetime.strptime(item['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            modified = time.mktime(dt.timetuple())
            print("ts:", created, modified)                                   

            if item['mimeType'].endswith("folder"):
                # recurse folders
                newurl = "https://drive.google.com/drive/folders/" + item['id']
                newpath = os.path.join(work_dir, item['name'])
                self.sync_folder(newurl, newpath)
            else:
                # fetch file
                name = self.fix_extension(item['name'], item['mimeType'])
                dest_file = os.path.join(work_dir, name)
                if os.path.exists(dest_file):
                    statinfo = os.stat(dest_file)
                    mtime = statinfo.st_mtime
                    if modified <= mtime or item['size'] != statinfo.st_size:
                        print("Skipping, already downloaded")
                        continue
                print("Downloading to:", dest_file)
                request = self.service.files().get_media(fileId=item['id'])
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    print("Download %d%%." % int(status.progress() * 100))
                print("downloaded bytes:", len(fh.getvalue()))
                with open(dest_file, 'wb') as f:
                    f.write(fh.getvalue())
                    f.close()
                os.utime(dest_file, times=(created, modified))
        return True
