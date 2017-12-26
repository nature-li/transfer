#!/usr/bin/env python2.7
# coding: utf-8

import sys
import os
import time
import poplib
import json
import traceback
import getpass
import smtplib
from email.parser import Parser
from email.header import decode_header
from email.utils import parseaddr
from email.mime.base import MIMEBase
from py_log.logger import Logger, LogEnv

poplib._MAXLINE = 10 * 1024 * 1024


class FileDict(object):
    def __init__(self, file_name, stay_seconds):
        try:
            self.file_name = file_name
            self.stay_seconds = stay_seconds
            self.dict = dict()
            self.load_from_disk()
            self.update = False
        except:
            Logger.error(traceback.format_exc())

    def __del__(self):
        try:
            self.clear_dead()
            self.flush_to_disk()
        except:
            Logger.error(traceback.format_exc())

    def load_from_disk(self):
        try:
            with open(self.file_name, 'ab+') as content_file:
                content_file.seek(0, 0)
                content = content_file.read()
                if content:
                    self.dict = json.loads(content)
            return True
        except:
            Logger.error(traceback.format_exc())
            return False

    def flush_to_disk(self):
        try:
            if not self.update:
                return True
            self.update = False
            content = json.dumps(self.dict, ensure_ascii=False)
            with open(self.file_name, 'w') as content_file:
                content_file.write(content)
            return True
        except:
            Logger.error(traceback.format_exc())
            return False

    def exist(self, a_key):
        if isinstance(a_key, str):
            a_key = a_key.decode('utf-8')
        return a_key in self.dict

    def put(self, a_key):
        try:
            if isinstance(a_key, str):
                a_key = a_key.decode('utf-8')
            self.dict[a_key] = time.time()
            self.update = True
            return True
        except:
            Logger.error(traceback.format_exc())
            return False

    def clear_dead(self):
        try:
            now = time.time()
            for key, value in self.dict.items():
                stay = now - value
                if stay > self.stay_seconds:
                    del self.dict[key]
                    self.update = True
                    Logger.info('del self.dict[%s]' % key)
            return True
        except:
            Logger.error(traceback.format_exc())
            return False


class SomeMailInfo(object):
    def __init__(self):
        self.from_name = ''
        self.from_address = ''
        self.to_name = ''
        self.to_address = ''
        self.cc_name = ''
        self.cc_address = ''
        self.subject = ''
        self.content = ''
        self.child_mail = list()


class SingleMailFilter(object):
    def __init__(self):
        self.from_filter = set()
        self.to_filter = set()
        self.cc_filter = set()
        self.subject_filter = set()
        self.content_filter = set()
        self.send = False

    def __str__(self):
        msg = ''
        msg += 'from=' + ','.join(self.from_filter) + ';'
        msg += 'to=' + ','.join(self.to_filter) + ';'
        msg += "cc=" + ','.join(self.cc_filter) + ';'
        msg += 'subject=' + ','.join(self.subject_filter) + ';'
        msg += 'content=' + ','.join(self.content_filter) + ';'
        msg += 'send=' + str(self.send) + ';'
        return msg

    def empty(self):
        if len(self.from_filter) > 0:
            return False
        if len(self.to_filter) > 0:
            return False
        if len(self.cc_filter) > 0:
            return False
        if len(self.subject_filter) > 0:
            return False
        if len(self.content_filter) > 0:
            return False
        return True

    def add_from(self, value):
        fields = value.split(',')
        for field in fields:
            if field:
                self.from_filter.add(field)

    def add_to(self, value):
        fields = value.split(',')
        for field in fields:
            if field:
                self.to_filter.add(field)

    def add_cc(self, value):
        fields = value.split(',')
        for field in fields:
            if field:
                self.cc_filter.add(field)

    def add_subject(self, value):
        fields = value.split(',')
        for field in fields:
            if field:
                self.subject_filter.add(field)

    def add_content(self, value):
        fields = value.split(',')
        for field in fields:
            if field:
                self.content_filter.add(field)

    def add_send(self, value):
        if value == '0':
            self.send = False
        elif value == '1':
            self.send = True

    def filter(self, mail_info):
        match = self.match(mail_info)
        if match:
            return self.send

        return not self.send

    def match(self, mail_info):
        """
        :type mail_info: SomeMailInfo
        :return: boolean
        """
        for word in self.from_filter:
            if mail_info.from_address.find(word) == -1:
                return False

        for word in self.to_filter:
            if mail_info.to_address.find(word) == -1:
                return False

        for word in self.cc_filter:
            if mail_info.cc_address.find(word) == -1:
                return False

        for word in self.subject_filter:
            if mail_info.subject.find(word) == -1:
                return False

        for word in self.content_filter:
            if mail_info.content.find(word) == -1:
                return False

        return True


