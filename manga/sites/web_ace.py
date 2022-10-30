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

    def get_episode_images(self, url):
        url = url + '/json/'
        r = self.web_get(url)
        images = r.json()

        return list(map(lambda img: self.domainUrl + img, images))

    @staticmethod
    def save_image(save_path, data):
        open(save_path, 'wb').write(data)

    @MangaCrawler.update_pbar
    async def download_image(self, image_url, save_path):
        if os.path.exists(save_path):
            return

        logger.info('Download image from: {} to : {}'.format(image_url, save_path))

        image = self.web_get(image_url)
        self.save_image(save_path, image.content)

    async def download(self, info):
        episode_dir = self.mk_episode_dir(self.save_dir, info['title'], info['episode'])
        image_data = self.get_episode_images(info['raw']['url'])
        info['raw']['images'] = image_data

        # for i in self.tqdm.trange(len(imageData), ncols=75, unit='page'):
        with self.tqdm.tqdm(total=len(image_data), ncols=75, unit='page') as pbar:
            self.pbar = pbar
            tasks = []
            for i in range(len(image_data)):
                image_url = image_data[i]
                image_save_path = os.path.join(episode_dir, str(i + 1) + '.jpg')
                task = asyncio.ensure_future(self.download_image(image_url, image_save_path))
                tasks.append(task)
            await asyncio.gather(*tasks)
            self.pbar = None

    def get_manga_info(self, url):
        if re.search('episode/+$', url) is None:
            url = url + '/episode/'

        r = self.web_get(url)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['title']))
        title = re.search('「(.*)」', title).group(1)
        episodes = []

        episodes_etree = html.xpath(self.xpath['episodes'])
        for episode in episodes_etree:
            episode_title = ''.join(episode.xpath(self.xpath['episode_title']))
            if len(episode_title) == 0:
                continue
            episode_url = ''.join(episode.xpath(self.xpath['episode_url']))
            episodes.append({
                'episode': episode_title,
                'pageSize': '', 'raw': {
                    'url': self.domainUrl + episode_url
                }
            })
        return {
            'title': title,
            'episodes': episodes
        }

    def get_episode_info(self, url):

        r = self.web_get(url)
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

    def get_info(self, url):
        if re.search('/+episode/+\\d+/*$', url) is None:
            logger.info('Type: Manga')

            episodes = self.get_manga_info(url)
            episodes['isEpisode'] = False
        else:
            logger.info('Type: Episode')

            episodes = self.get_episode_info(url)
            episodes['isEpisode'] = True
            episodes['episodes'][0]['isCurEpisode'] = True
        return episodes
