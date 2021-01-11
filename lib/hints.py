import csv
import os

from .logger import log

def load(path):
    hints_file = os.path.join(path, "hints.txt")
    hints = {}
    if os.path.exists(hints_file):
        try:
            with open(hints_file, 'r', encoding="utf-8") as fp:
                reader = csv.reader(fp, delimiter=' ', skipinitialspace=True)
                for row in reader:
                    pass
            encoding = "utf-8"
        except:
            with open(hints_file, 'r', encoding="utf-16") as fp:
                reader = csv.reader(fp, delimiter=' ', skipinitialspace=True)
                for row in reader:
                    pass
            encoding = "utf-16"
        log("Found a hints.txt file, encoding:", encoding)
        with open(hints_file, 'r', encoding=encoding) as fp:
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
                if hint in [ "face_detect", "gain", "rotate", "video_shift", "video_hide" ]:
                    hints[name][hint] = float(row[2])
                elif hint == "suppress":
                    if "suppress" in hints[name]:
                        hints[name]["suppress"].append( (float(row[2]), float(row[3])) )
                    else:
                        hints[name]["suppress"] = [ (float(row[2]), float(row[3])) ]
                else:
                    log("unknwon hint in hint.txt:", row)
    return hints
