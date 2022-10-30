# coding:utf-8

from .manga_crawler import MangaCrawler
from lxml import etree
from PIL import Image
import os
import re

from io import BytesIO as Bytes2Data

import asyncio

import logging

logger = logging.getLogger(__name__)


class MangaPoke(MangaCrawler):
    xpath = {
        'title': '//*[@class="series-header-title"]/text()',
        'series_id': '//*[@class="js-valve"]/@data-giga_series',
        'episode_id': '//*[@class="js-valve"]/@data-giga_episode',
        'episode_new_open': '//*[@id="page-viewer"]/section[3]/div[2]/div[1]/div/ul[1]/li/a',
        'episode_old_open': '//*[@id="page-viewer"]/section[3]/div[2]/div[1]/ul/li/a',
        'episode_more_url': '//*[@id="page-viewer"]/section[3]/div[2]/div/section/button/@data-read-more-endpoint',
        'episode_more_open': '/html/body/ul/li/a',
        'cur_episode': {
            'title': '//*[@class="episode-header-title"]/text()',
            'images': '//*[@class="image-container js-viewer-content"]/p/img/@data-src'
        },
    }

    EPISODES_URL = 'https://pocket.shonenmagazine.com/api/viewer/readable_products'

    def get_info(self, url):
        page = self.web_get(url)
        page.encoding = 'utf-8'
        html = etree.HTML(page.text)

        episode_title = ''.join(html.xpath(self.xpath['cur_episode']['title']))
        episode_id = self.get_episode_id(url)
        series_id = self.get_series_id(url, html)
        return {
            'isEpisode': True,
            'title': ''.join(html.xpath(self.xpath['title'])),
            'seriesId': series_id,
            'episodes': self.get_episodes(url, series_id, cur_episode={
                'title': episode_title,
                'id': episode_id,
                'url': url,
                'seriesId': series_id,
            })
        }

    @staticmethod
    def get_episode_id(url):
        return re.search("\\d*$", url).group(0)

    def get_series_id(self, url, html=None):
        if html is None:
            page = self.web_get(url)
            page.encoding = 'utf-8'
            html = etree.HTML(page.text)
        return ''.join(html.xpath(self.xpath['series_id']))

    def get_episodes(self, url, series_id, cur_episode=None):
        episodes = []
        params = {
            'aggregate_id': series_id,
            'number_since': 250,
            'number_until': -1,
            'read_more_num': 150,
            'type': 'episode',
            'is_guest': 1
        }
        r = self.web_get(self.EPISODES_URL, params=params)
        while True:
            html = r.json()['html']
            next_url = r.json()['nextUrl']
            html = etree.HTML(html)
            free_episodes = html.xpath('//*[@class="test-readable-product-is-free series-episode-list-is-free"]/../..')
            for episode in free_episodes:
                episode_url = ''.join(episode.xpath('@href'))
                title = ''.join(episode.xpath('./div[2]/h4/text()'))
                episode_info = {
                    'episode': title,
                    'pageSize': '',
                    'raw': {
                        'url': episode_url
                    }
                }
                if cur_episode is not None and title == cur_episode['title']:
                    episode_info['isCurEpisode'] = True
                    episode_info['raw']['url'] = url
                episodes.append(episode_info)
            if next_url.find('number_since=1&number_until=-1') < 0:
                r = self.web_get(next_url)
            else:
                break
        return episodes

    def get_episode_images(self, url):
        page = self.web_get(url + '.json')
        page.encoding = 'utf-8'
        data = page.json()
        image_data = data['readableProduct']['pageStructure']['pages']
        return list(filter(lambda image: 'src' in image.keys(), image_data))

    @MangaCrawler.update_pbar
    async def download_image(self, url, save_path):
        if os.path.exists(save_path):
            return
        logger.info('Download image from: {} to: {}'.format(url, save_path))

        r = self.web_get(url)
        logger.debug('Start handle image: {}'.format(save_path))
        self.handle_image(r.content, save_path)

    @staticmethod
    def handle_image(img_data, save_name):
        im = Image.open(Bytes2Data(img_data))
        ims = list()
        w_step = int(im.width / 4)
        h_step = int(im.height / 4)
        start = (0, 0)
        for i in range(0, 4):
            for j in range(0, 4):
                end = (start[0] + w_step, start[1] + h_step)
                ims.append(im.crop(start + end))

                start_y = int(start[1] + h_step)
                if im.height + 10 > start_y > im.height - 10:
                    start = (int(start[0] + w_step), 0)
                else:
                    start = (start[0], start_y)
        start = (0, 0)

        for i in range(0, 4):
            for j in range(0, 4):
                end = (start[0] + w_step, start[1] + h_step)
                im.paste(ims[i * 4 + j], start + end)

                start_x = int(start[0] + w_step)
                if im.width + 10 > start_x > im.width - 10:
                    start = (0, start[1] + h_step)
                else:
                    start = (start_x, start[1])
        im.save(save_name)

    def get_download_episode_data(self, info):
        images = self.get_episode_images(info['raw']['url'])
        info['pageSize'] = len(images)
        info['raw']['images'] = images
        return info

    async def download(self, info):
        episode_dir = self.mk_episode_dir(self.save_dir, info['title'], info['episode'])
        info = self.get_download_episode_data(info)

        # for i in self.tqdm.trange(len(info['raw']['images']), ncols=75, unit='page'):
        with self.tqdm.tqdm(total=len(info['raw']['images']), ncols=75, unit='page') as pbar:
            self.pbar = pbar
            tasks = []
            for i, image in enumerate(info['raw']['images']):
                image = info['raw']['images'][i]
                image_save_path = os.path.join(episode_dir, str(i + 1) + '.jpg')
                task = asyncio.ensure_future(self.download_image(image['src'], image_save_path))
                tasks.append(task)
            await asyncio.gather(*tasks)
            self.pbar = None
