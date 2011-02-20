#!/usr/bin/env python

import pprint
import logging
import sys
import imp
from os.path import expanduser


class Config(dict):

    def __init__(self):
        self["project"] = ""
        self["closed"] = ("Fixed", "Invalid", "Duplicate", "WontFix")
        self["open"] = ("New", "Accepted", "Assigned", "Started")
        self["user"] = ""
        self["password"] = ""
        self["open_issues_outfile"] = "open_issues.png"
        self["opened_closed_issues_outfile"] = "opened_closed_issues.png"
        self["loglevel"] = "INFO"
        self["cache"] = "none"
        self["next_retry"] = 5
        self["same_retry"] = 5
        self["annotations"] = ()

    def check_values(self):
        for key in ("next_retry", "same_retry"):
            try:
                self[key] = int(self[key])
            except ValueError:
                logging.critical("Config error: %s must be an integer, found: "
                                % (key, self[key]))
                sys.exit(1)

        for key in ("closed", "open", "annotations"):
            try:
                self[key] = tuple(self[key])
            except ValueError:
                logging.critical("Config error: %s must be a list or tuple, found: "
                                % (key, self[key]))
                sys.exit(1)

                
    def load_from_file(self, project):
        _ = imp.load_source("_", expanduser("~/.gcode_tracker_graphs.conf"))
        self.update(getattr(_, project))
        self["project"] = project
        self.check_values()
        
        

conf = Config()

if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(conf)
