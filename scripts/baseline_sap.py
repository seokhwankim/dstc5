# -*- coding: utf-8 -*-
__author__ = "Seokhwan Kim"

"""
A simple baseline tracker for SAP pilot task of DSTC5.

It trains SVM models for speech act prediction on English training dataset.
Then, the models are used in analyzing the English translation of each Chinese utterance in test set.
Finally, the predicted annotations on the English side are projected to the original Chinese utterances.
"""

from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.multiclass import OneVsRestClassifier
from sklearn.feature_extraction.text import CountVectorizer
from sklearn import preprocessing

from itertools import combinations

import pickle
import argparse
import sys
import dataset_walker
import time
import json

import operator
import copy

import re


class SimpleSAP:
    def __init__(self):
        self.__speech_act_instance_list = []
        self.__speech_act_model = None
        self.__speech_act_lb = None

    def load_model(self, modelfile):
        with open(modelfile, 'r') as f:
            self.__speech_act_model, self.__speech_act_lb = pickle.load(f)

        return True

    def add_instance(self, instance, speech_act):
        sa_label_list = []
        for sa in speech_act:
            sa_labels = ['%s_%s' % (sa['act'], attr) for attr in sa['attributes']]
            sa_label_list += sa_labels

        sa_label_list = sorted(set(sa_label_list))

        feats = self.__get_feats(instance)
        bi_feats = ['%s+%s' % (x, y) for x, y in combinations(feats, 2)]

        self.__speech_act_instance_list.append((' '.join(feats + bi_feats), sa_label_list))

        return True

    def __get_feats(self, instance):
        result = []
        # current semantic tag features
        if len(instance['curr_semantic_tags']) == 0:
            result.append('curr_semantic_tag:null')
        else:
            for tag in instance['curr_semantic_tags']:
                main_cat = tag['main']
                sub_cat = tag['attributes']['cat']
                result.append('curr_semantic_tag:%s' % (main_cat,))
                result.append('curr_semantic_tag:%s_%s' % (main_cat, sub_cat))

        # previous semantic tag features
        if instance['prev_semantic_tags'] is None or len(instance['prev_semantic_tags']) == 0:
            result.append('prev_semantic_tag:null')
        else:
            for tag in instance['prev_semantic_tags']:
                main_cat = tag['main']
                sub_cat = tag['attributes']['cat']
                result.append('prev_semantic_tag:%s' % (main_cat,))
                result.append('prev_semantic_tag:%s_%s' % (main_cat, sub_cat))

        # previous turn speech act features
        if instance['prev_turn_act'] is None:
            result.append('prev_turn_act:null')
        else:
            for act in instance['prev_turn_act']:
                main_act = act['act']
                result.append('prev_turn_act:%s' % (main_act,))

                for attr in act['attributes']:
                    result.append('prev_turn_act:%s_%s' % (main_act, attr))

        # distance from the previuos turn features
        dist = instance['dist_from_prev_turn']
        if dist == 1:
            result.append('dist_from_prev_turn:1')
        elif dist == 2:
            result.append('dist_from_prev_turn:2')
        else:
            result.append('dist_from_prev_turn>2')

        return result

    def train(self, modelfile):
        sa_feats = [x for x, _ in self.__speech_act_instance_list]
        sa_labels = [y for _, y in self.__speech_act_instance_list]

        self.__speech_act_lb = preprocessing.MultiLabelBinarizer()
        sa_labels = self.__speech_act_lb.fit_transform(sa_labels)

        self.__speech_act_model = Pipeline([
            ('vectorizer', CountVectorizer()),
            ('clf', OneVsRestClassifier(LinearSVC(verbose=True)))])

        self.__speech_act_model.fit(sa_feats, sa_labels)

        with open(modelfile, 'wb') as f:
            pickle.dump((self.__speech_act_model, self.__speech_act_lb), f)

    def pred(self, instance):
        feats = self.__get_feats(instance)
        bi_feats = ['%s+%s' % (x, y) for x, y in combinations(feats, 2)]

        pred_act = self.__speech_act_lb.inverse_transform(self.__speech_act_model.predict([' '.join(feats + bi_feats)]))
        return pred_act


