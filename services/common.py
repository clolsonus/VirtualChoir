# common support routins

import io
import json
import os
from tqdm import tqdm
import urllib.request

homedir = os.path.expanduser("~")
vcdir = os.path.join(homedir, "VirtualChoir")
config_file = os.path.join(vcdir, "config.json")

def init_vc_dir():
    # create if needed
    if not os.path.exists(vcdir):
        print("Creating:", vcdir)
        os.makedirs(vcdir)

def make_dummy_config():
    init_vc_dir()
    dummy = { "host": "your.imap.server.com",
              "user": "your imap email @ address",
              "password": "your imap password in clear text",
              "interval": 30,
              "responses": "https://docs.google.com/spreadsheets/d/$document_id_string$/export?format=csv"
             }
    with open(config_file, "w") as fp:
        json.dump(dummy, fp, indent=4)
    print("Creating a default config file:", config_file)
    print("Please edit this config file for your notification imap account.")
          
def get_config():
    init_vc_dir()
    if not os.path.exists(config_file):
        make_dummy_config()
        quit()
    with open(config_file, "r") as fp:
        config = json.load(fp)
    if config["host"] == "your.imap.server.com":
        print("Please configure your Virtual Choir setup:", config_file)
        quit()
    return config

# fetch a url with progress
def urlread(url, progress=True):
    with urllib.request.urlopen(url) as response:
        # replaces: html = response.read()
        length = response.getheader('content-length')
        if length:
            length = int(length)
            blocksize = max(4096, length//100)
        else:
            progress = False
            blocksize = 1000000 # just made something up

        print(length, blocksize)

        if progress:
            pbar = tqdm(total=length)
        buf = io.BytesIO()
        size = 0
        while True:
            buf1 = response.read(blocksize)
            if not buf1:
                break
            buf.write(buf1)
            size += len(buf1)
            if progress:
                pbar.update(blocksize)
        if progress:
            pbar.close()
        html = buf.getvalue()
    return html
