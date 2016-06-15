# -*- coding: utf-8 -*-
__author__ = "Seokhwan Kim"

"""
A simple baseline system for SLG pilot task of DSTC5.
"""


import argparse
import sys

import time
import json

import dataset_walker

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.neighbors import NearestNeighbors


class SimpleSLG:
    def __init__(self):
        self.__features = []
        self.__translations = []

        self.__vectorizer = CountVectorizer()
        self.__model = None

    def __get_feats(self, instance):
        feats = []
        for speech_act in instance['speech_act']:
            act = speech_act['act']
            feats.append(act)
            for attr in speech_act['attributes']:
                feats.append('%s_%s' % (act, attr))

        for semantic_tag in instance['semantic_tags']:
            cat = semantic_tag['main']
            feats.append(cat)
            for attr in semantic_tag['attributes']:
                val = semantic_tag['attributes'][attr]
                feats.append('%s_%s_%s' % (cat, attr, val))
        return feats

    def add_instance(self, instance, translations):
        feats = self.__get_feats(instance)

        self.__features.append(' '.join(feats))
        self.__translations.append(translations['translated'][0]['hyp'])

    def train(self):
        vecs = self.__vectorizer.fit_transform(self.__features)
        self.__model = NearestNeighbors(n_neighbors=1, algorithm='ball_tree').fit(vecs)

    def generate(self, instance):
        feats = self.__get_feats(instance)
        vecs = self.__vectorizer.transform([' '.join(feats)])
        distances, indices = self.__model.kneighbors(vecs)
        return self.__translations[indices[0][0]]

def main(argv):
    parser = argparse.ArgumentParser(description='Simple SLG baseline.')
    parser.add_argument('--trainset', dest='trainset', action='store', metavar='TRAINSET', required=True, help='The training dataset')
    parser.add_argument('--testset', dest='testset', action='store', metavar='TESTSET', required=True, help='The test dataset')
    parser.add_argument('--dataroot', dest='dataroot', action='store', required=True, metavar='PATH',  help='Will look for corpus in <destroot>/...')
    parser.add_argument('--outfile', dest='outfile', action='store', required=True, metavar='JSON_FILE',  help='File to write with SAP output')
    parser.add_argument('--roletype', dest='roletype', action='store', choices=['GUIDE',  'TOURIST'], required=True,  help='Target role')

    args = parser.parse_args()

    sap = SimpleSLG()

    trainset = dataset_walker.dataset_walker(args.trainset, dataroot=args.dataroot, labels=True, translations=True, task='SLG', roletype=args.roletype.lower())
    sys.stderr.write('Loading training instances ... ')

    for call in trainset:
        for (log_utter, translations, label_utter) in call:
            if log_utter['speaker'].lower() == args.roletype.lower():
                instance = {'semantic_tags': log_utter['semantic_tags'], 'speech_act': log_utter['speech_act']}
                sap.add_instance(instance, translations)

    sap.train()
    sys.stderr.write('Done\n')

    output = {'sessions': []}
    output['dataset'] = args.testset
    output['task_type'] = 'SAP'
    output['role_type'] = args.roletype
    start_time = time.time()

    testset = dataset_walker.dataset_walker(args.testset, dataroot=args.dataroot, labels=False, translations=True, task='SLG', roletype=args.roletype.lower())
    sys.stderr.write('Loading testing instances ... ')
    for call in testset:
        this_session = {"session_id": call.log["session_id"], "utterances": []}

        for (log_utter, translations, label_utter) in call:
            if log_utter['speaker'].lower() == args.roletype.lower():
                instance = {'semantic_tags': log_utter['semantic_tags'], 'speech_act': log_utter['speech_act']}

                slg_result = {'utter_index': log_utter['utter_index'], 'generated': sap.generate(instance)}
                this_session['utterances'].append(slg_result)

        output['sessions'].append(this_session)
    sys.stderr.write('Done\n')

    end_time = time.time()
    elapsed_time = end_time - start_time
    output['wall_time'] = elapsed_time

    with open(args.outfile, "wb") as of:
        json.dump(output, of, indent=4)

    sys.stderr.write('Done\n')

if __name__ == "__main__":
    main(sys.argv)
