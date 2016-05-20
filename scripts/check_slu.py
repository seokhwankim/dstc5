import argparse, sys, os, json, types, ontology_reader
from semantic_tag_parser import SemanticTagParser
from HTMLParser import HTMLParseError

def main(argv):
    install_path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    utils_dirname = os.path.join(install_path,'lib')

    sys.path.append(utils_dirname)
    from dataset_walker import dataset_walker

    parser = argparse.ArgumentParser(description='Check the validity of a system output for pilot tasks.')
    parser.add_argument('--dataset', dest='dataset', action='store', metavar='DATASET', required=True, help='The dataset to analyze')
    parser.add_argument('--dataroot',dest='dataroot',action='store', metavar='PATH', required=True, help='Will look for corpus in <destroot>/<dataset>/...')
    parser.add_argument('--pilotfile',dest='pilotfile',action='store',metavar='JSON_FILE',required=True, help='File containing JSON output')
    parser.add_argument('--ontology',dest='ontology',action='store',metavar='JSON_FILE',required=True, help='JSON Ontology file')
    parser.add_argument('--roletype',dest='roletype',action='store',choices=['GUIDE', 'TOURIST'],required=True, help='Target role')

    args = parser.parse_args()

    sessions = dataset_walker(args.dataset,dataroot=args.dataroot,labels=False)
    system_output = json.load(open(args.pilotfile))

    tagsets = ontology_reader.OntologyReader(args.ontology).get_pilot_tagsets()

    checker = TrackChecker(sessions, system_output, tagsets, args.roletype)
    checker.check()
    checker.print_errors()

class TrackChecker():
    def __init__(self, sessions, tracker_output, tagsets, roletype):
        self.sessions = sessions
        self.tracker_output = tracker_output
        self.errors = []
        self.tagsets = tagsets
        self.roletype = roletype

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

        if "task_type" not in self.tracker_output :
            self.add_error(("top level",),"task_type should be specified")
        elif self.tracker_output['task_type'] != 'SLU':
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
            label_utter_list = []

            for log_utter, _, label_utter in session:
                if (self.roletype == 'GUIDE' and log_utter['speaker'] == 'Guide') or (self.roletype == 'TOURIST' and log_utter['speaker'] == 'Tourist'):
                    log_utter_list.append(log_utter)
                    label_utter_list.append(label_utter)

            # check number of utterances
            if len(log_utter_list) != len(track_session["utterances"]) :
                self.add_error((session_id,),"number of utterances spoken by %s does not match" % (self.roletype,))

            # now iterate through turns
            for log_utter, label_utter, track_utter in zip(log_utter_list, label_utter_list, track_session["utterances"]):
                # check utter index
                if log_utter['utter_index'] != track_utter['utter_index']:
                    self.add_error((session_id, "utterance", log_utter['utter_index'], track_utter['utter_index']), "utter_index does not match")

                if 'speech_act' not in track_utter:
                    self.add_error((session_id, "utterance", log_utter['utter_index']), "no speech_act key in utterance")
                else:
                    if type(track_utter['speech_act']) != types.ListType:
                        self.add_error((session_id, "utterance", log_utter['utter_index']), "a value for 'speech_act' key should be a list of objects")
                    else:
                        for act_obj in track_utter['speech_act']:
                            if 'act' not in act_obj:
                                self.add_error((session_id, "utterance", log_utter['utter_index']), "no act key in speech_act")
                            else:
                                if act_obj['act'] not in self.tagsets['speech_act']['category']:
                                    self.add_error((session_id, 'utterance', log_utter['utter_index'], act_obj['act']), "do not recognise speech act category")

                            if 'attributes' not in act_obj:
                                self.add_error((session_id, "utterance", log_utter['utter_index']), "no attributes key in speech_act")
                            else:
                                for attr in act_obj['attributes']:
                                    if attr not in self.tagsets['speech_act']['attribute']:
                                        self.add_error((session_id, 'utterance', log_utter['utter_index'], attr), "do not recognise speech act attribute")

                if 'semantic_tagged' not in track_utter:
                    self.add_error((session_id, "utterance", log_utter['utter_index']), "no semantic_tagged key in utterance")
                else:
                    if type(track_utter['semantic_tagged']) != types.StringType and type(track_utter['semantic_tagged']) != types.UnicodeType:
                        self.add_error((session_id, "utterance", log_utter['utter_index'], type(track_utter['semantic_tagged'])), "a value for 'semantic_tagged' key should be a string")
                    else:
                        try:
                            parser_ref = SemanticTagParser()
                            parser_ref.feed(log_utter['transcript'])

                            parser_pred = SemanticTagParser()
                            parser_pred.feed(track_utter['semantic_tagged'])

                            if parser_ref.get_chr_seq() != parser_pred.get_chr_seq():
                                self.add_error((session_id, 'utterance', log_utter['utter_index'], log_utter['transcript'], track_utter['semantic_tagged']), "raw utterance has changed")

                            for bio, tag, attrs in parser_pred.get_word_tag_seq():
                                if tag is not None:
                                    tag = tag.upper()
                                    if tag not in self.tagsets['semantic']:
                                        self.add_error((session_id, 'utterance', log_utter['utter_index'], tag), "do not recognise semantic category")
                                    elif attrs is not None:
                                        for s,v in attrs:
                                            s = s.upper().strip()
                                            v = v.upper().strip()

                                            if len(v) == 0:
                                                v = 'NONE'

                                            if s not in self.tagsets['semantic'][tag]:
                                                if v is not None and v != 'NONE':
                                                    self.add_error((session_id, 'utterance', log_utter['utter_index'], tag, s), "do not recognise semantic attribute type")
                                            elif v not in self.tagsets['semantic'][tag][s]:
                                                self.add_error((session_id, 'utterance', log_utter['utter_index'], tag, s, v), "do not recognise semantic attribute value")

                        except HTMLParseError, err:
                            self.add_error((session_id, 'utterance', log_utter['utter_index'], track_utter['semantic_tagged']), "do not parse the tagged utterance")

if (__name__ == '__main__'):
    main(sys.argv)    
