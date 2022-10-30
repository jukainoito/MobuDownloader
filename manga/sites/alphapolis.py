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
        'cur_manga_title': '//*[@class="postscript"]/h1/text()',
        'cur_episode_title': '//*[@class="postscript"]/h2/text()',
        'cur_images_data': '/html/body/script[3]/text()'
    }

    @staticmethod
    def parse_images(js_content):
        target = (js_content.split('var _pages = [];')[1]).split('var _max_page = _pages.length;')[0]
        regex = re.compile("http[^\"]*")
        return regex.findall(target)

    def get_episode_info(self, url):
        r = self.web_get(url)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['cur_manga_title']))

        episode_title = ''.join(html.xpath(self.xpath['cur_episode_title']))
        js_content = ''.join(html.xpath(self.xpath['cur_images_data']))

        images = self.parse_images(js_content)

        episodes = [{
            'episode': episode_title,
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

    def get_manga_info(self, url):
        r = self.web_get(url)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['title']))
        episodes = []

        episodes_etree = html.xpath(self.xpath['episodes'])
        for episode in episodes_etree:
            episode_title = ''.join(episode.xpath(self.xpath['episode_title'])).strip()
            episode_url = ''.join(episode.xpath(self.xpath['episode_url'])).strip()
            if len(episode_url) == 0:
                continue
            episodes.append({
                'episode': episode_title,
                'pageSize': '', 'raw': {
                    'url': episode_url if episode_url.startswith('http') else self.domainUrl + episode_url
                }
            })
        return {
            'title': title,
            'episodes': episodes
        }

    def get_episode_images(self, url):
        r = self.web_get(url)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)
        js_content = ''.join(html.xpath(self.xpath['cur_images_data']))

        images = self.parse_images(js_content)

        return images

    @staticmethod
    def save_image(save_path, data):
        open(save_path, 'wb').write(data)

    @MangaCrawler.update_pbar
    async def download_image(self, image_url, save_path):
        if not os.path.exists(save_path):
            logger.info('Download image from: {} to : {}'.format(image_url, save_path))

            image = self.web_get(image_url)
            self.save_image(save_path, image.content)

    async def download(self, info):
        episode_dir = self.mk_episode_dir(self.save_dir, info['title'], info['episode'])

        if 'images' not in info['raw'].keys():
            images = self.get_episode_images(info['raw']['url'])
            info['pageSize'] = len(images)
            info['raw']['images'] = images
        else:
            images = info['raw']['images']

        with self.tqdm.tqdm(total=len(images), ncols=75, unit='page') as pbar:
            self.pbar = pbar
            tasks = []
            # for i in self.tqdm.trange(len(images), ncols=75, unit='page'):
            for i in range(len(images)):
                image_url = images[i]
                image_save_path = os.path.join(episode_dir, str(i + 1) + '.jpg')
                task = asyncio.ensure_future(self.download_image(image_url, image_save_path))
                tasks.append(task)
            await asyncio.gather(*tasks)
            self.pbar = None

    def get_info(self, url):
        episodes = None
        if re.match('^http.*/official/(\\d+)/(\\d+)/?$', url):
            logger.info('Type: Episode')

            episodes = self.get_episode_info(url)
            episodes['isEpisode'] = True
            episodes['episodes'][0]['isCurEpisode'] = True
        elif re.match('^http.*/official/(\\d+)/?$', url):
            logger.info('Type: Manga')

            episodes = self.get_manga_info(url)
            episodes['isEpisode'] = False
        return episodes
