#!/usr/bin/env python3

import argparse
import json
import lxml.etree as ET
import urllib.request

parser = argparse.ArgumentParser(description='google folder list')
parser.add_argument('url', help='google drive folder ulr')
args = parser.parse_args()


with urllib.request.urlopen(args.url) as response:
   html = response.read()

#print(html)

print("parse...")

parsed_html = ET.HTML(html)
print(parsed_html)

# def traverse(node, indent=""):
#     if len(node):
#         # parent
#         print(indent, "parent:", node.tag)
#         for child in node:
#             traverse(child, indent + "  ")
#     else:
#         # leaf
#         print(indent, "leaf:", node.tag, node.text)

body = parsed_html.find("body")
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
        #print(dir_json)
        
print("DECODING:")
dir_list = full_list[0]
print(len(dir_list))
for i, entry in enumerate(dir_list):
    print(i, entry)
    print("  google name:", entry[0])
    print("  parent:", entry[1][0])
    print("  pretty name:", entry[2])
    print("  type:", entry[3])
    print("  mdate:", entry[9])
    print("  cdate:", entry[10])
    print("  size:", entry[13])
