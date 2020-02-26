# coding:utf-8

from .manga_crawler import MangaCrawler
import re
import os
from lxml import etree

import logging

logger = logging.getLogger(__name__)



class WebAce(MangaCrawler):

    domainUrl = 'https://web-ace.jp'
    xpath = {
        'title': '/html/head/title/text()',
        'episodes': '//*[@id="read"]//ul/li/a',
        'episode_url': '@href',
        'episode_title': 'div/div/p/text()',
        'cur_episode_title': '//*[@class="container-headerArea"]/span/text()'
    }


    def getEpisodeImages(self, url):
        url = url + '/json/'
        r = self.session.get(url, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)
        images = r.json()

        return list(map(lambda img: self.domainUrl + img, images))

    @staticmethod
    def saveImage(savePath, data):
        open(savePath, 'wb').write(data)

    @staticmethod
    def saveImage(savePath, data):
        open(savePath, 'wb').write(data)

    def downloadImage(self, imageUrl, savePath):
        if os.path.exists(savePath):
            return

        logger.info('Dwonload image from: {} to : {}'.format(imageUrl, savePath))

        image = self.session.get(imageUrl, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)
        self.saveImage(savePath, image.content)

    def download(self, info):
        episodeDir = self.mkEpisodeDir(self.saveDir, 
            info['title'], info['episode'])
        imageData = self.getEpisodeImages(info['raw']['url'])
        info['raw']['images'] = imageData
        for i in range(len(imageData)):
            imageUrl = imageData[i]
            imageSavePath = os.path.join(episodeDir, str(i + 1) + '.jpg')
            self.downloadImage(imageUrl, imageSavePath)


    def getMangaInfo(self, url):
        if re.search("episode/+$", url) is None:
            url = url + '/episode/'

        logger.info('Start get manga info from: {}'.format(url))
        r = self.session.get(url, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['title']))
        title = re.search('「(.*)」', title).group(1)
        episodes = []

        episodesEtree = html.xpath(self.xpath['episodes'])
        for episode in episodesEtree:
            episodeTitle = ''.join(episode.xpath(self.xpath['episode_title']))
            if len(episodeTitle) == 0:
                continue
            episodeUrl = ''.join(episode.xpath(self.xpath['episode_url']))
            episodes.append({
                "episode": episodeTitle,
                "pageSize": "", "raw": {
                    "url": self.domainUrl + episodeUrl
                }
            })
        return {
            "title": title,
            "episodes": episodes
        }


    def getEpisodeInfo(self, url):
        logger.info('Start get episode info from: {}'.format(url))
        r = self.session.get(url, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['title']))
        title = re.search('「(.*)」', title).group(1)

        episode_title = ''.join(html.xpath(self.xpath['cur_episode_title']))

        episodes = [{
            "episode": episode_title,
            "pageSize": "",
            "raw": {
                "url": url
            }
        }]
        return {
            "title": title,
            "episodes": episodes
        }

    def getInfo(self, url):
        if re.search("/+episode/+\\d+/*$", url) is None:
            episodes = self.getMangaInfo(url)
            episodes['isEpisode'] = False
        else:
            episodes = self.getEpisodeInfo(url)
            episodes['isEpisode'] = True
            episodes['episodes'][0]['isCurEpisode'] = True
        return episodes