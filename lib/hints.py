import csv
import os

from .logger import log

def load(path):
    hints_file = os.path.join(path, "hints.txt")
    hints = {}
    if os.path.exists(hints_file):
        log("Found a hints.txt file, loading...")
        with open(hints_file, 'r') as fp:
            reader = csv.reader(fp, delimiter=' ', skipinitialspace=True)
            for row in reader:
                print("|".join(row))
                if len(row) < 3:
                    log("bad hint.txt syntax:", row)
                    continue
                name = row[0]
                if not name in hints:
                    hints[name] = {}
                hint = row[1]
                if hint in [ "gain", "rotate", "video_shift", "video_hide" ]:
                    hints[name][hint] = float(row[2])
                elif hint == "suppress":
                    if "suppress" in hints[name]:
                        hints[name]["suppress"].append( (float(row[2]), float(row[3])) )
                    else:
                        hints[name]["suppress"] = [ (float(row[2]), float(row[3])) ]
                else:
                    log("unknwon hint in hint.txt:", row)
    return hints
