#!/usr/bin/env python2.7
# coding: utf-8
import traceback
import sqlite3
import datetime
from pylog.logger import Logger


# CREATE TABLE mails (key TEXT PRIMARY KEY NOT NULL, time TEXT NOT NULL);
class DBDict(object):
    def __init__(self, file_name):
        try:
            self.file_name = file_name
            self.connection = sqlite3.connect(file_name)
        except:
            Logger.error(traceback.format_exc())

    def close(self):
        try:
            self.connection.close()
            return True
        except:
            Logger.error(traceback.format_exc())
            return False

    def exist(self, a_key):
        count = 0

        language = 'SELECT COUNT(1) AS count FROM mails WHERE key="%s"' % a_key
        cursor = self.connection.execute(language)
        for row in cursor:
            count = row[0]
        cursor.close()

        if count:
            count = int(count)
        else:
            count = 0

        return count > 0

    def put(self, a_key):
        try:
            language = 'INSERT OR REPLACE INTO mails(key, time) VALUES("%s", "%s")' % (a_key, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            cursor = self.connection.execute(language)
            cursor.execute(language)
            self.connection.commit()
            return True
        except:
            Logger.error(traceback.format_exc())
            return False
