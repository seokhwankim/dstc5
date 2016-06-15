# -*- coding: utf-8 -*-
__author__ = "Seokhwan Kim"

"""
Dataset converter for SLG pilot task of DSTC5.

It converts the training and development datasets for DSTC5 into the formats for SLG pilot task.
"""

import argparse
import sys
import dataset_walker
import json
import os
from semantic_tag_parser import SemanticTagParser

def main(argv):
    parser = argparse.ArgumentParser(description='Dataset Converter for SAP pilot task.')
    parser.add_argument('--dataset', dest='dataset', action='store', metavar='DATASET', required=True, help='The target dataset to be converted')
    parser.add_argument('--dataroot', dest='dataroot', action='store', required=True, metavar='PATH',  help='Will look for corpus in <destroot>/...')

    args = parser.parse_args()

    dataset = dataset_walker.dataset_walker(args.dataset, dataroot=args.dataroot, labels=True, translations=False)

    for call in dataset:
        session_id = call.log["session_id"]

        input_guide = {u'session_id': session_id, u'utterances': [], u'roletype': u'Guide'}
        output_guide = {u'session_id': session_id, u'utterances': [], u'roletype': u'Guide'}

        input_tourist = {u'session_id': session_id, u'utterances': [], u'roletype': u'Tourist'}
        output_tourist = {u'session_id': session_id, u'utterances': [], u'roletype': u'Tourist'}

        for (log_utter, _, label_utter) in call:
            speaker = log_utter['speaker']
            utter_index = log_utter['utter_index']
            transcript = log_utter['transcript']

            speech_act = label_utter['speech_act']

            mention_words = []
            curr_cat = None
            curr_attrs = None

            semantic_tags = []

            for semantic_tagged in label_utter['semantic_tagged']:
                parser = SemanticTagParser(False)
                parser.feed(semantic_tagged)

                for word, (bio, cat, attrs) in zip(parser.get_word_seq(), parser.get_word_tag_seq()):
                    if bio == 'I':
                        mention_words.append(word)
                    else:
                        if curr_cat is not None:
                            semantic_tags.append({
                                u'main': curr_cat,
                                u'attributes': curr_attrs,
                                u'mention': ' '.join(mention_words)
                            })

                        mention_words = []
                        curr_cat = None
                        curr_attrs = None

                        if bio == 'B':
                            mention_words = [word]
                            curr_cat = cat
                            curr_attrs = {}
                            for key, value in attrs:
                                curr_attrs[key] = value

                if curr_cat is not None:
                    semantic_tags.append({
                        u'main': curr_cat,
                        u'attributes': curr_attrs,
                        u'mention': ' '.join(mention_words)
                    })

            if speaker == 'Guide':
                input_guide[u'utterances'].append({
                    u'utter_index': utter_index,
                    u'speaker': speaker,
                    u'semantic_tags': semantic_tags,
                    u'speech_act': speech_act
                })
                output_guide[u'utterances'].append({
                    u'utter_index': utter_index,
                    u'transcript': transcript
                })
                input_tourist[u'utterances'].append({
                    u'utter_index': utter_index,
                    u'speaker': speaker,
                    u'transcript': transcript,
                    u'semantic_tags': semantic_tags,
                    u'speech_act': speech_act
                })
            elif speaker == 'Tourist':
                input_tourist[u'utterances'].append({
                    u'utter_index': utter_index,
                    u'speaker': speaker,
                    u'semantic_tags': semantic_tags,
                    u'speech_act': speech_act
                })
                output_tourist[u'utterances'].append({
                    u'utter_index': utter_index,
                    u'transcript': transcript
                })
                input_guide[u'utterances'].append({
                    u'utter_index': utter_index,
                    u'speaker': speaker,
                    u'transcript': transcript,
                    u'semantic_tags': semantic_tags,
                    u'speech_act': speech_act
                })

        path = os.path.join(os.path.abspath(args.dataroot), '%03d' % (session_id,))

        with open(os.path.join(path, 'slg.guide.in.json'), 'w') as fp:
            json.dump(input_guide, fp)
        with open(os.path.join(path, 'slg.guide.label.json'), 'w') as fp:
            json.dump(output_guide, fp)
        with open(os.path.join(path, 'slg.tourist.in.json'), 'w') as fp:
            json.dump(input_tourist, fp)
        with open(os.path.join(path, 'slg.tourist.label.json'), 'w') as fp:
            json.dump(output_tourist, fp)

if __name__ == "__main__":
    main(sys.argv)
