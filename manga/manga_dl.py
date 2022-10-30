# coding:utf-8

import asyncio
import json
import logging
import os
import sys
from urllib.parse import urlparse

from .sites import sites

logger = logging.getLogger(__name__)


class MangaDownloader(object):
    def __init__(self, sites_config, save_dir, default_proxy=None):
        self.save_dir = save_dir
        self.config = sites_config
        self.default_proxy = default_proxy
        self.init_cookies()
        self.manga = dict()

    def init_cookies(self):
        for site in sites.keys():
            if site not in self.config:
                self.config[site] = {
                    'proxy': self.default_proxy,
                    'cookies_file': None
                }
            if self.config[site]['cookies_file'] is not None:
                self.config[site]['cookies'] = self.load_cookies(self.config[site]['cookies_file'], site)
            else:
                self.config[site]['cookies'] = None

    @staticmethod
    def load_cookies(self, cookies_file_path, domain=None):
        cookies = {}
        try:
            temp, ext = os.path.splitext(cookies_file_path)
            if ext.lower() == '.json':
                with open(cookies_file_path, mode='r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for obj in data:
                            if domain is None or obj['domain'] == ('.' + domain):
                                cookies[obj['name']] = obj['value']
        except Exception:
            logger.error('Failed to load cookies file {}'.format(cookies_file_path), exc_info=True)
        finally:
            if f:
                f.close()
        return cookies

    @staticmethod
    def get_site(url):
        url_parse_res = urlparse(url)
        site = url_parse_res.netloc
        return site

    def get_manga_dl(self, url):
        site = self.get_site(url)
        if site not in sites.keys():
            print('Error: unsupported site')
            sys.exit(0)
        if site in self.manga.keys():
            manga_dl = self.manga[site]
        else:
            manga_crawler = sites[site]
            manga_dl = manga_crawler(self.save_dir,
                                     self.config[site]['cookies'], self.config[site]['proxy'])
            self.manga[site] = manga_dl
        return manga_dl

    def get_info(self, url):
        manga_dl = self.get_manga_dl(url)
        logger.info('Start get manga info: {}'.format(url))
        try:
            info = manga_dl.get_info(url)
            info['site'] = self.get_site(url)
            logger.debug('url info: {}'.format(info))
            return info
        except Exception as e:
            print('Parse error: {} '.format(url))
            raise e
            # sys.exit(-1)

        '''
        info = {
            'title':  manga title|string,
            'episode': pageSize|string,
            'url': page url|string,
            }
        '''

    def download(self, site, info):
        logger.info(
            'Start download title: {}  episode: {} url: {}'.format(info['title'], info['episode'], info['raw']['url']))
        manga_dl = self.manga[site]
        print('Downloading: {} - {}'.format(info['title'], info['episode']))
        asyncio.run(manga_dl.download(info))
        logger.info('Download complete title: {}  episode: {}'.format(info['title'], info['episode']))
