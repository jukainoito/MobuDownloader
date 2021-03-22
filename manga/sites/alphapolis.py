# coding:utf-8

import logging
import os
import re
import asyncio

from lxml import etree

from .manga_crawler import MangaCrawler

logger = logging.getLogger(__name__)


class AlifaPolis(MangaCrawler):
    domainUrl = 'https://www.alphapolis.co.jp'
    xpath = {
        'title': '//*[@class="title"]/h1/text()',
        'episodes': '//*[@class="episode-unit"]',
        'episode_url': '*[@class="abstract"]/object/*[@class="read-episode"]/@href',
        'episode_title': '*[@class="episode"]/div[2]/div[1]/text()',
        'cur_manga_title': '//*[@class="menu official"]/h1/text()',
        'cur_episode_title': '//*[@class="menu official"]/h2/text()',
        'cur_images_data': '/html/body/script[3]/text()'
    }

    def parseImages(self, jsContent):
        target = (jsContent.split('var _pages = [];')[1]).split('var _max_page = _pages.length;')[0]
        regex = re.compile("http[^\"]*")
        return regex.findall(target)

    def getEpisodeInfo(self, url):
        r = self.webGet(url)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['cur_manga_title']))

        episodeTitle = ''.join(html.xpath(self.xpath['cur_episode_title']))
        jsContent = ''.join(html.xpath(self.xpath['cur_images_data']))

        images = self.parseImages(jsContent)

        episodes = [{
            'episode': episodeTitle,
            'pageSize': len(images),
            'raw': {
                'url': url,
                'images': images
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
            if len(episodeUrl) == 0:
                continue
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

    def getEpisodeImages(self, url):
        r = self.webGet(url)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)
        jsContent = ''.join(html.xpath(self.xpath['cur_images_data']))

        images = self.parseImages(jsContent)

        return images

    @staticmethod
    def saveImage(savePath, data):
        open(savePath, 'wb').write(data)

    @MangaCrawler.update_pbar
    async def downloadImage(self, imageUrl, savePath):
        if not os.path.exists(savePath):
            logger.info('Dwonload image from: {} to : {}'.format(imageUrl, savePath))

            image = self.webGet(imageUrl)
            self.saveImage(savePath, image.content)

    async def download(self, info):
        episodeDir = self.mkEpisodeDir(self.saveDir, info['title'], info['episode'])

        if 'images' not in info['raw'].keys():
            images = self.getEpisodeImages(info['raw']['url'])
            info['pageSize'] = len(images)
            info['raw']['images'] = images
        else:
            images = info['raw']['images']

        with self.tqdm.tqdm(total=len(images), ncols=75, unit='page') as pbar:
            self.pbar = pbar
            tasks = []
            # for i in self.tqdm.trange(len(images), ncols=75, unit='page'):
            for i in range(len(images)):
                imageUrl = images[i]
                imageSavePath = os.path.join(episodeDir, str(i + 1) + '.jpg')
                task = asyncio.ensure_future(self.downloadImage(imageUrl, imageSavePath))
                tasks.append(task)
            await asyncio.gather(*tasks)
            self.pbar = None

    def getInfo(self, url):
        episodes = None
        if re.match('^http.*/official/(\\d+)/(\\d+)/?$', url):
            logger.info('Type: Episode')

            episodes = self.getEpisodeInfo(url)
            episodes['isEpisode'] = True
            episodes['episodes'][0]['isCurEpisode'] = True
        elif re.match('^http.*/official/(\\d+)/?$', url):
            logger.info('Type: Manga')

            episodes = self.getMangaInfo(url)
            episodes['isEpisode'] = False
        return episodes
