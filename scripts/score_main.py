# -*- coding: utf-8 -*-

"""
Evaluation script for the main task.
It creates a CSV file including the scores.
"""

import sys
import os
import argparse
import json
from ontology_reader import OntologyReader

SCHEDULES = [1,2]

def main(argv):
    install_path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    utils_dirname = os.path.join(install_path,'lib')

    sys.path.append(utils_dirname)
    from dataset_walker import dataset_walker
    from stat_classes import Stat_Accuracy, Stat_Frame_Precision_Recall

    parser = argparse.ArgumentParser(description='Evaluate output from a belief tracker.')
    parser.add_argument('--dataset', dest='dataset', action='store', metavar='DATASET', required=True,help='The dataset to analyze')
    parser.add_argument('--dataroot',dest='dataroot',action='store', metavar='PATH', required=True,help='Will look for corpus in <destroot>/<dataset>/...')
    parser.add_argument('--trackfile',dest='trackfile',action='store',metavar='JSON_FILE',required=True,help='File containing tracker JSON output')
    parser.add_argument('--scorefile',dest='scorefile',action='store',metavar='JSON_FILE',required=True,help='File to write with JSON scoring data')
    parser.add_argument('--ontology',dest='ontology',action='store',metavar='JSON_FILE',required=True,help='JSON Ontology file')

    args = parser.parse_args()

    sessions = dataset_walker(args.dataset, dataroot=args.dataroot, labels=True)
    tracker_output = json.load(open(args.trackfile))

    ontology = OntologyReader(args.ontology)

    stats = []
    stat_classes = [Stat_Accuracy, Stat_Frame_Precision_Recall]

    for schedule in SCHEDULES:
        for stat_class in stat_classes:
            stats.append((('all', 'all'), schedule, stat_class()))

        for topic in ontology.get_topics():
            for slot in ontology.get_slots(topic) + ['all']:
                for stat_class in stat_classes:
                    stats.append(((topic, slot), schedule, stat_class()))

    utter_counter = 0.0

    for session, track_session in zip(sessions, tracker_output["sessions"]):
        prev_ref_frame = None
        prev_track_frame = None
        prev_topic = None

        for (log_utter, translations, label_utter), track_utter in zip(session, track_session["utterances"]):
            utter_counter += 1.0

            if log_utter['segment_info']['target_bio'] == 'B':
                # Beginning of a new segment
                ref_frame = label_utter['frame_label']
                track_frame = track_utter['frame_label']

                for (topic, slot), schedule, stat_class in stats:
                    if schedule == 2:
                        if topic == 'all':
                            stat_class.add(prev_track_frame, prev_ref_frame)
                        elif prev_topic == topic:
                            if slot == 'all':
                                stat_class.add(prev_track_frame, prev_ref_frame)
                            else:
                                if slot in prev_track_frame and slot in prev_ref_frame:
                                    stat_class.add({slot: prev_track_frame[slot]}, {slot: prev_ref_frame[slot]})
                                elif slot in prev_track_frame and slot not in prev_ref_frame:
                                    stat_class.add({slot: prev_track_frame[slot]}, {slot: []})
                                elif slot not in prev_track_frame and slot in prev_ref_frame:
                                    stat_class.add({slot: []}, {slot: prev_ref_frame[slot]})

            elif log_utter['segment_info']['target_bio'] == 'I':
                ref_frame = label_utter['frame_label']
                track_frame = track_utter['frame_label']
            elif log_utter['segment_info']['target_bio'] == 'O':
                ref_frame = None
                track_frame = None

            for (topic, slot), schedule, stat_class in stats:
                if schedule == 1:
                    if topic == 'all':
                        stat_class.add(track_frame, ref_frame)
                    elif log_utter['segment_info']['topic'] == topic:
                        if slot == 'all':
                            stat_class.add(track_frame, ref_frame)
                        else:
                            if slot in track_frame and slot in ref_frame:
                                stat_class.add({slot: track_frame[slot]}, {slot: ref_frame[slot]})
                            elif slot in track_frame and slot not in ref_frame:
                                stat_class.add({slot: track_frame[slot]}, {slot: []})
                            elif slot not in track_frame and slot in ref_frame:
                                stat_class.add({slot: []}, {slot: ref_frame[slot]})

            prev_ref_frame = ref_frame
            prev_track_frame = track_frame
            prev_topic = log_utter['segment_info']['topic']

        for (topic, slot), schedule, stat_class in stats:
            if schedule == 2:
                if topic == 'all':
                    stat_class.add(prev_track_frame, prev_ref_frame)
                elif prev_topic == topic:
                    if slot == 'all':
                        stat_class.add(prev_track_frame, prev_ref_frame)
                    else:
                        if slot in prev_track_frame and slot in prev_ref_frame:
                            stat_class.add({slot: prev_track_frame[slot]}, {slot: prev_ref_frame[slot]})
                        elif slot in track_frame and slot not in ref_frame:
                            stat_class.add({slot: prev_track_frame[slot]}, {slot: []})
                        elif slot not in track_frame and slot in ref_frame:
                            stat_class.add({slot: []}, {slot: prev_ref_frame[slot]})

    csvfile = open(args.scorefile, 'w')
    print >> csvfile, ("topic, slot, schedule, stat, N, result")

    for stat in stats:
        (topic, slot), schedule, stat_class = stat

        results = stat_class.results()
        for stat_subname, N, result in results:
            if result == None:
                result = "-"
            else:
                result = "%.7f"%result
            print >>csvfile,("%s, %s, %i, %s, %i, %s"%(topic, slot, schedule, stat_subname, N, result))

    print >>csvfile,'basic,total_wall_time,,,,%s' % (tracker_output['wall_time'])
    print >>csvfile,'basic,sessions,,,,%s' % (len(sessions))
    print >>csvfile,'basic,utterances,,,,%i' % (int(utter_counter))
    print >>csvfile,'basic,wall_time_per_utterance,,,,%s' % (tracker_output['wall_time'] / utter_counter)
    print >>csvfile,'basic,dataset,,,,%s' % (tracker_output['dataset'] )

    csvfile.close()

if (__name__ == '__main__'):
    main(sys.argv)
