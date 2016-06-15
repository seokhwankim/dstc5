#!/usr/bin/python

# $Id: bleu.py 1307 2007-03-14 22:22:36Z hieuhoang1972 $


# For DSTC5 we have introduced some changes to allow calculating the score for each sentence. All changes start with the
# word DSTC5

'''Provides:

cook_refs(refs, n=4): Transform a list of reference sentences as strings into a form usable by cook_test().
cook_test(test, refs, n=4): Transform a test sentence as a string (together with the cooked reference sentences) into a form usable by score_cooked().
score_cooked(alltest, n=4): Score a list of cooked test sentences.

score_set(s, testid, refids, n=4): Interface with dataset_bleu.py; calculate BLEU score of testid against refids.

The reason for breaking the BLEU computation into three phases cook_refs(), cook_test(), and score_cooked() is to allow the caller to calculate BLEU scores for multiple test sets as efficiently as possible.
'''

import optparse
import sys, math, re, xml.sax.saxutils
#sys.path.append('/fs/clip-mteval/Programs/hiero')
import dataset_bleu  # DSTC5: Changed name
#import log

# Added to bypass NIST-style pre-processing of hyp and ref files -- wade
nonorm = 0

preserve_case = False
eff_ref_len = "shortest"

normalize1 = [
    ('<skipped>', ''),         # strip "skipped" tags
    (r'-\n', ''),              # strip end-of-line hyphenation and join lines
    (r'\n', ' '),              # join lines
#    (r'(\d)\s+(?=\d)', r'\1'), # join digits
]
normalize1 = [(re.compile(pattern), replace) for (pattern, replace) in normalize1]

normalize2 = [
    (r'([\{-\~\[-\` -\&\(-\+\:-\@\/])',r' \1 '), # tokenize punctuation. apostrophe is missing
    (r'([^0-9])([\.,])',r'\1 \2 '),              # tokenize period and comma unless preceded by a digit
    (r'([\.,])([^0-9])',r' \1 \2'),              # tokenize period and comma unless followed by a digit
    (r'([0-9])(-)',r'\1 \2 ')                    # tokenize dash when preceded by a digit
]
normalize2 = [(re.compile(pattern), replace) for (pattern, replace) in normalize2]


def normalize(s):
    '''Normalize and tokenize text. This is lifted from NIST mteval-v11a.pl.'''
    # Added to bypass NIST-style pre-processing of hyp and ref files -- wade
    if (nonorm):
        return s.split()
    if type(s) is not str:
        s = " ".join(s)
    # language-independent part:
    for (pattern, replace) in normalize1:
        s = re.sub(pattern, replace, s)
    s = xml.sax.saxutils.unescape(s, {'&quot;':'"'})
    # language-dependent part (assuming Western languages):
    s = " %s " % s
    if not preserve_case:
        s = s.lower()         # this might not be identical to the original
    for (pattern, replace) in normalize2:
        s = re.sub(pattern, replace, s)
    return s.split()


def count_ngrams(words, n=4):
    counts = {}
    for k in xrange(1,n+1):
        for i in xrange(len(words)-k+1):
            ngram = tuple(words[i:i+k])
            counts[ngram] = counts.get(ngram, 0)+1
    return counts


def cook_refs(refs, n=4):
    '''Takes a list of reference sentences for a single segment
    and returns an object that encapsulates everything that BLEU
    needs to know about them.'''

    refs = [normalize(ref) for ref in refs]
    maxcounts = {}
    for ref in refs:
        counts = count_ngrams(ref, n)
        for (ngram,count) in counts.iteritems():
            maxcounts[ngram] = max(maxcounts.get(ngram,0), count)
    return ([len(ref) for ref in refs], maxcounts)


def cook_test(test, (reflens, refmaxcounts), n=4):
    '''Takes a test sentence and returns an object that
    encapsulates everything that BLEU needs to know about it.'''

    test = normalize(test)
    result = {}
    result["testlen"] = len(test)

    # DSTC5: To skip empty lines
    if len(test) == 0:
        result["testlen"] = 1  # DSTC5: This trick avoids the system to crash


    # Calculate effective reference sentence length
    if eff_ref_len == "shortest":
        result["reflen"] = min(reflens)
    elif eff_ref_len == "average":
        result["reflen"] = float(sum(reflens))/len(reflens)
    elif eff_ref_len == "closest":
        min_diff = None
        for reflen in reflens:
            if min_diff is None or abs(reflen-len(test)) < min_diff:
                min_diff = abs(reflen-len(test))
                result['reflen'] = reflen

    result["guess"] = [max(len(test)-k+1,0) for k in xrange(1,n+1)]

    result['correct'] = [0]*n
    counts = count_ngrams(test, n)
    for (ngram, count) in counts.iteritems():
        result["correct"][len(ngram)-1] += min(refmaxcounts.get(ngram,0), count)

    return result


