import argparse
import sys
import os
import json


def main(argv):
    install_path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    utils_dirname = os.path.join(install_path,'lib')

    sys.path.append(utils_dirname)
    from dataset_walker import dataset_walker
    from eval_func import eval_utt
    from stat_classes import Stat_BLEU_AM_FM

    parser = argparse.ArgumentParser(
        description='Evaluate output from an SLG system.')
    parser.add_argument('--dataset', dest='dataset',
                        action='store', metavar='DATASET', required=True,
                        help='The dataset to analyze')
    parser.add_argument('--dataroot', dest='dataroot',
                        action='store', metavar='PATH', required=True,
                        help='look for corpus in <destroot>/...')
    parser.add_argument('--jsonfile', dest='jsonfile',
                        action='store', metavar='JSON_FILE', required=True,
                        help='File containing JSON output')
    parser.add_argument('--roletype', dest='roletype',
                        action='store', required=True,
                        choices=['GUIDE', 'TOURIST'], help='Target role')
    parser.add_argument('--scorefile', dest='scorefile',
                        action='store', metavar='JSON_FILE', required=True,
                        help='File to write with CSV scoring data')

    args = parser.parse_args()

    sessions = dataset_walker(
        args.dataset, dataroot=args.dataroot, labels=True,
        task='SLG', roletype=args.roletype.lower())

    system_output = json.load(open(args.jsonfile))

    stats = {}
    stats['generated'] = {}
    stats['generated']['all'] = Stat_BLEU_AM_FM('cn')

    for session, track_session in zip(sessions, system_output["sessions"]):
        log_utter_list = []
        label_utter_list = []

        for log_utter, translations, label_utter in session:
            if (args.roletype == 'GUIDE' and log_utter['speaker'] == 'Guide') or (args.roletype == 'TOURIST' and log_utter['speaker'] == 'Tourist'):
                log_utter_list.append(log_utter)
                label_utter_list.append(label_utter)

        # now iterate through turns
        for log_utter, label_utter, track_utter in zip(log_utter_list, label_utter_list, track_session["utterances"]):
            for subtask in stats:
                if subtask == 'generated':
                    ref = label_utter['transcript']
                    pred = track_utter['generated']
                    eval_utt(ref, pred, stats[subtask])

    csvfile = open(args.scorefile,'w')
    print >> csvfile,("task, subtask, schedule, stat, N, result")

    for subtask in stats:
        for schedule in stats[subtask]:
            for measure, N, result in stats[subtask][schedule].results():
                print >>csvfile, ("%s, %s, %s, %s, %i, %s" % (
                    'SLG', subtask, schedule, measure, N, result))
    csvfile.close()


if __name__ == '__main__':
    main(sys.argv)
