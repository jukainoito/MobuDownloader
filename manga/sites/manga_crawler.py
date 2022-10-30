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

    def __init__(self, save_dir='.', cookies=None, proxy=None, tqdm_obj=None):
        self.save_dir = save_dir
        self.cookies = cookies
        self.proxy = proxy
        if tqdm_obj is not None:
            self.tqdm = tqdm_obj
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
    def get_info(self, url):
        pass

    @abstractmethod
    async def download(self, info):
        pass

    @staticmethod
    def update_pbar(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            self_obj = args[0]
            result = await func(*args, **kwargs)
            if self_obj.pbar is not None:
                self_obj.pbar.update()
            return result

        return wrapper

    def web_get(self, url, params=None, scheme=None):
        if scheme is not None:
            url_parse = parse.urlparse(url)
            if len(url_parse.scheme) == 0:
                url = parse.urlunparse(url_parse._replace(scheme='https'))
        return self.session.get(url, params=params, headers=self.headers, cookies=self.cookies, proxies=self.proxies,
                                verify=False)

    @staticmethod
    def mk_episode_dir(save_dir, title, episode_title):
        rstr = r"[\/\\\:\*\?\"\<\>\|]"
        new_title = re.sub(rstr, '_', episode_title)
        episode_dir = os.path.join(save_dir, title, new_title)
        if os.path.exists(os.path.normpath(episode_dir)):
            return episode_dir
        os.makedirs(os.path.normpath(episode_dir))
        return episode_dir
