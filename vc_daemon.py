#!/usr/bin/env python3

import datetime
#import email
from imap_tools import MailBox, AND
import time
import urllib.request

from services import common
# from services import filemail
from services import responses

settings = common.get_config()

# process any pending jobs on startup
#responses.process( settings )

# watch the inbox for form submissions (or edits)
# imap host, username & password are stored externally as a json file.
print("imap host:", settings["host"])
print("imap email:", settings["user"])
mailbox = None
connected = False
while True:
    if not connected:
        mailbox = MailBox(settings["host"])
        mailbox.login(settings["user"], settings["password"])
        connected = True
    now = datetime.datetime.now()
    print("Checking for new mail notifications:",
          now.strftime("%Y-%m-%d %H:%M:%S"))
    try:
        mailbox.folder.set("INBOX")
        # messages = mailbox.fetch(AND(all=True), headers_only=True)
        # messages = mailbox.fetch(AND(seen=False), headers_only=True)
        messages = mailbox.fetch(AND(seen=False))
    except:
        print("imap connection dropped, or fetch failed...")
        connected = False
    if connected:
        form_notification = False
        for msg in messages:
            print(msg.from_)
            print(msg.subject)
            if "Virtual Choir" in msg.subject:
                form_notification = True
        if form_notification:
            print("new google form work ...")
            responses.fetch( settings["responses"] )
            responses.process( settings )
        
    # subjects = [msg.subject for msg in mailbox.fetch(AND(all=True))]
    print("  sleeping", settings["interval"], "seconds ...")
    time.sleep(settings["interval"])
