# coding:utf-8

from .manga_crawler import MangaCrawler
from string import Template
import re
import json
import six
import os
from lxml import etree

import logging
import asyncio

logger = logging.getLogger(__name__)


class MangaWalker(MangaCrawler):
    apiUrlTemp = Template('https://ssl.seiga.nicovideo.jp/api/v1/comicwalker/episodes/${cid}/frames')

    xpath = {
        "title": '//*[@id="detailIndex"]/div/h1/text()',
        "episodes": '//*[@id="reversible"]/li',
        "episode_title": './div/div/span/text()',
        "episode_url": './a/@href'
    }

    def get_episode_info(self, url):
        r = self.web_get(url)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)
        script_str = ''.join(html.xpath('/html/head/script[1]/text()'))
        json_data = script_str[script_str.find('['): script_str.rfind(']') + 1]
        episode_info = json.loads(json_data)
        logging.info(episode_info)
        title = episode_info[0]['content_title']
        episode_info[0]['url'] = url
        episodes = list(map(lambda episode: {'episode': episode['episode_title'],
                                             'pageSize': '', 'raw': episode}, episode_info))
        return {
            'title': title,
            'episodes': episodes,
            'extend': {
                'content_id': episode_info[0]['contentID']
            }
        }

    def get_manga_info(self, url):
        r = self.web_get(url)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['title']))
        episodes = []

        episodes_etree = html.xpath(self.xpath['episodes'])
        for episode in episodes_etree:
            episode_title = ''.join(episode.xpath(self.xpath['episode_title']))
            episode_url = ''.join(episode.xpath(self.xpath['episode_url']))
            episodes.append({
                'episode': episode_title,
                'pageSize': '', 'raw': {
                    'url': episode_url,
                    'episode_id': re.match('.*cid=(\\w*)', episode_url).group(1)
                }
            })
        return {
            'title': title,
            'episodes': episodes,
            'extend': {
                'content_id': re.match('.*/([^/]+)/?$', url).group(1)
            }
        }

    def get_image_data(self, cid):
        api_url = self.apiUrlTemp.substitute(cid=cid)
        r = self.web_get(api_url)
        api_data = json.loads(r.text)
        if api_data['meta']['status'] == 200:
            return api_data['data']['result']
        else:
            raise RuntimeError('接口调用失败')

    @staticmethod
    def generate_key(hash_str):
        m = re.findall(r'[\da-f]{2}', hash_str[0:16])
        key = b''
        for i in m:
            key += six.int2byte(int(i, 16))
        return key

    @staticmethod
    def save_image(save_path, data):
        open(save_path, 'wb').write(data)

    @MangaCrawler.update_pbar
    async def download_image(self, image_info, episode_dir):

        image_key = self.generate_key(image_info['meta']['drm_hash'])
        save_path = os.path.join(episode_dir, str(image_info['id']) + '.jpg')

        if os.path.exists(save_path):
            return

        logger.info('Download image from: {} to : {}'.format(image_info['meta']['source_url'], save_path))

        image_data = self.web_get(image_info['meta']['source_url'])

        key = bytearray(image_key)
        data = bytearray(image_data.content)

        for i in range(len(data)):
            data[i] ^= key[i % len(key)]

        self.save_image(save_path, data)

    async def download(self, info):
        episode_dir = self.mk_episode_dir(self.save_dir, info['title'], info['episode'])
        image_data = self.get_image_data(info['raw']['episode_id'])
        info['raw']['images'] = image_data
        info['pageSize'] = len(image_data)

        # for i in self.tqdm.trange(len(imageData), ncols=75, unit='page'):
        with self.tqdm.tqdm(total=len(image_data), ncols=75, unit='page') as pbar:
            self.pbar = pbar
            tasks = []
            for image_info in image_data:
                task = asyncio.ensure_future(self.download_image(image_info, episode_dir))
                tasks.append(task)
            await asyncio.gather(*tasks)
            self.pbar = None

    def get_info(self, url):
        if url.find('/contents/') > 0:
            logger.info('Type: Manga')

            episodes = self.get_manga_info(url)
            episodes['isEpisode'] = False
        else:
            logger.info('Type: Episode')

            episodes = self.get_episode_info(url)
            episodes['isEpisode'] = True
            episodes['episodes'][0]['isCurEpisode'] = True
        return episodes
