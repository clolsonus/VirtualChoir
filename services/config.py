# config file management

import json
import os

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

