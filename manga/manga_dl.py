# coding:utf-8

import json
import os, sys

from .sites import sites

from urllib.parse import urlparse

import logging

logger = logging.getLogger(__name__)

from tqdm import tqdm

import asyncio
class MangaDownloader(object):
    def __init__(self, sitesConfig, saveDir):
        self.saveDir = saveDir
        self.config = sitesConfig
        self.initCookies()
        self.manga = dict()

    def initCookies(self):
        for site in sites.keys():
            if self.config[site]['cookies_file'] is not None:
                self.config[site]['cookies'] = self.loadCookies(self.config[site]['cookies_file'], site)
            else :
                self.config[site]['cookies'] = None

    def loadCookies(self, cookiesFilePath, domain=None):
        cookies = {}
        try:
            temp, ext = os.path.splitext(cookiesFilePath)
            if ext.lower() == '.json':
                with open(cookiesFilePath, mode='r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for obj in data:
                            if domain == None or obj['domain'] == ('.' + domain):
                                cookies[obj['name']] = obj['value']
        except Exception:
            logger.error('Faild to load cookies file {}'.format(cookiesFilePath),exc_info = True)
        finally:
            if f:
                f.close()
        return cookies

    def getSite(self, url):
        urlParseRes = urlparse(url)
        site = urlParseRes.netloc
        return site

    def getMangaDL(self, url):
        site = self.getSite(url)
        if site not in sites.keys():
            print('Error: unsupport site')
            sys.exit(0)
        if site in self.manga.keys():
            mangaDL = self.manga[site]
        else:
            mangaCrawler = sites[site]
            mangaDL = mangaCrawler(self.saveDir,
                                   self.config[site]['cookies'], self.config[site]['proxy'])
            self.manga[site] = mangaDL
        return mangaDL

    def getInfo(self, url):
        mangaDL = self.getMangaDL(url)
        logger.info('Start get manga info: {}'.format(url))
        try:
            info = mangaDL.getInfo(url)
            info['site'] = self.getSite(url)
            logger.debug('url info: {}'.format(info))
            return info
        except:
            print('Parse error: {} '.format(url))
            sys.exit(-1)

        '''
        info = {
            'title':  manga title|string,
            'episode': pageSize|string,
            'url': page url|string,
            }
        '''
    def download(self, site, info):
        logger.info('Start download title: {}  episode: {} url: {}'.format(info['title'], info['episode'], info['raw']['url']))
        mangaDL = self.manga[site]
        print('Downloading: {} - {}'.format(info['title'], info['episode']))
        asyncio.run(mangaDL.download(info))
        logger.info('Download complete title: {}  episode: {}'.format(info['title'], info['episode']))