def score_cooked(allcomps, n=4):
    totalcomps = {'testlen':0, 'reflen':0, 'guess':[0]*n, 'correct':[0]*n}
    for comps in allcomps:
        for key in ['testlen','reflen']:
            totalcomps[key] += comps[key]
        for key in ['guess','correct']:
            for k in xrange(n):
                totalcomps[key][k] += comps[key][k]
    logbleu = 0.0
    for k in xrange(n):
        if totalcomps['correct'][k] == 0:
            return 0.0
        # log.write("%d-grams: %f\n" % (k,float(totalcomps['correct'][k])/totalcomps['guess'][k]))  # DSTC5: Commented out to have a cleaner output
        logbleu += math.log(totalcomps['correct'][k])-math.log(totalcomps['guess'][k])
    logbleu /= float(n)
    # log.write("Effective reference length: %d test length: %d\n" % (totalcomps['reflen'], totalcomps['testlen']))  # DSTC5: Commented out to have a cleaner output
    logbleu += min(0,1-float(totalcomps['reflen'])/totalcomps['testlen'])
    return math.exp(logbleu)


# DSTC5: Introduced to keep track of the score for each sentence. It is based on score_cooked function
def score_cooked_per_sentence(allcomps, n=4):
    bleu_scores = []
    for comps in allcomps:
        totalcomps = {'testlen':0, 'reflen':0, 'guess':[0]*n, 'correct':[0]*n}
        for key in ['testlen','reflen']:
            totalcomps[key] = comps[key]
        for key in ['guess','correct']:
            for k in xrange(n):
                totalcomps[key][k] = comps[key][k]

        logbleu = 0.0
        bleu_per_ngram = []
        num_ngram = 0
        for k in xrange(n):
            if totalcomps['correct'][k] == 0:
                bleu_per_ngram.append(0.0)
                num_ngram += 1
                continue
            num_ngram += 1
            bleu_per_ngram.append(float(totalcomps['correct'][k]+1)/(totalcomps['guess'][k]+1))  # DSTC5: Smoothed BLEU
            logbleu += math.log(totalcomps['correct'][k]+1)-math.log(totalcomps['guess'][k]+1)   # DSTC5: Smoothed BLEU

        if logbleu == 0.0 and max(bleu_per_ngram) == 0.0:  # There was not any match between both sentences, then return 0.0
            bleu_per_ngram.append(0.0)
        elif num_ngram > 0:
            logbleu /= float(num_ngram)
            # log.write("Effective reference length: %d test length: %d\n" % (totalcomps['reflen'], totalcomps['testlen'])) # DSTC5: Commented out to have a cleaner output
            logbleu += min(0, 1.0-float(totalcomps['reflen'])/(totalcomps['testlen']))
            bleu_per_ngram.append(math.exp(logbleu))
        else:
            bleu_per_ngram.append(0.0)
        bleu_scores.append(bleu_per_ngram)
    return bleu_scores


def score_set(set, testid, refids, n=4):
    alltest = []
    for seg in set.segs():
        try:
            test = seg.versions[testid].words
        except KeyError:
            #log.write("Warning: missing test sentence\n")
            print("Warning: missing test sentence\n")
            continue
        try:
            refs = [seg.versions[refid].words for refid in refids]
        except KeyError:
            #log.write("Warning: missing reference sentence, %s\n" % seg.id)
            print("Warning: missing reference sentence, %s\n" % seg.id)
        refs = cook_refs(refs, n)
        r = cook_test(test, refs, n)
        if r is not None:  # Avoid empty lines
            alltest.append(r)
    # log.write("%d sentences\n" % len(alltest))
    # bleu_global = score_cooked(alltest, n)
    # print 'BLEU Global=' + str(bleu_global)
    return score_cooked_per_sentence(alltest, n)


# DSTC5: Allows the module to be call from another script. By default we read raw_test.
# This function is based on the process done in the main function
def calculateBLEU(ref, tst, lang='en', pc=False, ngram_order=4):
    global preserve_case
    s = dataset_bleu.Dataset()
    if pc is True:
        preserve_case = pc

    if lang == 'cn':
        ref = ' '.join(list(ref.strip()))
        tst = ' '.join(list(tst.strip()))

    (root, refids) = s.add_sent(ref, docid='whatever', sysid='refsys')
    (root, testid) = s.add_sent(tst, docid='whatever', sysid='testsys')
    return score_set(s, testid[0], refids, ngram_order)

if __name__ == "__main__":
    # import psyco  # DSTC5: Commented as they are just to optimize the calculation process
    # psyco.full()

    import getopt
    raw_test = False
    (opts, args) = getopt.getopt(sys.argv[1:], "rc", [])
    for (opt,parm) in opts:
        if opt == "-r":
            raw_test = True
        elif opt == "-c":
            preserve_case = True

    s = dataset_bleu.Dataset()
    if args[0] == '-':
        infile = sys.stdin
    else:
        infile = args[0]

    if raw_test:
        (root, testids) = s.read_raw(infile, docid='whatever', sysid='testsys')
    else:
        (root, testids) = s.read(infile)
    print "Test systems: %s" % ", ".join(testids)

    if raw_test: # Included to allow reading raw information for the reference file too
        (root, refids) = s.read_raw(args[1], docid='whatever', sysid='refsys')
    else:
        (root, refids) = s.read(args[1])

    print "Reference systems: %s" % ", ".join(refids)

    for testid in testids:
        print "BLEU score: ", score_set(s, testid, refids)
