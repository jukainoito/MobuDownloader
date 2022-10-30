# coding:utf-8

import os
import re
from abc import ABCMeta, abstractmethod
from functools import wraps
from urllib import parse

import requests
import tqdm
import urllib3
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

urllib3.disable_warnings()


class MangaCrawler:
    __metaclass__ = ABCMeta

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/68.0.3440.106 Safari/537.36'}

    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    def __init__(self, saveDir='.', cookies=None, proxy=None, tqdmObj=None):
        self.saveDir = saveDir
        self.cookies = cookies
        self.proxy = proxy
        if tqdmObj is not None:
            self.tqdm = tqdmObj
        else:
            self.tqdm = tqdm
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
    async def download(self, info):
        pass


    @staticmethod
    def update_pbar(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            selfObj = args[0]
            result = await func(*args, **kwargs)
            if selfObj.pbar is not None:
                selfObj.pbar.update()
            return result
        return wrapper

    def webGet(self, url, params=None, scheme=None):
        if scheme is not None:
            urlParse = parse.urlparse(url)
            if len(urlParse.scheme) == 0:
                url = parse.urlunparse(urlParse._replace(scheme='https'))
        return self.session.get(url, params=params, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)


    @staticmethod
    def mkEpisodeDir(saveDir, title, episodeTitle):
        rstr = r"[\/\\\:\*\?\"\<\>\|]"
        newTitle = re.sub(rstr, '_', episodeTitle)
        episodeDir = os.path.join(saveDir, title, newTitle)
        if os.path.exists(os.path.normpath(episodeDir)):
            return episodeDir
        os.makedirs(os.path.normpath(episodeDir))
        return episodeDir
