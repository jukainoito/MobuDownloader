# coding:utf-8

from abc import ABCMeta, abstractmethod
import os

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import urllib3
urllib3.disable_warnings()

class MangaCrawler:
    __metaclass__ = ABCMeta

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'}

    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    def __init__(self, saveDir='.', cookies=None, proxy=None):
        self.saveDir = saveDir
        self.cookies = cookies
        self.proxy = proxy
        if self.proxy is not None:
            self.proxies = {
                'http': self.proxy,
                'https': self.proxy
            }
        else:
            self.proxies = None

    @abstractmethod
    def getInfo(self, url):
        pass

    @abstractmethod
    def download(self, info):
        pass


    @staticmethod
    def mkEpisodeDir(saveDir, title, episodeTitle):
        episodeDir = os.path.join(saveDir, title, episodeTitle)
        if os.path.exists(os.path.normpath(episodeDir)):
            return episodeDir
        os.makedirs(os.path.normpath(episodeDir))
        return episodeDir
