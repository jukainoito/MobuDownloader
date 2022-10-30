# coding:utf-8

from .manga_crawler import MangaCrawler
import re
import os
import math
from PIL import Image

from urllib import parse

from io import BytesIO as Bytes2Data
import asyncio

import logging

logger = logging.getLogger(__name__)


class ComicEarthStat(MangaCrawler):
    episodeInfoApiUrl = 'http://api.comic-earthstar.jp/c.php'
    mangaPageUrl = 'https://www.info_api_url.jp/detail/'
    xpath = {
        'title': '//*[@id="comic_info"]/div[1]/text()',
        'top_episode': '//*[@valign="top"]',
        'episodes': '//*[@id="ep_list"]/ul/li',
        'episode_url': 'a/@href',
        'episode_title': 'h4/text()',

    }

    def get_episode_storage_info(self, episode_url):
        cid = parse.parse_qs(parse.urlparse(episode_url).query)['cid']
        if len(cid) == 0:
            return None
        cid = cid[0]
        info_api_url = self.episodeInfoApiUrl + '?cid=' + cid
        r = self.web_get(info_api_url, scheme='https')
        episode_info = r.json()

        return episode_info

    def get_episode_info(self, url):

        episode_info = self.get_episode_storage_info(url)
        if episode_info is None:
            return None

        now_episode_title = episode_info['cti']

        manga_url = episode_info['url']
        manga_ident = re.search('data/([^/]*)/', manga_url).group(1)
        manga_url = self.mangaPageUrl + manga_ident + '/'

        episodes = self.get_manga_info(manga_url, now_episode_title)
        return episodes

    def get_manga_info(self, url, now_episode_title=None):

        pattern = re.compile(r'(http(s)?://(www.)comic-earthstar.jp/detail/[^/]*)/?.*')
        find_res = pattern.findall(url)
        if len(find_res) == 0:
            return

        json_url = find_res[0][0] + '.json'
        json_url = json_url.replace('detail', 'json/contents/detail')

        r = self.web_get(json_url, scheme='https')
        r.encoding = 'utf-8'
        manga_info = r.json()
        title = manga_info['categorys']['comic_category_title']

        episodes = []
        for episode_raw in manga_info['episodes']:
            temp = {
                'episode': episode_raw['comic_episode_title'],
                'pageSize': '',
                'raw': episode_raw
            }
            temp['raw']['url'] = temp['raw']['page_url']
            if now_episode_title is not None and now_episode_title == temp['episode']:
                temp['isCurEpisode'] = True
            episodes.append(temp)

        return {
            'title': title,
            'episodes': episodes
        }

    def get_episode_images(self, url):
        episode_storage_info = self.get_episode_storage_info(url)
        images_api_url = episode_storage_info['url'] + 'configuration_pack.json'

        r = self.web_get(images_api_url, scheme='https')
        image_data = r.json()
        return {
            'episodeStorageInfoUrl': episode_storage_info['url'],
            'data': image_data
        }

    def download_image_data(self, url, save_path, a3f_data):
        r = self.web_get(url, scheme='https')
        self.handle_image(r.content, save_path, a3f_data)

    @staticmethod
    def handle_image(img_data, save_path, a3f_data):
        im = Image.open(Bytes2Data(img_data))
        new_im = im.copy()
        for data in a3f_data:
            image_area = im.crop((data['destX'], data['destY'],
                                  data['destX'] + data['width'],
                                  data['destY'] + data['height']))
            new_im.paste(image_area, (data['srcX'], data['srcY']))
        new_im.save(save_path)

    @staticmethod
    def gen_pattern(name):
        a3h = 4
        ch_sum = 0
        for ch in name:
            ch_sum = ch_sum + ord(ch)
        return ch_sum % a3h + 1

    def generate_a3f(self, width, height, pattern):
        base_width = 64
        base_height = 64
        return self.a3f(width, height, base_width, base_height, pattern)

    @MangaCrawler.update_pbar
    async def download_image(self, episode_storage_url, episode_dir, image_data):
        save_path = os.path.join(episode_dir, str(image_data['index']) + '.jpg')

        if os.path.exists(save_path):
            return

        no = image_data['extend']['FileLinkInfo']['PageLinkInfoList'][0]['Page']['No']
        no = str(no)
        image_url = episode_storage_url + image_data['original-file-path'] + '/' + no + '.jpeg'

        logger.info('Download image from: {} to : {}'.format(image_url, save_path))

        page_data = image_data['extend']['FileLinkInfo']['PageLinkInfoList'][0]['Page']
        content_area = page_data['ContentArea']
        width = content_area['Width'] + page_data['DummyWidth']
        height = content_area['Height'] + page_data['DummyHeight']
        pattern = self.gen_pattern(image_data['original-file-path'] + '/' + no)

        a3f_data = self.generate_a3f(width, height, pattern)

        self.download_image_data(image_url, save_path, a3f_data)

    async def download(self, info):
        episode_dir = self.mk_episode_dir(self.save_dir, info['title'], info['episode'])
        image_data = self.get_episode_images(info['raw']['url'])
        info['images'] = image_data['data']
        info['pageSize'] = len(image_data['data']['configuration']['contents'])

        episode_storage_url = image_data['episodeStorageInfoUrl']
        images = image_data['data']

        with self.tqdm.tqdm(total=len(images['configuration']['contents']), ncols=75, unit='page') as pbar:
            self.pbar = pbar
            tasks = []
            # for i in range(len(images['configuration']['contents'])):
            # image = images['configuration']['contents'][i]
            for image in images['configuration']['contents']:
                extend_data = images[image['original-file-path']]
                image['extend'] = extend_data
                task = asyncio.ensure_future(self.download_image(episode_storage_url, episode_dir, image))
                tasks.append(task)
            await asyncio.gather(*tasks)
            self.pbar = None

    def get_info(self, url):
        if re.search('//(www.)?comic-earthstar.jp', url) is not None:
            logger.info('Type: Manga')

            episodes = self.get_manga_info(url)
            episodes['isEpisode'] = False
        else:
            logger.info('Type: Episode')

            episodes = self.get_episode_info(url)
            episodes['isEpisode'] = True
        return episodes

    # From http://viewer.comic-earthstar.jp/js/viewer_1.0.1_2017-01-16.js
    @staticmethod
    def calc_position_with_rest_(a, f, b, e):
        return a * e + (b if a >= f else 0)

    @staticmethod
    def calc_x_coordinate_x_rest_(a, f, b):
        return (a + 61 * b) % f

    @staticmethod
    def calc_y_coordinate_x_rest_(a, f, b, e, d):
        c = (1 == d % 2)
        if c if a < f else not c:
            e = b
            f = 0
        else:
            e = e - b
            f = b
        return (a + 53 * d + 59 * b) % e + f

    @staticmethod
    def calc_x_coordinate_y_rest_(a, f, b, e, d):
        c = (1 == d % 2)
        if c if a < b else not c:
            e = e - f
            b = f
        else:
            e = f
            b = 0
        return (a + 67 * d + f + 71) % e + b

    @staticmethod
    def calc_y_coordinate_y_rest_(a, f, b):
        return (a + 73 * b) % f

    @staticmethod
    def a3f(a, f, b, e, d):
        c = math.floor(a / b)
        g = math.floor(f / e)
        a %= b
        f %= e
        v = []
        h = c - 43 * d % c
        h = ((c - 4) % c) if (0 == h % c) else h
        h = (c - 1) if (0 == h) else h
        l = g - 47 * d % g
        l = ((g - 4) % g) if (0 == l % g) else l
        l = (g - 1) if (0 == l) else l
        if a > 0 and f > 0:
            k = h * b
            m = l * e
            v.append({
                'srcX': k,
                'srcY': m,
                'destX': k,
                'destY': m,
                'width': a,
                'height': f
            })

        if 0 < f:
            for t in range(c):

                p = ComicEarthStat.calc_x_coordinate_x_rest_(t, c, d)
                k = ComicEarthStat.calc_y_coordinate_x_rest_(p, h, l, g, d)
                p = ComicEarthStat.calc_position_with_rest_(p, h, a, b)
                r = k * e
                k = ComicEarthStat.calc_position_with_rest_(t, h, a, b)
                m = l * e
                v.append({
                    'srcX': k,
                    'srcY': m,
                    'destX': p,
                    'destY': r,
                    'width': b,
                    'height': f
                })
        if 0 < a:
            for q in range(g):
                k = ComicEarthStat.calc_y_coordinate_y_rest_(q, g, d)
                p = ComicEarthStat.calc_x_coordinate_y_rest_(k, h, l, c, d)
                p *= b
                r = ComicEarthStat.calc_position_with_rest_(k, l, f, e)
                k = h * b
                m = ComicEarthStat.calc_position_with_rest_(q, l, f, e)
                v.append({
                    'srcX': k,
                    'srcY': m,
                    'destX': p,
                    'destY': r,
                    'width': a,
                    'height': e
                })

        for t in range(c):
            for q in range(g):
                p = (t + 29 * d + 31 * q) % c
                k = (q + 37 * d + 41 * p) % g
                r = (a if p >= ComicEarthStat.calc_x_coordinate_y_rest_(k, h, l, c, d) else 0)
                m = (f if k >= ComicEarthStat.calc_y_coordinate_x_rest_(p, h, l, g, d) else 0)
                p = p * b + r
                r = k * e + m
                k = t * b + (a if (t >= h) else 0)
                m = q * e + (f if (q >= l) else 0)
                v.append({
                    'srcX': k,
                    'srcY': m,
                    'destX': p,
                    'destY': r,
                    'width': b,
                    'height': e
                })
        return v
