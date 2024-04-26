import argparse
import os
import os.path as osp
import sys
import logging
import pdb

import pathlib as Path

import json
import time
import pprint
import hashlib

LABEL_ATTR_LOOKUP = {}

def init_via_data():
    return {}

def populate_header(d,p):
#     "project": {                       # ["project"] contains all metadata associated with this VIA project
#     "pid": "__VIA_PROJECT_ID__",     # uniquely identifies a shared project (DO NOT CHANGE)
#     "rev": "__VIA_PROJECT_REV_ID__", # project version number starting form 1 (DO NOT CHANGE)
#     "rev_timestamp": "__VIA_PROJECT_REV_TIMESTAMP__", # commit timestamp for last revision (DO NOT CHANGE)
#     "pname": "VIA3 Sample Project",  # Descriptive name of VIA project (shown in top left corner of VIA application)
#     "creator": "VGG Image Annotator (http://www.robots.ox.ac.uk/~vgg/software/via)",
#     "created": 1588343615019,        # timestamp recording the creation date/time of this project (not important)
#     "vid_list": ["1", "2"]           # selects the views that are visible to the user for manual annotation (see ["view"])
#   },
    d['project'] = {}
    d['project']['pid'] = "__VIA_PROJECT_ID__"
    d['project']['rev'] = "__VIA_PROJECT_REV_ID__"
    d['project']['rev_timestamp'] = "__VIA_PROJECT_REV_TIMESTAMP__"
    d['project']['pname'] = "PHAR export project"
    d['project']['creator'] = "VGG Image Annotator (http://www.robots.ox.ac.uk/~vgg/software/via)" # Lies
    d['project']['created'] = 1000 # Dummy value
    d['project']['vid_list'] =  ["1"]

def populate_config(d,a):
    d['config'] = {
        "file": {
            "loc_prefix": {   # a prefix automatically appended to each file 'src' attribute. Leave it blank if you don't understand it. See https://gitlab.com/vgg/via/-/blob/master/via-3.x.y/src/js/_via_file.js
                "1": "",        # appended to files added using browser's file selector (NOT USED YET)
                "2": "",        # appended to remote files (e.g. http://images.google.com/...)
                "3": "",        # appended to local files  (e.g. /home/tlm/data/videos)
                "4": ""         # appended to files added as inline (NOT USED YET)
            }
        },
        "ui": {
            "file_content_align": "center",
            "file_metadata_editor_visible": True,
            "spatial_metadata_editor_visible": True,
            "spatial_region_label_attribute_id": ""
        }
    }

def populate_attributes(d,p,a):
    with open(a.ann) as file:
        labels = [line.rstrip() for line in file]
    # Create one attribute with all labels as options
    d["attribute"] = {       # defines the things that a human annotator will describe and define for images, audio and video.
        "1" : {                          # attribute-id (unique)
            "aname" : "PHAR-HC",           # attribute name (shown to the user)
            "anchor_id":"FILE1_Z2_XY0",   # FILE1_Z2_XY0 denotes that this attribute define a temporal segment of a video file. See https://gitlab.com/vgg/via/-/blob/master/via-3.x.y/src/js/_via_attribute.js
            "type":4,                     # attributes's user input type ('TEXT':1, 'CHECKBOX':2, 'RADIO':3, 'SELECT':4, 'IMAGE':5 )
            "desc":"Activity",            # (NOT USED YET)
             # defines KEY:VALUE pairs and VALUE is shown as options of dropdown menu or radio button list
            "options":{}, # To populate, below
            "default_option_id":""
        }
    }
    for i in range(0, len(labels)):
        d["attribute"]["1"]["options"][str(i+1)] = labels[i]
        LABEL_ATTR_LOOKUP[labels[i]] = str(i+1)

