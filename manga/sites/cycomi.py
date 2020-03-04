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

        r = self.webGet(url)
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

        r = self.webGet(url)
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
        r = self.webGet(url)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)
        images = html.xpath(self.xpath['images'])

        return list(filter(lambda img: img.find('http') == 0, images))

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
        episodeDir = self.mkEpisodeDir(self.saveDir, 
            info['title'], info['episode'])
        imageData = self.getEpisodeImages(info['raw']['url'])
        info['raw']['images'] = imageData


        with self.tqdm.tqdm(total=len(imageData), ncols=75, unit='page') as pbar:
            self.pbar = pbar
            tasks = []
        # for i in self.tqdm.trange(len(imageData), ncols=75, unit='page'):
            for i in range(len(imageData)):
                imageUrl = imageData[i]
                imageSavePath = os.path.join(episodeDir, str(i + 1) + '.jpg')
                task = asyncio.ensure_future(self.downloadImage(imageUrl, imageSavePath))
                tasks.append(task)
            await asyncio.gather(*tasks)
            self.pbar = None


    def getInfo(self, url):
        if url.find('title') > 0:
            logger.info('Type: Manga')

            episodes = self.getMangaInfo(url)
            episodes['isEpisode'] = False
        else:
            logger.info('Type: Episode')

            episodes = self.getEpisodeInfo(url)
            episodes['isEpisode'] = True
            episodes['episodes'][0]['isCurEpisode'] = True
        return episodes
