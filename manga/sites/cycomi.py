# coding:utf-8

from .manga_crawler import MangaCrawler
import os
from lxml import etree

import logging

logger = logging.getLogger(__name__)


class Cycomi(MangaCrawler):

    domainUrl = 'https://cycomi.com'
    xpath = {
        'title': '//*[@class="title-texts"]/h3/text()',
        'episodes': '//*[@class="title-chapters"]/a',
        'episode_url': '@href',
        'episode_title': 'div/p[1]/text()',
        'cur_episode_manga_title': '/html/body/header/p/a/text()',
        'cur_episode_title': '/html/body/header/p/text()',
        'images': '//*[@class="swiper-wrapper"]/div/img/@src'
    }


    def getEpisodeInfo(self, url):
        logger.info('Start get episode info from: {}'.format(url))

        r = self.session.get(url, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['cur_episode_manga_title']))

        episodeTitle = ''.join(html.xpath(self.xpath['cur_episode_title']))
        episodeTitle = episodeTitle.replace(' - ', '')
        episodes = [{
            "episode": episodeTitle,
            "pageSize": "",
            "raw": {
                "url": url
            }
        }]
        return {
            "title": title,
            "episodes": episodes
        }

    def getMangaInfo(self, url):
        logger.info('Start get manga info from: {}'.format(url))

        r = self.session.get(url, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['title']))
        episodes = []

        episodesEtree = html.xpath(self.xpath['episodes'])
        for episode in episodesEtree:
            episodeTitle = ''.join(episode.xpath(self.xpath['episode_title']))
            if len(episodeTitle) == 0:
                continue
            episodeUrl = ''.join(episode.xpath(self.xpath['episode_url']))
            episodes.append({"episode": episodeTitle,
                "pageSize": "", "raw": {
                    "url": self.domainUrl + episodeUrl
                }
            })
        return {
            "title": title,
            "episodes": episodes
        }

    def getEpisodeImages(self, url):
        r = self.session.get(url, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)
        images = html.xpath(self.xpath['images'])

        return list(filter(lambda img: img.find('http') == 0, images))

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


    def getInfo(self, url):
        if url.find('title') > 0:
            episodes = self.getMangaInfo(url)
            episodes['isEpisode'] = False
        else:
            episodes = self.getEpisodeInfo(url)
            episodes['isEpisode'] = True
            episodes['episodes'][0]['isCurEpisode'] = True
        return episodes