class MultipleMailFilter(object):
    def __init__(self):
        self.filter_list = list()
        """:type: list[SingleMailFilter]"""

    def init(self, strategy_file):
        try:
            with open(strategy_file, 'rb') as content_file:
                for line in content_file:
                    if not line:
                        continue
                    if line.startswith('#'):
                        continue
                    a_filter = self.get_filter(line)
                    if not a_filter:
                        continue
                    if not a_filter.empty():
                        Logger.info(str(a_filter))
                        self.filter_list.append(a_filter)
            return True
        except Exception, msg:
            Logger.error(msg)
            return False

    @classmethod
    def get_filter(cls, line):
        try:
            a_filter = SingleMailFilter()
            fields = line.split(';')
            for field in fields:
                if not field:
                    continue
                twice = field.split('=')
                if len(twice) != 2:
                    continue
                header = twice[0]
                value = twice[1]

                if header == 'from':
                    a_filter.add_from(value)

                if header == 'to':
                    a_filter.add_to(value)

                if header == 'subject':
                    a_filter.add_subject(value)

                if header == 'content':
                    a_filter.add_content(value)

                if header == 'send':
                    a_filter.add_send(value)

                if header == "cc":
                    a_filter.add_cc(value)
            return a_filter
        except:
            Logger.error(traceback.format_exc())
            return None

    def filter(self, mail_info):
        """
        :type mail_info: SomeMailInfo
        :return:
        """
        for single_filter in self.filter_list:
            # 有一个不发送则不发送
            if not single_filter.filter(mail_info):
                return False
        return True


