# -*- coding: utf-8 -*-

"""
This script checks whether the structure and contents of a given tracking result are valid or not.
For a valid input, it outputs `Found no errors, trackfile is valid'.
It is particularly useful for checking the tracker output on an unlabelled test set, before submitting it for evaluation in the challenge.
"""

import argparse, sys, os, json, ontology_reader

def main(argv):
    install_path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    utils_dirname = os.path.join(install_path,'lib')

    sys.path.append(utils_dirname)
    from dataset_walker import dataset_walker
    
    parser = argparse.ArgumentParser(description='Check the validity of a tracker output object.')
    parser.add_argument('--dataset', dest='dataset', action='store', metavar='DATASET', required=True,
                        help='The dataset to analyze')
    parser.add_argument('--dataroot',dest='dataroot',action='store', metavar='PATH', required=True,
                        help='Will look for corpus in <destroot>/<dataset>/...')
    parser.add_argument('--trackfile',dest='scorefile',action='store',metavar='JSON_FILE',required=True,
                        help='File containing score JSON')
    parser.add_argument('--ontology',dest='ontology',action='store',metavar='JSON_FILE',required=True,
                        help='JSON Ontology file')

    args = parser.parse_args()

    sessions = dataset_walker(args.dataset,dataroot=args.dataroot,labels=False)
    tracker_output = json.load(open(args.scorefile))

    tagsets = ontology_reader.OntologyReader(args.ontology).get_tagsets()

    checker = TrackChecker(sessions, tracker_output, tagsets)
    checker.check()
    checker.print_errors()

class TrackChecker():
    def __init__(self, sessions, tracker_output, tagsets):
        self.sessions = sessions
        self.tracker_output = tracker_output
        self.errors = []
        self.tagsets = tagsets

    def add_error(self, context, error_str):
        self.errors.append((context, error_str))

    def print_errors(self):
        if len(self.errors) == 0 :
            print "Found no errors, trackfile is valid"
        else:
            print "Found",len(self.errors),"errors:"
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

        for session, track_session in zip(self.sessions, self.tracker_output["sessions"]):
            session_id = session.log["session_id"]
            # check session id
            if session_id != track_session["session_id"] :
                self.add_error((session_id,),"session-id does not match")
            # check number of utterances
            if len(session) != len(track_session["utterances"]) :
                self.add_error((session_id,),"number of utterances do not match")

            # now iterate through turns
            for (log_utter, translations, label_utter), track_utter in zip(session, track_session["utterances"]):
                # check utter index
                if log_utter['utter_index'] != track_utter['utter_index']:
                    self.add_error((session_id, "utterance", log_utter['utter_index'], track_utter['utter_index']), "utter_index does not match")

                # check frame labels for target utterances
                if log_utter['segment_info']['target_bio'] != 'O' and 'frame_label' not in track_utter:
                    self.add_error((session_id, "utterance", log_utter['utter_index']), "no frame_label key in utterance")

                topic = log_utter['segment_info']['topic']
                if 'frame_label' in track_utter:
                    frame_label = track_utter['frame_label']
                    for slot in frame_label:
                        # check slots in frame labels
                        if slot not in self.tagsets[topic]:
                            self.add_error((session_id, 'utterance', log_utter['utter_index'], slot), "do not recognise slot")
                        else:
                            # check slot values in frame labels
                            cnt = {}
                            for value in frame_label[slot]:
                                if value not in self.tagsets[topic][slot]:
                                    self.add_error((session_id, 'utterance', log_utter['utter_index'], slot, value), "do not recognise slot value")
                                if value not in cnt: cnt[value] = 0
                                cnt[value] += 1
                                if cnt[value] > 1:
                                    self.add_error((session_id, 'utterance', log_utter['utter_index'], slot, value), "repeated value")
        
if __name__ =="__main__":
    main(sys.argv)
