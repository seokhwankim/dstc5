# -*- coding: utf-8 -*-

"""
This module makes it easy to iterate through a dataset specified by file list (.flist) in scripts/config.
"""

import os
import json


class dataset_walker(object):
    def __init__(self, dataset, labels=False, translations=True, dataroot=None, task='MAIN', roletype=None):
        if "[" in dataset:
            self.datasets = json.loads(dataset)
        elif type(dataset) == type([]):
            self.datasets = dataset
        else:
            self.datasets = [dataset]
            self.dataset = dataset
        self.install_root = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
        self.dataset_session_lists = [os.path.join(self.install_root, 'config', dataset_id + '.flist') for dataset_id in self.datasets]

        self.labels = labels
        self.translations = translations

        if (dataroot == None):
            install_parent = os.path.dirname(self.install_root)
            self.dataroot = os.path.join(install_parent,'data')
        else:
            self.dataroot = os.path.join(os.path.abspath(dataroot))

        # load dataset (list of calls)
        self.session_list = []
        for dataset_session_list in self.dataset_session_lists:
            f = open(dataset_session_list)
            for line in f:
                line = line.strip()
                if (line in self.session_list):
                    raise RuntimeError,'Call appears twice: %s' % (line)
                self.session_list.append(line)
            f.close()

        if task == 'MAIN' or task == 'SLU':
            self.logfile = 'log.json'
            self.labelfile = 'label.json'
        elif task == 'SAP':
            if roletype == 'tourist':
                self.logfile = 'sap.tourist.in.json'
                self.labelfile = 'sap.tourist.label.json'
            elif roletype == 'guide':
                self.logfile = 'sap.guide.in.json'
                self.labelfile = 'sap.guide.label.json'
            else:
                raise RuntimeError, 'Wrong roletype argument: %s' % (roletype)
        elif task == 'SLG':
            if roletype == 'tourist':
                self.logfile = 'slg.tourist.in.json'
                self.labelfile = 'slg.tourist.label.json'
            elif roletype == 'guide':
                self.logfile = 'slg.guide.in.json'
                self.labelfile = 'slg.guide.label.json'
            else:
                raise RuntimeError, 'Wrong roletype argument: %s' % (roletype)
        else:
            raise RuntimeError, 'Wrong task identifier: %s' % (task)

    def __iter__(self):
        for session_id in self.session_list:
            session_id_list = session_id.split('/')
            session_dirname = os.path.join(self.dataroot, *session_id_list)
            applog_filename = os.path.join(session_dirname, self.logfile)

            if (self.translations):
                translations_filename = os.path.join(session_dirname, 'translations.json')
                if (not os.path.exists(translations_filename)):
                    raise RuntimeError,'Cant open translations file %s' % (translations_filename)
            else:
                translations_filename = None

            if (self.labels):
                labels_filename = os.path.join(session_dirname, self.labelfile)
                if (not os.path.exists(labels_filename)):
                    raise RuntimeError,'Cant score : cant open labels file %s' % (labels_filename)
            else:
                labels_filename = None

            call = Call(applog_filename, translations_filename, labels_filename)
            call.dirname = session_dirname
            yield call

    def __len__(self, ):
        return len(self.session_list)


class Call(object):
    def __init__(self, applog_filename, translations_filename, labels_filename):
        self.applog_filename = applog_filename
        self.translations_filename = translations_filename
        self.labels_filename = labels_filename

        f = open(applog_filename)
        self.log = json.load(f)
        f.close()

        if (translations_filename != None):
            f = open(translations_filename)
            self.translations = json.load(f)
            f.close()
        else:
            self.translations = None

        if (labels_filename != None):
            f = open(labels_filename)
            self.labels = json.load(f)
            f.close()
        else:
            self.labels = None

    def __iter__(self):
        if (self.translations_filename != None):
            if (self.labels_filename != None):
                for (log, translations, labels) in zip(self.log['utterances'], self.translations['utterances'], self.labels['utterances']):
                    if 'speech_act' in labels:
                        for i in range(len(labels['speech_act'])):
                            act = labels['speech_act'][i]['act'].strip().upper()
                            if act == '':
                                act = 'NONE'
                            labels['speech_act'][i]['act'] = act
                            for j in range(len(labels['speech_act'][i]['attributes'])):
                                attr = labels['speech_act'][i]['attributes'][j].strip()
                                if attr is None or attr == '':
                                    attr = 'NONE'
                                labels['speech_act'][i]['attributes'][j] = attr

                    yield (log, translations, labels)
            else:
                for (log, translations) in zip(self.log['utterances'], self.translations['utterances']):
                    yield (log, translations, None)
        else:
            if (self.labels_filename != None):
                for (log, labels) in zip(self.log['utterances'],self.labels['utterances']):
                    if 'speech_act' in labels:
                        for i in range(len(labels['speech_act'])):
                            act = labels['speech_act'][i]['act'].strip().upper()
                            if act == '':
                                act = 'NONE'
                            labels['speech_act'][i]['act'] = act
                            for j in range(len(labels['speech_act'][i]['attributes'])):
                                attr = labels['speech_act'][i]['attributes'][j].strip()
                                if attr is None or attr == '':
                                    attr = 'NONE'
                                labels['speech_act'][i]['attributes'][j] = attr

                    yield (log, None, labels)
            else:
                for log in self.log['utterances']:
                    yield (log, None, None)

    def __len__(self, ):
        return len(self.log['utterances'])
