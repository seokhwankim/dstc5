# Dialog State Tracking Challenge 5 (DSTC5)

Dialog state tracking is one of the key sub-tasks of dialog management, which defines the representation of dialog states and updates them at each moment on a given on-going conversation. To provide a common testbed for this task, the first Dialog State Tracking Challenge (DSTC) was organized. More recently, Dialog State Tracking Challenges 2 & 3 and Dialog State Tracking Challenge 4 have been successfully completed.

In the fifth challenge, we will continue evaluating the dialog state tracking task on human-human dialogs. Different from DSTC4, in this challenge we will focus on cross-language DST. In addition to this main task, we also propose a series of pilot tracks for the core components in developing end-to-end dialog systems based on the same dataset.

More details about the challenge can be found from the official website (http://workshop.colips.org/dstc5/index.html).

This repository provides the resources including evaluation scripts, ontology, and handbooks for the challenge participants.

## Getting started

Clone this repository into your working directory.
``` shell
$ git clone https://github.com/seokhwankim/dstc5.git
$ cd dstc5/
```
Download the archived datasets from the link provided to each registered participant and extract the files into 'data/' directory.
``` shell
$ tar xvfz dstc5_train_dev.tar.gz
```
Install *python-levenshtein* and *fuzzywuzzy* which is a prerequisite for the baseline tracker.
``` shell
$ pip install python-levenshtein
$ pip install fuzzywuzzy
```
Run the baseline tracker (with method 1).
``` shell
$ python scripts/baseline.py --dataset dstc5_dev --dataroot data --trackfile baseline_dev.json --ontology scripts/config/ontology_dstc5.json --method 1
```
Check the structure and contents of the tracker output.
``` shell
$ python scripts/check_main.py --dataset dstc5_dev --dataroot data --ontology scripts/config/ontology_dstc5.json --trackfile baseline_dev.json
Found no errors, trackfile is valid
```
Evaluate the output.
``` shell
$ python scripts/score_main.py --dataset dstc5_dev --dataroot data --trackfile baseline_dev.json --scorefile baseline_dev.score.csv --ontology scripts/config/ontology_dstc5.json
```
Print out the summarized results.
``` shell
$ python scripts/report_main.py --scorefile baseline_dev.score.csv

                       featured metrics
--------------------------------------------------------------
                    |   all.schedule1    |   all.schedule2   |
--------------------------------------------------------------
segment.accuracy    |     0.0388305      |     0.0497738     |
slot_value.precision|     0.2091008      |     0.2091691     |
slot_value.recall   |     0.1142012      |     0.1492843     |
slot_value.fscore   |     0.1477229      |     0.1742243     |



                                    basic stats
-----------------------------------------------------------------------------------
                  dataset : dstc5_dev
                 sessions : 2
          total_wall_time : 23.1418588161
               utterances : 3130
  wall_time_per_utterance : 0.00739356511698
```

## Contact Information
You can get the latest updates and participate in discussions on DSTC mailing list

To join the mailing list, send an email to: (listserv@lists.research.microsoft.com)
putting "subscribe DSTC" in the body of the message (without the quotes).
To post a message, send your message to: (dstc@lists.research.microsoft.com).
