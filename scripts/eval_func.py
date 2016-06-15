# -*- coding: utf-8 -*-

from semantic_tag_parser import SemanticTagParser
from HTMLParser import HTMLParseError


def eval_acts(ref_act_objs, pred_act_objs, stat_acts):
    ref_act_tag_list = []
    ref_act_attr_list = []
    for act_obj in ref_act_objs:
        act_tag = act_obj['act']
        ref_act_tag_list.append(act_tag)
        for attr in act_obj['attributes']:
            ref_act_attr_list.append((act_tag, attr))

    ref_act_tag_list = sorted(set(ref_act_tag_list))
    ref_act_attr_list = sorted(set(ref_act_attr_list))

    pred_act_tag_list = []
    pred_act_attr_list = []
    for act_obj in pred_act_objs:
        act_tag = act_obj['act']
        pred_act_tag_list.append(act_tag)
        for attr in act_obj['attributes']:
            pred_act_attr_list.append((act_tag, attr))

    pred_act_tag_list = sorted(set(pred_act_tag_list))
    pred_act_attr_list = sorted(set(pred_act_attr_list))

    if 'act' in stat_acts:
        stat_acts['act'].add(
            pred_act_tag_list, ref_act_tag_list, list_mode=True)
    if 'all' in stat_acts:
        stat_acts['all'].add(
            pred_act_attr_list, ref_act_attr_list, list_mode=True)


def eval_semantics(ref_tagged, pred_tagged, stat_semantics):
    parser_ref = SemanticTagParser()
    parser_pred = SemanticTagParser()
    try:
        parser_ref.feed(ref_tagged)
        ref_chr_seq = parser_ref.get_chr_seq()
        ref_space_seq = parser_ref.get_chr_space_seq()

        parser_pred.feed(pred_tagged)
        pred_chr_seq = parser_pred.get_chr_seq()
        pred_space_seq = parser_pred.get_chr_space_seq()

        if ref_chr_seq != pred_chr_seq:
            raise

        merged_space_seq = [
            x or y for x, y in zip(ref_space_seq, pred_space_seq)]

        parser_ref.tokenize(merged_space_seq)
        parser_pred.tokenize(merged_space_seq)

        ref_word_tag_seq = parser_ref.get_word_tag_seq()
        pred_word_tag_seq = parser_pred.get_word_tag_seq()

        for ref_tuple, pred_tuple in zip(ref_word_tag_seq, pred_word_tag_seq):
            ref_bio, ref_tag, ref_attrs = ref_tuple
            pred_bio, pred_tag, pred_attrs = pred_tuple

            pred_obj = None
            ref_obj = None            

            if pred_bio is not None:
                pred_obj = {'bio': pred_bio}
            if ref_bio is not None:
                ref_obj = {'bio': ref_bio}

            if 'detection' in stat_semantics:
                stat_semantics['detection'].add(pred_obj, ref_obj)

            if pred_obj is not None and pred_tag is not None:
                pred_obj['tag'] = pred_tag
            if ref_obj is not None and ref_tag is not None:
                ref_obj['tag'] = ref_tag

            if 'class' in stat_semantics:
                stat_semantics['class'].add(pred_obj, ref_obj)

            if pred_obj is not None and pred_attrs is not None:
                for (s, v) in pred_attrs:
                    if v != 'NONE':
                        pred_obj[s] = v

            if ref_obj is not None and ref_attrs is not None:
                for (s, v) in ref_attrs:
                    if v != 'NONE':
                        ref_obj[s] = v

            if 'all' in stat_semantics:
                stat_semantics['all'].add(pred_obj, ref_obj)

        parser_ref.close()
        parser_pred.close()
    except HTMLParseError, err:
        print "HTMLParseError: %s" % err


def eval_utt(ref, pred, stat_text):
    stat_text['all'].add(ref, pred)
