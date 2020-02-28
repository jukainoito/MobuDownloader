# coding:utf-8

from .manga_crawler import MangaCrawler
# from urllib.parse import urlparse
# from urllib.parse import parse_qs
from string import Template
import re
import json
import six
import os
from lxml import etree

import logging

logger = logging.getLogger(__name__)

class MangaWalker(MangaCrawler):

    apiUrlTemp = Template('https://ssl.seiga.nicovideo.jp/api/v1/comicwalker/episodes/${cid}/frames')

    xpath = {
        "title": '//*[@id="detailIndex"]/div/h1/text()',
        "episodes": '//*[@id="reversible"]/li',
        "episode_title": './div/div/span/text()',
        "episode_url": './a/@href'
    }

    def getEpisodeInfo(self, url):
        r = self.session.get(url, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)
        scriptStr = ''.join(html.xpath('/html/head/script[1]/text()'))
        jsonData = scriptStr[scriptStr.find('['): scriptStr.rfind(']')+1]
        episodeInfo = json.loads(jsonData)
        title = episodeInfo[0]["content_title"]
        episodes = list(map(lambda episode: {"episode": episode["episode_title"],
                                             "pageSize": "", "raw": episode}, episodeInfo))
        return {
            "title": title,
            "episodes": episodes,
            "extend": {
                "content_id": episodeInfo[0]["contentID"]
            }
        }

    def getMangaInfo(self, url):
        r = self.session.get(url, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['title']))
        episodes = []

        episodesEtree = html.xpath(self.xpath['episodes'])
        for episode in episodesEtree:
            episodeTitle = ''.join(episode.xpath(self.xpath['episode_title']))
            episodeUrl = ''.join(episode.xpath(self.xpath['episode_url']))
            episodes.append({
                "episode": episodeTitle,
                "pageSize": "", "raw": {
                    "url": episodeUrl,
                    "episode_id": re.match(".*cid=([A-Za-z0-9_]*)", episodeUrl).group(1)
                }
            })
        return {
            "title": title,
            "episodes": episodes,
            "extend": {
                "content_id": re.match(".*/([^/]+)/?$", url).group(1)
            }
        }

    def getImageData(self, cid):
        apiUrl = self.apiUrlTemp.substitute(cid=cid)
        r = self.session.get(apiUrl, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)
        apiData = json.loads(r.text)
        if apiData['meta']['status'] == 200:
            return apiData['data']['result']
        else:
            raise RuntimeError('接口调用失败')

    @staticmethod
    def genKey(hashStr):
        m = re.findall(r'[\da-f]{2}', hashStr[0:16])
        key = b''
        for i in m:
            key += six.int2byte(int(i, 16))
        return key

    @staticmethod
    def saveImage(savePath, data):
        open(savePath, 'wb').write(data)

    def downloadImage(self, imageInfo, episodeDir):

        imageKey = self.genKey(imageInfo['meta']['drm_hash'])
        savePath = os.path.join(episodeDir, str(imageInfo['id']) + '.jpg')

        if os.path.exists(savePath):
            return

        logger.info('Dwonload image from: {} to : {}'.format(imageInfo['meta']['source_url'], savePath))
        
        imageData = self.session.get(imageInfo['meta']['source_url'], headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)

        key = bytearray(imageKey)
        data = bytearray(imageData.content)

        for i in range(len(data)):
            data[i] ^= key[i % len(key)]

        self.saveImage(savePath, data)

    def download(self, info):
        episodeDir = self.mkEpisodeDir(self.saveDir, 
            info['title'], info['episode'])
        imageData = self.getImageData(info['raw']['episode_id'])
        info['raw']['images'] = imageData
        info['pageSize'] = len(imageData)
        for imageInfo in imageData:
            self.downloadImage(imageInfo, episodeDir)




    def getInfo(self, url):
        if url.find('/contents/') > 0:
            logger.info('Type: Manga')

            episodes = self.getMangaInfo(url)
            episodes['isEpisode'] = False
        else:
            logger.info('Type: Episode')

            episodes = self.getEpisodeInfo(url)
            episodes['isEpisode'] = True
            episodes['episodes'][0]['isCurEpisode'] = True
        return episodes

