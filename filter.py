#!/usr/bin/env python2.7
# coding: utf-8
import xml.etree.ElementTree
from rule import Rule
import traceback
from mail_info import MailInfo
from pylog.logger import Logger


class Filter(object):
    def __init__(self):
        self.__leave = list()
        """:type: list[Rule]"""
        self.__discard = list()
        """:type: list[Rule]"""

    def __parse(self, e, leave):
        for item in e:
            rule = Rule(leave)
            for child in item:
                if child.tag == 'from':
                    rule.from_address = child.text
                if child.tag == 'to':
                    rule.to_address = child.text
                if child.tag == 'cc':
                    rule.cc_address = child.text
                if child.tag == 'subject':
                    rule.subject = child.text
                if child.tag == 'content':
                    rule.content = child.text
            if leave:
                self.__leave.append(rule)
            else:
                self.__discard.append(rule)
            Logger.info(str(rule))

    @classmethod
    def __match_rule(cls, rule, mail_info):
        """
        :type rule: Rule
        :type mail_info: MailInfo
        """
        if rule.from_address:
            from_address = ','.join(mail_info.from_address)
            if from_address.find(rule.from_address) == -1:
                return False
        if rule.to_address:
            to_address = ','.join(mail_info.to_address)
            if to_address.find(rule.to_address) == -1:
                return False
        if rule.cc_address:
            cc_address = ','.join(mail_info.cc_address)
            if cc_address.find(rule.cc_address) == -1:
                return False
        if rule.subject:
            if mail_info.subject.find(rule.subject) == -1:
                return False
        if rule.content:
            if mail_info.content.find(rule.content) == -1:
                return False
        return True

    def __is_leave(self, mail_info):
        for rule in self.__leave:
            if self.__match_rule(rule, mail_info):
                return True
        return False

    def __is_discard(self, mail_info):
        for rule in self.__discard:
            if self.__match_rule(rule, mail_info):
                return True
        return False

    def load(self, xml_file):
        try:
            root = xml.etree.ElementTree.parse(xml_file).getroot()
            for child in root:
                if child.tag == 'leave':
                    self.__parse(child, leave=True)

                if child.tag == 'discard':
                    self.__parse(child, leave=False)
            return True
        except:
            Logger.error(traceback.format_exc())
            return False

    def filter(self, mail_info):
        try:
            if not self.__is_leave(mail_info):
                return False
            if self.__is_discard(mail_info):
                return False
            return True
        except:
            Logger.error(traceback.format_exc())
            return True

