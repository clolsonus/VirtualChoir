#!/usr/bin/env python3

import datetime
#import email
from imap_tools import MailBox, AND
import time
import urllib.request

import common

settings = common.get_config()

def fetch_csv_response():
    
# watch the inbox for form submissions (or edits)
# imap host, username & password are stored externally as a json file.
print("imap host:", settings["host"])
print("imap email:", settings["user"])
mailbox = MailBox(settings["host"])
mailbox.login(settings["user"], settings["password"])
while True:
    now = datetime.datetime.now()
    print("Checking for new mail notifications:",
          now.strftime("%Y-%m-%d %H:%M:%S"))
    mailbox.folder.set("INBOX")
    # messages = mailbox.fetch(AND(all=True))
    messages = mailbox.fetch(AND(seen=False), headers_only=True)
    for msg in messages:
        print(msg.subject)
    # subjects = [msg.subject for msg in mailbox.fetch(AND(all=True))]
    print("  sleeping", settings["interval"], "seconds ...")
    time.sleep(settings["interval"])