def populate_files(d,p):
    filepath = p["video_input"]
    basename = osp.basename(filepath)
    d["file"] = {                         # define the files (image, audio, video) used in this project
        "1" : {                           # unique file identifier
            "fid" : 1,                    # unique file identifier (same as above)
            "fname": basename,            # file name (shown to the user, no other use)
            "type":4,                     # file type { IMAGE:2, VIDEO:4, AUDIO:8 }
            "loc":1,                      # file location { LOCAL:1, URIHTTP:2, URIFILE:3, INLINE:4 }
            "src":""                      # file content is fetched from this location (VERY IMPORTANT)
        }
    }

def populate_views(d):
    d['view'] = {
        "1": {            # unique view identifier
          "fid_list":[1]  # this view shows a single file with file-id of 1 (which is the Alioli.ogv video file)
        },
    }

def populate_metadata(d,p):
    d["metadata"] = {}

    # First determine the duration of the video. We didn't store this directly, so determine it from the names of the keys of the
    vid_duration = max([ int(t) for t in [ osp.splitext(osp.basename(clip))[0].split('_')[2] for clip in p['raw_predictions'].keys() ] if '.' not in t ])

    # Next determine clip length. Use round here, not int division.
    num_clips = len(p["weighted_results"])
    clip_length = round(vid_duration / num_clips)

    # Determine the top-ranked activity in each clip.
    # Each is a hash mapping confidence to label.
    # TODO - add a threshold (but must preserve space in list)
    clip_results = [ r[list(r)[0]] for r in p["weighted_results"] ]


    logging.debug("About to pop metadata, have lookup attrs as " + pprint.pformat(LABEL_ATTR_LOOKUP))

    # For each entry in weighted_results, inject a metadata entry with attribute "1" and option matching the top1 entry.
    offset = 0
    for clip_idx in range(0, len(clip_results) - 1):
        id = hashlib.sha512(bytes(clip_results[clip_idx] + str(time.time()), 'utf-8')).hexdigest()[0:8]
        d["metadata"][id] = {
            "vid": "1",     # view to which this metadata is attached to
            "flg": 0,       # NOT USED YET
                  # z defines temporal location in audio or video, here it records a temporal segment from 2 sec. to 6.5 sec.
            "z": [
                offset,
                offset + clip_length
            ],
            "xy": [],       # xy defines spatial location (e.g. bounding box), here it is empty
            "av": {         # defines the value of each attribute for this (z, xy) combination
             "1": LABEL_ATTR_LOOKUP[clip_results[clip_idx]]      # the value for attribute-id="1" is one of its option with id "1" (i.e. Activity = Break Egg)
            }
        }
        offset = offset + clip_length


def parse_args():
    parser = argparse.ArgumentParser(description='Convert extended PHAR JSON output into a CSV file suitable for import into VGG Image Annotator')
    parser.add_argument('phar', help='JSON file from demo/multimodial_demo.py',)
    parser.add_argument('via', help='output JSON file, for use with VGG Image Annotator',)
    parser.add_argument('--loglevel', nargs=1, type=str, default=["info"], choices=['debug', 'info', 'warning', 'error'])
    parser.add_argument('--ann',
                        type=str,
                        default='resources/annotations/annotations.txt',
                        help='annotation file')

    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    logging.basicConfig(level=args.loglevel[0].upper())

    logging.debug(f"Have input JSON at {args.phar} with size {os.stat(args.phar).st_size}")

    phar_data = json.load(open(args.phar,))
    via_data = init_via_data()

    # Populate each major section of the project
    # Ref https://gitlab.com/vgg/via/blob/master/via-3.x.y/CodeDoc.md#structure-of-via-project-json-file
    populate_header(via_data, phar_data)
    populate_config(via_data, args)
    populate_attributes(via_data, phar_data, args)
    populate_files(via_data, phar_data)
    populate_views(via_data)
    populate_metadata(via_data, phar_data)

    logging.debug("Have final output as " + pprint.pformat(via_data))

    # Write to file
    with open(args.via,"w") as via_file:
        via_file.write(json.dumps(via_data, indent=2))

    logging.info(f"Wrote {args.via}")

if __name__ == '__main__':
    main()
