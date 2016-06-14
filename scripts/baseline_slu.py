# -*- coding: utf-8 -*-
__author__ = "Seokhwan Kim"

"""
A simple baseline tracker for SLU pilot task of DSTC5.

It trains a pair of CRF and SVM models for semantic tagging and speech act identification, respectively, based on English training dataset.
Then, the models are used in analyzing the English translation of each Chinese utterance in test set.
Finally, the predicted annotations on the English side are projected to the original Chinese utterances through given word alignments.
"""

import nltk
from nltk.tag import CRFTagger

from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.multiclass import OneVsRestClassifier
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn import preprocessing

import pickle
import argparse, sys, dataset_walker, time, json
from semantic_tag_parser import SemanticTagParser

import operator

import re


class SimpleSLU:
    def __init__(self):
        self.__semantic_instance_list = []
        self.__speech_act_instance_list = []

        self.__semantic_model = None
        self.__speech_act_model = None

        self.__speech_act_lb = None

    def load_model(self, modelfile):
        with open('%s.act.model' % modelfile, 'r') as f:
            self.__speech_act_model, self.__speech_act_lb = pickle.load(f)

        self.__semantic_model = CRFTagger(verbose=True)
        self.__semantic_model.set_model_file('%s.semantic.model' % modelfile)

        return True

    def add_instance(self, utter, speech_act, semantic_tagged):
        tokenized = self.__tokenize(utter, semantic_tagged)
        if tokenized is None:
            return False

        semantic_instance = []
        for word, (bio, tag, attrs) in tokenized:
            if bio is None:
                sem_label = 'O'
            else:
                cat = None
                for attr, val in attrs:
                    if attr == 'cat':
                        cat = val
                sem_label = '%s-%s_%s' % (bio, tag, cat)
            semantic_instance.append((unicode(word.lower()), unicode(sem_label)))
        self.__semantic_instance_list.append(semantic_instance)

        sa_label_list = []
        for sa in speech_act:
            sa_labels = ['%s_%s' % (sa['act'], attr) for attr in sa['attributes']]
            sa_label_list += sa_labels

        sa_label_list = sorted(set(sa_label_list))

        word_feats = ' '.join([word.lower() for word, _ in tokenized])
        self.__speech_act_instance_list.append((word_feats, sa_label_list))

        return True

    def train(self, modelfile):
        sa_feats = [x for x, _ in self.__speech_act_instance_list]
        sa_labels = [y for _, y in self.__speech_act_instance_list]

        self.__speech_act_lb = preprocessing.LabelBinarizer()
        sa_labels = self.__speech_act_lb.fit_transform(sa_labels)

        self.__speech_act_model = Pipeline([
            ('vectorizer', CountVectorizer()),
            ('tfidf', TfidfTransformer()),
            ('clf', OneVsRestClassifier(LinearSVC(verbose=True)))])

        self.__speech_act_model.fit(sa_feats, sa_labels)

        with open('%s.act.model' % modelfile, 'wb') as f:
            pickle.dump((self.__speech_act_model, self.__speech_act_lb), f)

        self.__semantic_model = CRFTagger(verbose=True)
        self.__semantic_model.train(self.__semantic_instance_list, '%s.semantic.model' % modelfile)

    def pred(self, utter):
        tokenized = self.__tokenize(utter)
        word_feats = ' '.join([word.lower() for word, _ in tokenized])

        pred_act = self.__speech_act_lb.inverse_transform(self.__speech_act_model.predict([word_feats]))
        pred_semantic = self.__semantic_model.tag([word.lower() for word, _ in tokenized])

        return (pred_act, pred_semantic)

    def __tokenize(self, utter, semantic_tagged=None):
        result = None
        if semantic_tagged is None:
            result = [(word, None) for word in nltk.word_tokenize(utter)]
        else:
            parser_raw = SemanticTagParser(False)
            parser_tagged = SemanticTagParser(False)

            segmented = ' '.join(nltk.word_tokenize(utter))
            tagged = ' '.join(semantic_tagged)

            parser_raw.feed(segmented)
            parser_tagged.feed(tagged)

            raw_chr_seq = parser_raw.get_chr_seq()
            raw_space_seq = parser_raw.get_chr_space_seq()

            tagged_chr_seq = parser_tagged.get_chr_seq()
            tagged_space_seq = parser_tagged.get_chr_space_seq()

            if raw_chr_seq == tagged_chr_seq:
                merged_space_seq = [
                    x or y for x, y in zip(raw_space_seq, tagged_space_seq)]

                word_seq = parser_tagged.tokenize(merged_space_seq)
                tag_seq = parser_tagged.get_word_tag_seq()

                result = [(word, tag) for word, tag in zip(word_seq, tag_seq)]

        return result