def main(argv):
    parser = argparse.ArgumentParser(description='Simple SAP baseline.')
    parser.add_argument('--trainset', dest='trainset', action='store', metavar='TRAINSET', required=True, help='The training dataset')
    parser.add_argument('--testset', dest='testset', action='store', metavar='TESTSET', required=True, help='The test dataset')
    parser.add_argument('--dataroot', dest='dataroot', action='store', required=True, metavar='PATH',  help='Will look for corpus in <destroot>/...')
    parser.add_argument('--modelfile', dest='modelfile', action='store', required=True, metavar='MODEL_FILE',  help='File to write with trained model')
    parser.add_argument('--outfile', dest='outfile', action='store', required=True, metavar='JSON_FILE',  help='File to write with SAP output')
    parser.add_argument('--roletype', dest='roletype', action='store', choices=['GUIDE',  'TOURIST'], required=True,  help='Target role')

    args = parser.parse_args()

    sap = SimpleSAP()

    trainset = dataset_walker.dataset_walker(args.trainset, dataroot=args.dataroot, labels=True, translations=True, task='SAP', roletype=args.roletype.lower())
    sys.stderr.write('Loading training instances ... ')

    for call in trainset:
        instance = {'prev_turn_act': None, 'curr_semantic_tags': None, 'prev_semantic_tags': None, 'dist_from_prev_turn': 0}
        for (log_utter, translations, label_utter) in call:
            if log_utter['speaker'].lower() == args.roletype.lower():
                instance['curr_semantic_tags'] = log_utter['semantic_tags']
                instance['dist_from_prev_turn'] += 1

                sap.add_instance(copy.deepcopy(instance), label_utter['speech_act'])
            else:
                instance['prev_turn_act'] = log_utter['speech_act']
                instance['dist_from_prev_turn'] = 0
            instance['prev_semantic_tags'] = log_utter['semantic_tags']
    sys.stderr.write('Done\n')

    sap.train(args.modelfile)

    output = {'sessions': []}
    output['dataset'] = args.testset
    output['task_type'] = 'SAP'
    output['role_type'] = args.roletype
    start_time = time.time()

    testset = dataset_walker.dataset_walker(args.testset, dataroot=args.dataroot, labels=False, translations=True, task='SAP', roletype=args.roletype.lower())
    sys.stderr.write('Loading testing instances ... ')
    for call in testset:
        this_session = {"session_id": call.log["session_id"], "utterances": []}

        instance = {'prev_turn_act': None, 'curr_semantic_tags': None, 'prev_semantic_tags': None, 'dist_from_prev_turn': 0}

        for (log_utter, translations, label_utter) in call:
            if log_utter['speaker'].lower() == args.roletype.lower():
                sap_result = {'utter_index': log_utter['utter_index']}

                instance['curr_semantic_tags'] = log_utter['semantic_tags']
                instance['dist_from_prev_turn'] += 1

                pred_act = sap.pred(copy.deepcopy(instance))
                combined_act = {}
                for act_label in reduce(operator.add, pred_act):
                    m = re.match('^([^_]+)_(.+)$', act_label)
                    act = m.group(1)
                    attr = m.group(2)
                    if act not in combined_act:
                        combined_act[act] = []
                    if attr not in combined_act[act]:
                        combined_act[act].append(attr)

                sap_result['speech_act'] = []
                for act in combined_act:
                    attr = combined_act[act]
                    sap_result['speech_act'].append({'act': act, 'attributes': attr})

                this_session['utterances'].append(sap_result)
            else:
                instance['prev_turn_act'] = log_utter['speech_act']
                instance['dist_from_prev_turn'] = 0
            instance['prev_semantic_tags'] = log_utter['semantic_tags']

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
