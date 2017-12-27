#!/usr/bin/env python2.7
# coding: utf-8
import traceback
import json
import time
from pylog.logger import Logger


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
