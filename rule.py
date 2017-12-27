#!/usr/bin/env python2.7
# coding: utf-8


class Rule(object):
    def __init__(self, leave):
        self.leave = leave
        self.from_address = ''
        self.to_address = ''
        self.cc_address = ''
        self.subject = ''
        self.content = ''

    def __str__(self):
        return 'leave[{}], ' \
               'from_address[{}], ' \
               'to_address[{}], ' \
               'cc_address[{}], ' \
               'subject[{}], ' \
               'content[{}]'. \
            format(self.leave,
                   self.from_address,
                   self.to_address,
                   self.cc_address,
                   self.subject,
                   self.content)
