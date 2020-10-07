#!/usr/bin/env python3

import imaplib
import json
import os

# store username & password externally as a json file.
homedir = os.path.expanduser("~")
dotfile = os.path.join(homedir, ".virtualchoir.json")
with open(dotfile, "r") as fp:
    config = json.load(fp)

mail = imaplib.IMAP4_SSL('imap.gmail.com') 
mail.login(config["user"], config["password"])
mail.select()
typ, data = mail.search(None, 'ALL') 
for num in data[0].split(): 
    typ, data = mail.fetch(num, '(RFC822)') 
    print('Message %s\n%s\n' % (num, data[0][1])) 
mail.close() 
mail.logout()
