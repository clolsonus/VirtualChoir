#!/usr/bin/env python3

import argparse
import json
import lxml.etree as ET
import os

from . import common

def my_xml_traverse(node, indent=""):
    if len(node):
        # parent
        print(indent, "parent:", node.tag)
        for child in node:
            traverse(child, indent + "  ")
    else:
        # leaf
        print(indent, "leaf:", node.tag, node.text)
        
def sync_folder(url, subpath=None):
    tmp1 = url.split('/')
    tmp2 = tmp1[-1].split('?')
    folder_id = tmp2[0]
    print('folder_id:', folder_id)

    project_dir = os.path.join(common.vcdir, "projects")
    # create if needed
    if not os.path.exists(project_dir):
        print("Creating:", project_dir)
        os.makedirs(project_dir)

    html = common.urlread(url, progress=False)
    #print("RAW HTML:", html)

    parsed_html = ET.HTML(html)
    #print(parsed_html)

    body = parsed_html.find("body")
    #my_xml_traverse(parsed_html.find("head"))

    scripts = body.findall("script")
    # print( len(scripts) )
    marker = "window['_DRIVE_ivd'] = '"
    full_list = []
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

    if not full_list:
        # no luck finding a directory listing
        return
    
    # work_dir
    if subpath:
        work_dir = subpath
    else:
        work_dir = os.path.join(project_dir, folder_id)
    # create if needed
    if not os.path.exists(work_dir):
        print("Creating:", work_dir)
        os.makedirs(work_dir)

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
        if entry[3].endswith("folder"):
            # recurse folders
            newurl = "https://drive.google.com/drive/folders/" + entry[0]
            newpath = os.path.join(work_dir, entry[2])
            sync_folder(newurl, newpath)
        else:
            # fetch file
            url = "https://drive.google.com/uc?export=download&id=%s" % entry[0]
            print("  download url:", url)
            dest_file = os.path.join(work_dir, entry[2])
            if True or dest_file.endswith(".m4a"):
                if os.path.exists(dest_file):
                    statinfo = os.stat(dest_file)
                    mtime = statinfo.st_mtime
                    if entry[10]/1000 <= mtime:
                        print("Skipping, already downloaded")
                        continue
                print("Downloading:", url)
                print("Saving as:", dest_file)
                html = common.urlread(url)
                with open(dest_file, 'wb') as f:
                    f.write(html)
                    f.close()
                os.utime(dest_file, times=(entry[9]/1000, entry[10]/1000))
