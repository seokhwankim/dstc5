#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
__author__ = 'DSTC5'
__version__ = "$Revision: 1.0.4 $"

# Common python modules
import os
import sys
import string
import cPickle as pickle
from lm import ArpaLM
import bleu as bleu

try:
    import numpy as np
except:
    print "Error: Requires numpy from http://www.numpy.org/. Have you installed numpy?"
    sys.exit()

try:
    from sklearn.externals import joblib
    from sklearn.metrics.pairwise import cosine_similarity
except:
    print "Error: Requires sklearn from http://scikit-learn.org/. Have you installed scikit?"
    sys.exit()

# Important directories for the system
root_dir = './scripts/'

# Global variables

CONF_VALUES = {
    'en': {
        'FULL_AM_SIZE': 500,                    # Size of the trained AM model
        'OPT_AM_SIZE': 400,                     # Optimal value for the trained AM model
        'NGRAM_ORDER': 3,                       # Order the FM score calculation
    },
    'cn': {
        'FULL_AM_SIZE': 500,                    # Size of the trained AM model
        'OPT_AM_SIZE': 400,                     # Optimal value for the trained AM model
        'NGRAM_ORDER': 3,                       # Order the FM score calculation
    }
}

PREFIX_AM_FM = 'dstc5'              # Prefix for the AM-FM models

# Vector Space Model used by the AM score
class VSM:
    def __init__(self, model_file, size_am):
        self.am = None
        self.vectorizer = None
        self.load(model_file)
        self.am_components = self.am[:,0:size_am]

    def search(self, ref_sentences, test_sentences, lang='en'):
        """ search for documents that match based on a list of terms """

        assert len(ref_sentences) == len(test_sentences), "ERROR: the length of the reference (%d) and test (%d) " \
                                                          "sentences are not the same" % (len(ref_sentences),
                                                                                          len(test_sentences))
        # Monolingual search
        if lang != 'en':
            ref_sentences = [' '.join([' '.join([c for c in list(word.strip())]) for word in document.split()])
                             for document in ref_sentences]
            test_sentences = [' '.join([' '.join([c for c in list(word.strip())]) for word in document.split()])
                              for document in test_sentences]
        else:
            ref_sentences = [' '.join([word for word in document.split()]) for document in ref_sentences]
            test_sentences = [' '.join([word for word in document.split()]) for document in test_sentences]
        reference_vector = self.vectorizer.transform(ref_sentences)
        target_vector = self.vectorizer.transform(test_sentences)
        cosines = self.cosine_dist(target_vector, reference_vector)
        return cosines

    def cosine_dist(self, target, reference):
        """ related documents j and q are in the concept space by comparing the vectors :
            cosine  = ( V1 * V2 ) / ||V1|| x ||V2|| """
        tgt = np.matrix.dot(target.todense(), self.am_components)
        ref = np.matrix.dot(reference.todense(), self.am_components)
        return max(0.0, cosine_similarity(ref, tgt)[0])

    def load(self, name_model):
        print('Loading AM model')
        self.am = joblib.load(name_model + '.h5')
        file_h = open(name_model + '.dic', "rb")
        self.vectorizer = pickle.load(file_h)
        file_h.close()


class calcScoresBleuAMFM():
    def __init__(self, LANGUAGE='en'):

        # Check that the AM models exist
        self.full_am_size = CONF_VALUES[LANGUAGE]['FULL_AM_SIZE']
        self.opt_am_size = CONF_VALUES[LANGUAGE]['OPT_AM_SIZE']
        self.ngram_order = CONF_VALUES[LANGUAGE]['NGRAM_ORDER']

        am_full_matrix = root_dir + '/' + PREFIX_AM_FM + '.' + LANGUAGE + '.' + str(self.full_am_size)
        if not os.path.isfile(am_full_matrix + '.h5') or not os.path.isfile(am_full_matrix + '.dic'):
            print('******* ERROR: files: ' + am_full_matrix + '.h5 or ' + am_full_matrix + '.dic does not exists.')
            exit(-1)
        elif os.path.getsize(am_full_matrix + '.h5') == 0 or os.path.getsize(am_full_matrix + '.dic') == 0:
            print('******* ERROR: Check if files: ' + am_full_matrix + '.h5 or ' + am_full_matrix + '.dic are not empty.')
            exit(-1)

        # Check that the LM model exists
        lm_model = root_dir + '/' + PREFIX_AM_FM + '.' + LANGUAGE + '.' + str(self.ngram_order) + '.lm'
        if not os.path.exists(lm_model):
            print("******* ERROR: LM file " + lm_model + ' does not exists.')
            exit(-1)
        elif os.path.getsize(lm_model) == 0:
            print("******* ERROR: LM file " + lm_model + ' is empty.')
            exit(-1)

        # Load the models
        self.vs = VSM(am_full_matrix, self.opt_am_size)
        self.lm = ArpaLM(lm_model)

    def doProcessFromStrings(self, ref, pred, id=1, lang='en'):
        ref = self.preProcess(ref, lang)
        pred = self.preProcess(pred, lang)
        return ref, pred

    def preProcess(self, s, lang):
        if len(s) == 0:  # To avoid empty lines
            return '_EMPTY_'

        # Tokenization
        if lang != 'en':
            tokens = [[c for c in list(word.strip())] for word in s.split()][0]
        else:
            tokens = s.split()
        new_sent = []
        for token in tokens:
            if token.startswith("%"):
                continue
            if token.endswith("-"):
                token = token[:-1]
            new_sent.append(token)
        s = ' '.join(new_sent).lower()

        return s

    def calculateFMMetric(self, ref, tst, lang='en'):
        if lang == 'cn':
            ref = ' '.join(list(ref.strip()))
            tst = ' '.join(list(tst.strip()))
        sent = '<s> ' + ref.strip() + ' </s>'
        aWords = sent.split()
        num_words_ref = len(aWords) - 2
        prob_ref = 0.0
        # Calculates the log-prob for the different n-grams
        for i in range(1, len(aWords)):
            prob_ref += self.lm.score(tuple(aWords[max(0, i-self.ngram_order+1):i+1]))

        sent = '<s> ' + tst.strip() + ' </s>'
        aWords = sent.split()
        num_words_tst = len(aWords) - 2
        prob_tst = 0.0
        # Calculates the log-prob for the different n-grams
        for i in range(1, len(aWords)):
            prob_tst += self.lm.score(tuple(aWords[max(0, i-self.ngram_order+1):i+1]))

        # Calculate the scaled probability
        prob_ref = np.exp(prob_ref / num_words_ref)
        prob_tst = np.exp(prob_tst / num_words_tst)
        return 1.0 - ((max(prob_tst, prob_ref) - min(prob_tst, prob_ref))/max(prob_tst, prob_ref))

    def calculateBLEUMetric(self, ref, pred, lang='en'):
        return bleu.calculateBLEU(ref, pred, lang=lang)

    def calculateAMMetric(self, ref, pred, lang='en'):
        return min(1.0, self.vs.search([ref], [pred], lang=lang))