# coding:utf-8

from .manga_crawler import MangaCrawler
import re
import os
from lxml import etree
import asyncio

import logging

logger = logging.getLogger(__name__)


class WebMedu(MangaCrawler):
    domainUrl = 'http://www.comic-medu.com'
    xpath = {
        'title': '//*[@property="og:title"]/@content',
        'episodes': '//*[@class="episode"]/li/a',
        'episode_url': '@href',
        'episode_title': 'text()',
        'cur_manga_title': '//*[@name="keywords"]/@content',
        'cur_episode_title': '//*[@property="og:title"]/@content',
        'episode_image_url': '//*[@class="swiper-slide"]/img/@src'
    }

    def getEpisodeInfo(self, url):

        r = self.webGet(url)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['cur_manga_title']))
        title = title.split(',')[0]

        episodeTitle = ''.join(html.xpath(self.xpath['cur_episode_title']))

        episodes = [{
            'episode': episodeTitle,
            'pageSize': '',
            'raw': {
                'url': url
            }
        }]
        return {
            'title': title,
            'episodes': episodes
        }

    def getMangaInfo(self, url):

        r = self.webGet(url)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['title']))
        episodes = []

        episodesEtree = html.xpath(self.xpath['episodes'])
        for episode in episodesEtree:
            episodeTitle = ''.join(episode.xpath(self.xpath['episode_title']))
            episodeUrl = ''.join(episode.xpath(self.xpath['episode_url']))
            episodes.append({
                'episode': episodeTitle,
                'pageSize': '', 'status': '', 'raw': {
                    'url': self.domainUrl + episodeUrl
                }
            })
        return {
            'title': title,
            'episodes': episodes
        }

    def getEpisodeImages(self, url):
        r = self.webGet(url)
        html = etree.HTML(r.text)
        images = (html.xpath(self.xpath['episode_image_url']))
        title = ''.join(html.xpath(self.xpath['cur_episode_title']))

        return title, list(map(lambda img: self.domainUrl + img, images))

    def get_download_episode(self, data):
        down_episodes = []
        for episode in data['episodes']:
            if episode['sel']:
                (title, images) = self.get_episode_images(episode['raw']['url'])
                episode['pageSize'] = len(images)
                episode['raw']['images'] = images
                episode['episode'] = title
                down_episodes.append(episode)
        return down_episodes

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
        episodeTitle, imageData = self.getEpisodeImages(info['raw']['url'])
        info['raw']['images'] = imageData
        info['raw']['episode'] = episodeTitle

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

    def getInfo(self, url):
        if re.search('.*/wk/.*', url):
            logger.info('Type: Manga')

            episodes = self.getMangaInfo(url)
            episodes['isEpisode'] = False
        else:
            logger.info('Type: Episode')

            episodes = self.getEpisodeInfo(url)
            episodes['isEpisode'] = True
            episodes['episodes'][0]['isCurEpisode'] = True
        return episodes
