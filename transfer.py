#!/usr/bin/env python2.7
# coding: utf-8

import sys
import os
import poplib
import traceback
import getpass
import smtplib
import time
from email.parser import Parser
from email.header import decode_header
from email.mime.base import MIMEBase
from pylog.logger import Logger, LogEnv
from file_dict import FileDict
from db_dict import DBDict
from mail_info import MailInfo
from filter import Filter
from email._parseaddr import AddressList

poplib._MAXLINE = 10 * 1024 * 1024


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
        """:type: DBDict"""
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

    def handle_one(self, mail_idx, mail_id):
        try:
            Logger.info("get mail[%s]" % mail_idx)
            resp, lines, octets = self.pop3_session.retr(mail_idx)
            msg_content = '\r\n'.join(lines)
            root = Parser().parsestr(msg_content)

            # 记录邮件
            self.recorder.put(mail_id)

            # 解析邮件
            mail_info = self.parse_mail(root)
            if not mail_info:
                return

            # 过滤邮件
            msg = "idx[{}], id[{}], from[{}], to[{}], cc[{}], subject[{}]". \
                format(mail_idx,
                       mail_id,
                       mail_info.from_address,
                       mail_info.to_address,
                       mail_info.cc_address,
                       mail_info.subject)

            if not self.filters.filter(mail_info):
                Logger.report("filter: " + msg)
                return

            # 发送邮件
            Logger.report("send: " + msg)
            if self.send_flag:
                self.send_mime(root)
            else:
                Logger.report(mail_info.content)
        except:
            Logger.error(traceback.format_exc())

    def handle(self):
        try:
            # 获取邮件唯一编号
            mail_dict = self.get_new_mail_ids()

            # 依次处理所有邮件
            for mail_idx, mail_id in mail_dict.items():
                self.handle_one(mail_idx, mail_id)

            # recorder内存刷到磁盘
            Logger.info("close sqlite")
            self.recorder.close()
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
    def parse_address(cls, addr):
        return AddressList(addr).addresslist

    # indent用于缩进显示:
    def parse_mail(self, root):
        try:
            mail_info = MailInfo()

            # from
            value = root.get('From', '')
            values = self.parse_address(value)
            if values:
                for (header, address) in values:
                    name = self.decode_str(header)
                    mail_info.from_name.add(name)
                    mail_info.from_address.add(address)

            # to
            value = root.get('To', '')
            values = self.parse_address(value)
            if values:
                for (header, address) in values:
                    name = self.decode_str(header)
                    mail_info.to_name.add(name)
                    mail_info.to_address.add(address)

            # cc
            value = root.get('Cc', '')
            values = self.parse_address(value)
            if values:
                for (header, address) in values:
                    name = self.decode_str(header)
                    mail_info.cc_name.add(name)
                    mail_info.cc_address.add(address)

            # subject
            value = root.get('Subject', '')
            if value:
                mail_info.subject = self.decode_str(value)

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
        recorder = DBDict(recorder_file)

        # 初始化过滤策略
        filters = Filter()
        if not filters.load(filter_file):
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
    log_target = "logs"
    # 邮件过滤策
    filter_file = "config/filter.xml"
    # 收件账号
    r_account = raw_input("receive mail account: ")
    # 收件密码
    r_password = getpass.getpass('receive mail password: ')
    # 接收服务器
    pop3_server = "pop.qiye.163.com"
    # 发件账号
    s_account = raw_input("send mail account: ")
    # 发件密码
    s_password = getpass.getpass('send mail password: ')
    # 发送服务器
    smpt_server = "smtp.163.com"
    # 转发邮箱
    target_account = raw_input("target mail account: ")

    # 非调试状态时获取用户输入
    # # 日志目录
    # log_target = raw_input("log directory: ")
    # # 邮件过滤策
    # filter_file = raw_input("filter file: ")
    # # 收件账号
    # r_account = raw_input("receive mail account: ")
    # # 发件密码
    # r_password = getpass.getpass('receive mail password: ')
    # # 接收服务器
    # pop3_server = raw_input("receive pop3 server: ")
    # # 发件账号
    # s_account = raw_input("send mail account: ")
    # # 发件密码
    # s_password = getpass.getpass('send mail password: ')
    # # 发送服务器
    # smpt_server = raw_input("send mail smtp server: ")
    # # 转发邮箱
    # target_account = raw_input("target mail account: ")

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

    # 非调试状态时在后台启动
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
    recorder_file = os.path.join(self_dir, 'data', 'transfer.db')

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
            # 非调试状态时循环转发邮件
            time.sleep(60)
            # 调试用
            # break
        except:
            Logger.error(traceback.format_exc())


if __name__ == '__main__':
    __main__()
