# -*- coding: utf-8 -*-

"""
A simple baseline tracker for the main task of DSTC5.

It determines the slot values by fuzzy string matching between the entries in the ontology and the utterances mentioned from the beginning of a given segment to the current turn.
To adapt it for the cross-language execution, the following two different methods are implemented here:
- Method 1: The translated utterances from Chinese to English are matched to the English entries in the original ontology.
- Method 2: The Chinese utterances are matched to the translated entries in the ontology from English to Chinese.
"""

import argparse, sys, ontology_reader, dataset_walker, time, json, copy
from fuzzywuzzy import fuzz

class BaselineMethod1(object):
    def __init__(self, tagsets):
        self.tagsets = tagsets
        self.frame = {}
        self.memory = {}

        self.reset()

    def addUtter(self, utter, translations):
        output = {'utter_index': utter['utter_index']}
        
        top_hyp = ''
        if len(translations['translated']) > 0:
            top_hyp = translations['translated'][0]['hyp']

        topic = utter['segment_info']['topic']

        if utter['segment_info']['target_bio'] == 'B':
            self.frame = {}
            
        if topic in self.tagsets:
            for slot in self.tagsets[topic]:
                for value in self.tagsets[topic][slot]:
                    ratio = fuzz.partial_ratio(value, top_hyp)
                    if ratio > 80:
                        if slot not in self.frame:
                            self.frame[slot] = []
                        if value not in self.frame[slot]:
                            self.frame[slot].append(value)
            if topic == 'ATTRACTION' and 'PLACE' in self.frame and 'NEIGHBOURHOOD' in self.frame and self.frame['PLACE'] == self.frame['NEIGHBOURHOOD']:
                del self.frame['PLACE']

            output['frame_label'] = self.frame
        return output

    def reset(self):
        self.frame = {}

class BaselineMethod2(object):
    def __init__(self, translated_tagsets):
        self.translated_tagsets = translated_tagsets
        self.frame = {}
        self.memory = {}

        self.reset()

    def addUtter(self, utter, translations):
        output = {'utter_index': utter['utter_index']}
    	transcript = utter['transcript']
        
        topic = utter['segment_info']['topic']

        if utter['segment_info']['target_bio'] == 'B':
            self.frame = {}
            
        if topic in self.translated_tagsets:
            for slot in self.translated_tagsets[topic]:
                for value_obj in self.translated_tagsets[topic][slot]:
                    entry_en = value_obj['entry_en']
                    if len(value_obj['translated_cn']) > 0:
                        top_hyp = value_obj['translated_cn'][0]
                    
                        ratio = fuzz.partial_ratio(top_hyp, transcript)
                        if ratio > 80:
                            if slot not in self.frame:
                                self.frame[slot] = []
                            if entry_en not in self.frame[slot]:
                                self.frame[slot].append(entry_en)
            if topic == 'ATTRACTION' and 'PLACE' in self.frame and 'NEIGHBOURHOOD' in self.frame and self.frame['PLACE'] == self.frame['NEIGHBOURHOOD']:
                del self.frame['PLACE']

            output['frame_label'] = self.frame
        return output

    def reset(self):
        self.frame = {}

def main(argv):
    parser = argparse.ArgumentParser(description='Simple hand-crafted dialog state tracker baseline.')
    parser.add_argument('--dataset', dest='dataset', action='store', metavar='DATASET', required=True, help='The dataset to analyze')
    parser.add_argument('--dataroot',dest='dataroot',action='store',required=True,metavar='PATH', help='Will look for corpus in <destroot>/<dataset>/...')
    parser.add_argument('--trackfile',dest='trackfile',action='store',required=True,metavar='JSON_FILE', help='File to write with tracker output')
    parser.add_argument('--ontology',dest='ontology',action='store',metavar='JSON_FILE',required=True,help='JSON Ontology file')
    parser.add_argument('--method',dest='method',action='store',choices=['1', '2'],required=True,help='Baseline mode')

    args = parser.parse_args()
    dataset = dataset_walker.dataset_walker(args.dataset, dataroot=args.dataroot, labels=False, translations = True)

    track_file = open(args.trackfile, "wb")
    track = {"sessions":[]}
    track["dataset"]  = args.dataset
    start_time = time.time()

    if args.method == '1':
        tagsets = ontology_reader.OntologyReader(args.ontology).get_tagsets()
        tracker = BaselineMethod1(tagsets)
    elif args.method == '2':
        translated_tagsets = ontology_reader.OntologyReader(args.ontology).get_translated_tagsets()
        tracker = BaselineMethod2(translated_tagsets)

    for call in dataset:
        this_session = {"session_id":call.log["session_id"], "utterances":[]}
        tracker.reset()
        for (utter, translations, _) in call:
            sys.stderr.write('%d:%d      \r'%(call.log['session_id'], utter['utter_index']))
            tracker_result = tracker.addUtter(utter, translations)
            if tracker_result is not None:
                this_session["utterances"].append(copy.deepcopy(tracker_result))
        track["sessions"].append(this_session)
    end_time = time.time()
    elapsed_time = end_time - start_time
    track['wall_time'] = elapsed_time

    json.dump(track, track_file, indent=4)

    track_file.close()

if __name__ =="__main__":
    main(sys.argv)
