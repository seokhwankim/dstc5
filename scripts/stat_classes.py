# -*- coding: utf-8 -*-
from calc_amfm_bleu import calcScoresBleuAMFM


class Stat(object):
    def __init__(self,):
        pass

    def add(self, pred, ref):
        pass

    def results(self,):
        return []


class Stat_Accuracy(Stat):
    def __init__(self,):
        self.N = 0.0
        self.correct = 0.0

    def add(self, pred, ref, slot=None):
        if pred is not None and ref is not None:
            self.N += 1
            self.correct += int(pred == ref)

    def results(self,):
        acc = None
        if self.N > 0.0:
            acc = self.correct/self.N
        return [("acc", self.N, acc)]


class Stat_Precision_Recall(Stat):
    def __init__(self,):
        self.tp = 0.0
        self.fp = 0.0
        self.fn = 0.0

    def add(self, pred, ref, list_mode=False):
        if list_mode:
            for pred_obj in pred:
                if pred_obj in ref:
                    self.tp += 1
                else:
                    self.fp += 1
            for ref_obj in ref:
                if ref_obj not in pred:
                    self.fn += 1
        else:
            if pred is not None:
                self.tp += int(pred == ref)
                self.fp += int(pred != ref)
            if ref is not None:
                self.fn += int(pred != ref)

    def results(self,):
        precision = None
        recall = None
        fscore = None

        if (self.tp+self.fp) > 0.0:
            precision = self.tp/(self.tp+self.fp)
        if (self.tp+self.fn) > 0.0:
            recall = self.tp/(self.tp+self.fn)
        if precision is not None and recall is not None and (precision+recall) > 0.0:
            fscore = 2*precision*recall/(precision+recall)

        return [("precision", self.tp+self.fp, precision),("recall", self.tp+self.fn, recall), ("f1", self.tp+self.fp+self.fn, fscore)]


class Stat_Frame_Precision_Recall(Stat_Precision_Recall):
    def add(self, pred, ref):
        if pred is not None and ref is not None:
            pred_slot_value_list = []
            for s in pred:
                for v in pred[s]:
                    pred_slot_value_list.append((s, v))
            ref_slot_value_list = []
            for s in ref:
                for v in ref[s]:
                    ref_slot_value_list.append((s, v))

            for (s, v) in pred_slot_value_list:
                self.tp += int((s, v) in ref_slot_value_list)
                self.fp += int((s, v) not in ref_slot_value_list)
            for (s, v) in ref_slot_value_list:
                self.fn += int((s, v) not in pred_slot_value_list)


class Stat_BLEU_AM_FM(Stat):
    def __init__(self, lang):
        self.bleu = 0.0
        self.am_fm = 0.0
        self.alpha = 0.5
        self.num_sent = 0
        self.lang = lang
        self.cs = calcScoresBleuAMFM(LANGUAGE=lang)

    def add(self, pred, ref):
        self.num_sent += 1
        ref, pred = self.cs.doProcessFromStrings(ref, pred, self.num_sent, self.lang)
        b = self.cs.calculateBLEUMetric(ref, pred, lang=self.lang)[0][-1]
        self.bleu += b
        am = self.cs.calculateAMMetric(ref, pred, lang=self.lang)
        fm = self.cs.calculateFMMetric(ref, pred, lang=self.lang)
        am_fm = (self.alpha)*am + (1.0 - self.alpha)*fm
        self.am_fm += am_fm
        if self.lang != 'en':
            ref = ''.join(ref.split())
            pred = ''.join(pred.split())
        print('num:%d ref: %s | pred: %s | bleu: %f | am: %f | fm: %f | am_fm: %f' %(self.num_sent, ref, pred, b, am, fm, am_fm))

    def results(self,):
        return ("am_fm_avg", self.num_sent, self.am_fm/self.num_sent), ("bleu_avg", self.num_sent, self.bleu/self.num_sent)
