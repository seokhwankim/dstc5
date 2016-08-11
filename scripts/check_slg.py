# -*- coding: utf-8 -*-

import argparse
import sys
import os
import json
import types


def main(argv):
    install_path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    utils_dirname = os.path.join(install_path,'lib')

    sys.path.append(utils_dirname)
    from dataset_walker import dataset_walker

    parser = argparse.ArgumentParser(description='Check the validity of a system output for SLG task.')
    parser.add_argument('--dataset', dest='dataset', action='store', metavar='DATASET', required=True, help='The dataset to analyze')
    parser.add_argument('--dataroot',dest='dataroot',action='store', metavar='PATH', required=True, help='Will look for corpus in <destroot>/...')
    parser.add_argument('--jsonfile',dest='jsonfile',action='store',metavar='JSON_FILE',required=True, help='File containing JSON output')
    parser.add_argument('--roletype',dest='roletype',action='store',choices=['GUIDE', 'TOURIST'],required=True, help='Target role')

    args = parser.parse_args()

    sessions = dataset_walker(args.dataset, dataroot=args.dataroot, labels=False, task='SLG', roletype=args.roletype.lower())
    system_output = json.load(open(args.jsonfile))

    checker = TrackChecker(sessions, system_output, args.roletype)
    checker.check()
    checker.print_errors()


class TrackChecker():
    def __init__(self, sessions, tracker_output, roletype):
        self.sessions = sessions
        self.tracker_output = tracker_output
        self.errors = []
        self.roletype = roletype

    def add_error(self, context, error_str):
        self.errors.append((context, error_str))

    def print_errors(self):
        if len(self.errors) == 0:
            print "Found no errors, trackfile is valid"
        else:
            print "Found %d errors:" % len(self.errors)
        for context, error in self.errors:
            print " ".join(map(str, context)), "-", error

    def check(self):
    # first check the top-level stuff
        if len(self.sessions.datasets) != 1 :
            self.add_error(("top level",), "tracker output should be over a single dataset")
        if "dataset" not in self.tracker_output :
            self.add_error(("top level",),"trackfile should specify its dataset")
        elif self.sessions.datasets[0] != self.tracker_output["dataset"]:
            self.add_error(("top level",),"datasets do not match")
        if len(self.tracker_output["sessions"]) !=  len(self.sessions) :
            self.add_error(("top level",),"number of sessions does not match")
        if "wall_time" not in self.tracker_output :
            self.add_error(("top level",),"wall_time should be included")
        else:
            wall_time = self.tracker_output["wall_time"]
            if type(wall_time) != type(0.0):
                self.add_error(("top level",),"wall_time must be a float")
            elif wall_time <= 0.0 :
                self.add_error(("top level",),"wall_time must be positive")

        if "task_type" not in self.tracker_output :
            self.add_error(("top level",),"task_type should be specified")
        elif self.tracker_output['task_type'] != 'SLG':
            self.add_error(("top level",),"task_type does not match")

        if "role_type" not in self.tracker_output:
            self.add_error(("top level",),"role_type should be specified")
        elif self.tracker_output['role_type'] != self.roletype:
            self.add_error(("top level",),"role_type does not match")

        for session, track_session in zip(self.sessions, self.tracker_output["sessions"]):
            session_id = session.log["session_id"]
            # check session id
            if session_id != track_session["session_id"] :
                self.add_error((session_id,),"session-id does not match")

            log_utter_list = []

            for log_utter, _, _ in session:
                if log_utter['speaker'].lower() == self.roletype.lower():
                    log_utter_list.append(log_utter)

            # check number of utterances
            if len(log_utter_list) != len(track_session["utterances"]) :
                self.add_error((session_id,),"number of utterances spoken by %s does not match" % (self.roletype,))

            # now iterate through turns
            for log_utter, track_utter in zip(log_utter_list, track_session["utterances"]):
                # check utter index
                if log_utter['utter_index'] != track_utter['utter_index']:
                    self.add_error((session_id, "utterance", log_utter['utter_index'], track_utter['utter_index']), "utter_index does not match")

                if 'generated' not in track_utter:
                    self.add_error((session_id, "utterance", log_utter['utter_index']), "no generated key in utterance")
                else:
                    if type(track_utter['generated']) != types.StringType and type(track_utter['generated']) != types.UnicodeType:
                        self.add_error((session_id, "utterance", log_utter['utter_index']), "a value for 'generated' key should be a string")

if (__name__ == '__main__'):
    main(sys.argv)    
