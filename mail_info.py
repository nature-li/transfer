#!/usr/bin/env python2.7
# coding: utf-8


class MailInfo(object):
    def __init__(self):
        self.from_name = set()
        self.from_address = set()
        self.to_name = set()
        self.to_address = set()
        self.cc_name = set()
        self.cc_address = set()
        self.subject = ''
        self.content = ''
        self.child_mail = list()

    def __str__(self):
        return 'from_address={}, ' \
               'to_address={}, ' \
               'cc_address={}, ' \
               'subject={}'. \
            format(self.from_address,
                   self.to_address,
                   self.cc_address,
                   self.subject)
