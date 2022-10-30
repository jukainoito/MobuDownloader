# coding:utf-8

from .manga_crawler import MangaCrawler
import re
import os
from lxml import etree
import asyncio

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
        r = self.webGet(url)
        images = r.json()

        return list(map(lambda img: self.domainUrl + img, images))

    @staticmethod
    def saveImage(savePath, data):
        open(savePath, 'wb').write(data)

    @MangaCrawler.update_pbar
    async def downloadImage(self, imageUrl, savePath):
        if os.path.exists(savePath):
            return

        logger.info('Dwonload image from: {} to : {}'.format(imageUrl, savePath))

        image = self.webGet(imageUrl)
        self.saveImage(savePath, image.content)

    async def download(self, info):
        episodeDir = self.mkEpisodeDir(self.saveDir, info['title'], info['episode'])
        imageData = self.getEpisodeImages(info['raw']['url'])
        info['raw']['images'] = imageData

        # for i in self.tqdm.trange(len(imageData), ncols=75, unit='page'):
        with self.tqdm.tqdm(total=len(imageData), ncols=75, unit='page') as pbar:
            self.pbar = pbar
            tasks = []
            for i in range(len(imageData)):
                imageUrl = imageData[i]
                imageSavePath = os.path.join(episodeDir, str(i + 1) + '.jpg')
                task = asyncio.ensure_future(self.downloadImage(imageUrl, imageSavePath))
                tasks.append(task)
            await asyncio.gather(*tasks)
            self.pbar = None

    def getMangaInfo(self, url):
        if re.search('episode/+$', url) is None:
            url = url + '/episode/'

        r = self.webGet(url)
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
                'episode': episodeTitle,
                'pageSize': '', 'raw': {
                    'url': self.domainUrl + episodeUrl
                }
            })
        return {
            'title': title,
            'episodes': episodes
        }

    def getEpisodeInfo(self, url):

        r = self.webGet(url)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['title']))
        title = re.search('「(.*)」', title).group(1)

        episode_title = ''.join(html.xpath(self.xpath['cur_episode_title']))

        episodes = [{
            'episode': episode_title,
            'pageSize': '',
            'raw': {
                'url': url
            }
        }]
        return {
            'title': title,
            'episodes': episodes
        }

    def getInfo(self, url):
        if re.search('/+episode/+\\d+/*$', url) is None:
            logger.info('Type: Manga')

            episodes = self.getMangaInfo(url)
            episodes['isEpisode'] = False
        else:
            logger.info('Type: Episode')

            episodes = self.getEpisodeInfo(url)
            episodes['isEpisode'] = True
            episodes['episodes'][0]['isCurEpisode'] = True
        return episodes