class MailFilterProxy(object):
    def __init__(self, r_account, r_password, pop3_server,
                 s_account, s_password, smpt_server,
                 recorder, filters,
                 send_flag, target_account):
        self.r_account = r_account
        """:type: str"""
        self.r_password = r_password
        """:type: str"""
        self.pop3_server = pop3_server
        """:type: str"""
        self.s_account = s_account
        """:type: str"""
        self.s_password = s_password
        """:type: str"""
        self.smpt_server = smpt_server
        """:type: str"""
        self.target_account = target_account
        """:type: str"""
        self.recorder = recorder
        """:type: FileDict"""
        self.filters = filters
        """:type: MultipleMailFilter"""
        self.send_flag = send_flag
        """:type: bool"""
        self.pop3_session = None

    def __del__(self):
        self.close()

    def close(self):
        if self.pop3_session:
            self.pop3_session.quit()
            self.pop3_session = None

    def get_new_mail_ids(self):
        try:
            # 连接到POP3服务器:
            self.pop3_session = poplib.POP3(self.pop3_server)

            # 身份认证:
            self.pop3_session.user(self.r_account)
            self.pop3_session.pass_(self.r_password)

            # 获取邮件唯一编号
            resp, mails, octets = self.pop3_session.uidl()

            # 获取邮件唯一编号和在服务器中的索引
            mail_dict = dict()
            for mail_idx_id in mails:
                twice = mail_idx_id.split()
                mail_idx = int(twice[0])
                mail_id = twice[1]
                mail_dict[mail_idx] = mail_id

            # 过虑已读邮件
            for mail_idx, mail_id in mail_dict.items():
                if self.recorder.exist(mail_id):
                    del mail_dict[mail_idx]

            # 返回结果
            return mail_dict
        except:
            Logger.error(traceback.format_exc())
            return None

    def handle(self):
        try:
            # 获取邮件唯一编号
            mail_dict = self.get_new_mail_ids()

            # 依次处理所有邮件
            for mail_idx, mail_id in mail_dict.items():
                Logger.info("get mail[%s]" % mail_idx)
                resp, lines, octets = self.pop3_session.retr(mail_idx)
                msg_content = '\r\n'.join(lines)
                root = Parser().parsestr(msg_content)

                # 记录邮件
                self.recorder.put(mail_id)

                # 解析邮件
                mail_info = self.parse_mail(root)
                if not mail_info:
                    continue

                # 过滤邮件
                if not self.filters.filter(mail_info):
                    Logger.report("filter: idx[%s], id[%s], from[%s], to[%s], subject[%s]"
                                  % (mail_idx, mail_id, mail_info.from_address,
                                     mail_info.to_address, mail_info.subject))
                    continue

                # 发送邮件
                Logger.report("send: idx[%s], id[%s], from[%s], to[%s], subject[%s]"
                              % (mail_idx, mail_id, mail_info.from_address,
                                 mail_info.to_address, mail_info.subject))
                if self.send_flag:
                    self.send_mime(root)
                else:
                    Logger.report(mail_info.content)

                    # 调试用
                    # break

            # recorder内存刷到磁盘
            Logger.info("flush_to_disk")
            self.recorder.flush_to_disk()
        except:
            Logger.error(traceback.format_exc())

    @classmethod
    def decode_str(cls, content):
        value, charset = decode_header(content)[0]
        if charset:
            value = value.decode(charset)
        return value

    @classmethod
    def guess_charset(cls, root):
        try:
            # 先从root对象获取编码:
            charset = root.get_charset()
            if charset is None:
                # 如果获取不到，再从Content-Type字段获取:
                content_type = root.get('Content-Type', '').lower()
                pos = content_type.find('charset=')
                if pos >= 0:
                    charset = content_type[pos + 8:].strip()
            return charset
        except:
            Logger.error(traceback.format_exc())
            return None

    @classmethod
    def filter_mail(cls, mail_info):
        """
        :type mail_info: SomeMailInfo
        :return: boolean
        """

    # indent用于缩进显示:
    def parse_mail(self, root):
        try:
            mail_info = SomeMailInfo()

            # from
            value = root.get('From', '')
            header, mail_info.from_address = parseaddr(value)
            mail_info.from_name = self.decode_str(header)

            # to
            value = root.get('To', '')
            header, mail_info.to_address = parseaddr(value)
            mail_info.to_name = self.decode_str(header)

            # subject
            value = root.get('Subject', '')
            if value:
                mail_info.subject = self.decode_str(value)

            # cc
            value = root.get('Cc', '')
            header, mail_info.cc_address = parseaddr(value)
            if value:
                mail_info.cc_name = self.decode_str(value)

            # child MIMEMultipart
            if root.is_multipart():
                parts = root.get_payload()
                for n, part in enumerate(parts):
                    sub_mail_info = self.parse_mail(part)
                    mail_info.child_mail.append(sub_mail_info)
            else:
                content_type = root.get_content_type()
                if content_type == 'text/plain' or content_type == 'text/html':
                    # 纯文本或HTML内容:
                    content = root.get_payload(decode=True)
                    # 要检测文本编码:
                    charset = self.guess_charset(root)
                    if charset:
                        content = content.decode(charset)
                    mail_info.content = content
                    # 调试用
                    # Logger.report(mail_info.content)
                else:
                    # 不是文本,作为附件处理
                    pass
            return mail_info
        except:
            Logger.error(traceback.format_exc())
            return None

    def send_mime(self, root):
        """
        :type root: MIMEBase
        """
        try:
            # 显示原始信息
            for key in root.keys():
                raw_header = 'old_key[%s] ====> [%s]' % (key, root.get(key))
                Logger.info(raw_header)

            # 仅保留以下 Header
            left_header = ('from',
                           'boundary',
                           'content-type',
                           'mime-version',
                           'subject',
                           'date',
                           'message-id',
                           'content-transfer-encoding')
            for key in root.keys():
                little = key.lower()
                if little not in left_header:
                    del root[key]
                    Logger.info("delete key[%s]" % key)
            root['to'] = self.target_account

            # 打印新key
            # for key in root.keys():
            #     raw_header = 'new_key[%s] ====> [%s]' % (key, root.get(key))
            #     Logger.info(raw_header)

            # 发送邮件
            server = smtplib.SMTP(self.smpt_server, 25)
            server.login(self.s_account, self.s_password)
            server.sendmail(self.s_account, [self.target_account], root.as_string())
            server.quit()
        except:
            Logger.error(traceback.format_exc())


