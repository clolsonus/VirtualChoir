#!/usr/bin/env python3

import email
from email.parser import Parser
from email.policy import default
import imaplib
import json
import os
import time

# username & password are stored externally as a json file.
homedir = os.path.expanduser("~")
dotfile = os.path.join(homedir, ".virtualchoir.json")
if os.path.exists(dotfile):
    with open(dotfile, "r") as fp:
        config = json.load(fp)
else:
    config = { "host": "your.imap.server.com",
               "user": "your imap email @ address",
               "password": "your imap password in clear text" }
    with open(dotfile, "w") as fp:
        json.dump(config, fp, indent=4)
    print("Creating a default config file:", dotfile)
    print("Please edit this config file for your notification imap account.")
    quit()


if False:
    # fetch all message and dump them out
    mail = imaplib.IMAP4_SSL(config["host"])
    mail.login(config["user"], config["password"])
    mail.select()
    typ, data = mail.search(None, 'ALL') 
    for num in data[0].split(): 
        typ, data = mail.fetch(num, '(RFC822)') 
        print('Message %s\n%s\n' % (num, data[0][1])) 
    mail.close() 
    mail.logout()

# snippet of code to detect new messages and mark them seen

mail = imaplib.IMAP4_SSL(config["host"])
(retcode, capabilities) = mail.login(config["user"], config["password"])
#mail.list()

while True:
    n=0
    mail.select()
    (retcode, messages) = mail.search(None, 'ALL') # testing
    #(retcode, messages) = mail.search(None, '(UNSEEN)')
    if retcode == 'OK':
       for num in messages[0].split():
          print('Processing:', n)
          n += 1
          typ, data = mail.fetch(num,'(RFC822)')
          for response_part in data:
              #print(response_part)
              if isinstance(response_part, tuple):
                  # headers = email.message_from_string(str(response_part[1]))
                  # headers = Parser(policy=default).parsestr(response_part[1].encode('utf8').decode('unicode_escape'))
                  headers = Parser(policy=default).parsestr(str(response_part[1]))
                  #print(headers['From'])
                  #print(headers['Subject'])
                  print("headers:", headers)
                  # not needed with gmail
                  # typ, data = mail.store(num,'+FLAGS','\\Seen')

    print(n)

    print("sleeping 30 seconds ...")
    time.sleep(30)