class DirectLabelProjection:
    def __init__(self):
        pass

    def project(self, cn_utter, en_translated, align, en_tagged):
        cn_word_id_map = self.__get_char_word_map(cn_utter, [word for word, _ in align])
        en_word_id_map = self.__get_char_word_map(en_translated, en_translated.split())

        en_tagged_unit_id_map = self.__get_char_word_map(en_translated.lower(), [word for word, _ in en_tagged])

        result = {}

        for cn_idx in range(len(cn_word_id_map)):
            cn_chr = cn_utter[cn_idx]
            cn_word_id = cn_word_id_map[cn_idx]

            aligned_en_word_id_list = []
            if cn_word_id is not None:
                _, aligned_en_word_id_list = align[cn_word_id]

            projected_tag_count = {'O': 0}

            for en_word_id in aligned_en_word_id_list:
                for en_chr_id in self.__get_char_index_list(en_word_id_map, en_word_id):
                    en_tagged_unit_id = en_tagged_unit_id_map[en_chr_id]
                    if en_tagged_unit_id is not None:
                        _, tag = en_tagged[en_tagged_unit_id]
                        tag = tag.replace('B-', '').replace('I-', '')
                        if tag not in projected_tag_count:
                            projected_tag_count[tag] = 0
                        projected_tag_count[tag] += 1

            tags_w_max_freq = [key for key, val in projected_tag_count.iteritems() if key != 'O' and val == max(projected_tag_count.values())]

            if len(tags_w_max_freq) > 0:
                result[cn_idx] = {'char': cn_chr, 'tag': tags_w_max_freq[0]}
            else:
                result[cn_idx] = {'char': cn_chr, 'tag': None}

        return result

    def convert_to_tagged_utter(self, projection_result):
        result = ''
        prev_tag = None
        for idx in sorted(projection_result.keys()):
            char = projection_result[idx]['char']
            tag = projection_result[idx]['tag']

            if tag != prev_tag:
                if prev_tag is not None:
                    result += '</%s>' % (prev_tag.split('_')[0],)
                if tag is not None:
                    result += '<%s cat="%s">' % (tag.split('_')[0], tag.split('_')[1])

            result += char
            prev_tag = tag

        if prev_tag is not None:
            result += '</%s>' % (prev_tag.split('_')[0])

        return result

    def __get_char_index_list(self, word_id_map, word_id):
        result = []
        for idx in word_id_map:
            if word_id_map[idx] == word_id:
                result.append(idx)
        return sorted(set(result))

    def __get_char_word_map(self, utter, tokenized):
        chr_word_id_map = {}
        for idx in range(len(utter)):
            chr_word_id_map[idx] = None

        cur = 0
        for word_id in range(len(tokenized)):
            word = tokenized[word_id]
            pos = utter.find(word, cur)

            if pos >= 0:
                for idx in range(pos, pos+len(word)):
                    chr_word_id_map[idx] = word_id
                cur = pos + len(word)
        return chr_word_id_map


def main(argv):
    parser = argparse.ArgumentParser(description='Simple SLU baseline.')
    parser.add_argument('--trainset', dest='trainset', action='store', metavar='TRAINSET', required=True, help='The training dataset')
    parser.add_argument('--testset', dest='testset', action='store', metavar='TESTSET', required=True, help='The test dataset')
    parser.add_argument('--dataroot', dest='dataroot', action='store', required=True, metavar='PATH',  help='Will look for corpus in <destroot>/<dataset>/...')
    parser.add_argument('--modelfile', dest='modelfile', action='store', required=True, metavar='MODEL_FILE',  help='File to write with trained model')
    parser.add_argument('--outfile', dest='outfile', action='store', required=True, metavar='JSON_FILE',  help='File to write with SLU output')
    parser.add_argument('--roletype', dest='roletype', action='store', choices=['GUIDE',  'TOURIST'], required=True,  help='Target role')

    args = parser.parse_args()

    slu = SimpleSLU()

    trainset = dataset_walker.dataset_walker(args.trainset, dataroot=args.dataroot, labels=True, translations=True)
    sys.stderr.write('Loading training instances ... ')
    for call in trainset:
        for (log_utter, translations, label_utter) in call:
            if (log_utter['speaker'] == 'Guide' and args.roletype == 'GUIDE') or (log_utter['speaker'] == 'Tourist' and args.roletype == 'TOURIST'):
                slu.add_instance(log_utter['transcript'], label_utter['speech_act'], label_utter['semantic_tagged'])
    sys.stderr.write('Done\n')

    slu.train(args.modelfile)

    projection = DirectLabelProjection()

    output = {'sessions': []}
    output['dataset'] = args.testset
    output['task_type'] = 'SLU'
    output['role_type'] = args.roletype
    start_time = time.time()

    testset = dataset_walker.dataset_walker(args.testset, dataroot=args.dataroot, labels=False, translations=True)
    sys.stderr.write('Loading testing instances ... ')
    for call in testset:
        this_session = {"session_id": call.log["session_id"], "utterances": []}
        for (log_utter, translations, label_utter) in call:
            if (log_utter['speaker'] == 'Guide' and args.roletype == 'GUIDE') or (log_utter['speaker'] == 'Tourist' and args.roletype == 'TOURIST'):
                slu_result = {'utter_index': log_utter['utter_index']}
                if len(translations['translated']) > 0:
                    top_hyp = translations['translated'][0]['hyp']
                    pred_act, pred_semantic = slu.pred(top_hyp)

                    combined_act = {}
                    for act_label in reduce(operator.add, pred_act):
                        m = re.match('^([^_]+)_(.+)$', act_label)
                        act = m.group(1)
                        attr = m.group(2)
                        if act not in combined_act:
                            combined_act[act] = []
                        if attr not in combined_act[act]:
                            combined_act[act].append(attr)

                    slu_result['speech_act'] = []
                    for act in combined_act:
                        attr = combined_act[act]
                        slu_result['speech_act'].append({'act': act, 'attributes': attr})

                    align = translations['translated'][0]['align']

                    projected = projection.project(log_utter['transcript'], top_hyp, align, pred_semantic)
                    slu_result['semantic_tagged'] = projection.convert_to_tagged_utter(projected)
                else:
                    slu_result['semantic_tagged'] = log_utter['transcript']
                    slu_result['speech_act'] = []
                this_session['utterances'].append(slu_result)
        output['sessions'].append(this_session)

    end_time = time.time()
    elapsed_time = end_time - start_time
    output['wall_time'] = elapsed_time

    with open(args.outfile, "wb") as of:
        json.dump(output, of, indent=4)

    sys.stderr.write('Done\n')

if __name__ == "__main__":
    main(sys.argv)
