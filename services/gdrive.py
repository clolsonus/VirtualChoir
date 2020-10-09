#!/usr/bin/env python3

import argparse
import json
import lxml.etree as ET
import os

import common

parser = argparse.ArgumentParser(description='google folder list')
parser.add_argument('url', help='google drive folder ulr')
args = parser.parse_args()

html = common.urlread(args.url, progress=False)
#print("RAW HTML:", html)

parsed_html = ET.HTML(html)
#print(parsed_html)

def traverse(node, indent=""):
    if len(node):
        # parent
        print(indent, "parent:", node.tag)
        for child in node:
            traverse(child, indent + "  ")
    else:
        # leaf
        print(indent, "leaf:", node.tag, node.text)

body = parsed_html.find("body")
#traverse(parsed_html.find("head"))

scripts = body.findall("script")
# print( len(scripts) )
marker = "window['_DRIVE_ivd'] = '"
for script in scripts:
    if script.text and script.text.startswith(marker):
        print("YAS SCRIPT:", script.tag)
        text = script.text[len(marker):]
        head, sep, tail = text.partition("'")
        #print(type(script.text), head)
        decoded_head = head.encode('utf8').decode('unicode_escape')
        #print(decoded_head)
        full_list = json.loads(decoded_head)
        #print(full_list)
        
print("DECODING:")
dir_list = full_list[0]
print(len(dir_list))
for i, entry in enumerate(dir_list):
    print(i, entry)
    print("  google name:", entry[0])
    print("  parent:", entry[1][0])
    print("  pretty name:", entry[2])
    print("  type:", entry[3])
    print("  adate:", entry[9])
    print("  mdate:", entry[10])
    print("  size:", entry[13])
    url = "https://drive.google.com/uc?export=download&id=%s" % entry[0]
    print("  download url:", url)
    if entry[2].endswith(".m4a"):
        if os.path.exists(entry[2]):
            statinfo = os.stat(entry[2])
            mtime = statinfo.st_mtime
            if entry[10]/1000 <= mtime:
                print("Skipping, already downloaded")
                continue
        print("Downloading:", url)
        print("Saving as:", entry[2])
        html = common.urlread(url)
        with open(entry[2], 'wb') as f:
            f.write(html)
            f.close()
        os.utime(entry[2], times=(entry[9]/1000, entry[10]/1000))