def loop_once(r_account, r_password, pop3_server,
              s_account, s_password, smpt_server,
              recorder_file, filter_file,
              send_flag, target_account,
              idx):
    """
    :type r_account: str
    :type r_password: str
    :type pop3_server: str
    :type s_account: str
    :type s_password: str
    :type recorder_file: str
    :type filter_file: str
    :type smpt_server: str
    :type send_flag: bool
    :type target_account: str
    :type idx: int
    :return:
    """
    try:
        # 打印标志
        Logger.info("-----------------------%s--------------------------" % idx)
        # 初始化已读邮件记录
        recorder = FileDict(recorder_file, stay_seconds=90 * 24 * 3600)

        # 初始化过滤策略
        filters = MultipleMailFilter()
        if not filters.init(filter_file):
            Logger.error("init mail filter error")
            return False

        # 初始化邮件 proxy
        proxy = MailFilterProxy(r_account, r_password, pop3_server,
                                s_account, s_password, smpt_server,
                                recorder, filters,
                                send_flag, target_account)
        proxy.handle()
    except:
        Logger.error(traceback.format_exc())


def __main__():
    # utf-8
    reload(sys)
    sys.setdefaultencoding('utf-8')

    # 日志目录
    log_target = raw_input("log directory: ")
    # 邮件过滤策
    filter_file = raw_input("filter file: ")
    # 收件账号
    r_account = raw_input("receive mail account: ")
    # 发件邮箱密码
    r_password = getpass.getpass('receive mail password: ')
    # 接收服务器
    pop3_server = raw_input("receive pop3 server: ")
    # 发件账号
    s_account = raw_input("send mail account: ")
    # 接收邮件密码
    s_password = getpass.getpass('send mail password: ')
    # 发送服务器
    smpt_server = raw_input("send mail smtp server: ")
    # 转发邮箱
    target_account = raw_input("target mail account: ")

    # 是否发送邮件
    input_flag = raw_input("send mail or not? [Y/N]:")
    input_flag = input_flag.upper()
    if input_flag != 'Y' and input_flag != 'N':
        print >> sys.stderr, "Invalid send_flag values, it must be Y or N"
        return False
    send_flag = True if input_flag == 'Y' else False

    print >> sys.stdout, "program is running in background, please check the running log!"

    # 初始化日志
    Logger.init(LogEnv.develop, log_target, "result", max_file_count=10)
    Logger.info("program is starting......")

    try:
        pid = os.fork()
        if pid > 0:
            Logger.info("#1 parent exit")
            os._exit(0)
    except:
        Logger.error(traceback.format_exc())

    try:
        pid = os.fork()
        if pid > 0:
            Logger.info("#2 parent exit")
            Logger.info("pid[%s] is running..." % pid)
            os._exit(0)
    except:
        Logger.error(traceback.format_exc())

    # 邮件记录文件
    self_dir = os.path.dirname(os.path.abspath(__file__))
    recorder_dir = os.path.join(self_dir, 'data')
    if not os.path.exists(recorder_dir):
        os.mkdir(recorder_dir)
    recorder_file = os.path.join(self_dir, 'data', 'transfer')

    # 循环接收邮件
    idx = 0
    while True:
        try:
            loop_once(r_account, r_password, pop3_server,
                      s_account, s_password, smpt_server,
                      recorder_file, filter_file,
                      send_flag, target_account,
                      idx)
            idx += 1
            time.sleep(60)
        except:
            pass


if __name__ == '__main__':
    __main__()
