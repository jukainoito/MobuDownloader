# coding:utf-8

from .manga_crawler import MangaCrawler
import re
import os
from lxml import etree
import threadpool
import math
from PIL import Image


from urllib import parse

from io import BytesIO as Bytes2Data



class ComicEarthStat(MangaCrawler):

    episode_info_api_url = 'http://api.comic-earthstar.jp/c.php'
    manga_page_url = 'https://www.comic-earthstar.jp/detail/'
    xpath = {
        'title': '//*[@id="comic_info"]/div[1]/text()',
        'top_episode': '//*[@valign="top"]',
        'episodes': '//*[@id="ep_list"]/ul/li',
        'episode_url': 'a/@href',
        'episode_title': 'h4/text()',

    }

    def __init__(self,  url, save_dir='.', num_workers=8):
        self.save_dir = save_dir
        self.url = url
        self.num_workers = num_workers
        self.task_pool = None

    def get_episode_storage_info(self, episode_url):
        cid = parse.parse_qs(parse.urlparse(episode_url).query)['cid']
        if len(cid) == 0:
            return None
        cid = cid[0]
        info_api_url = self.episode_info_api_url + '?cid='+cid
        r = self.session.get(info_api_url, headers=self.headers)
        episode_info = r.json()

        return episode_info

    def get_episode_info(self, url):
        episode_info = self.get_episode_storage_info(url)
        if episode_info is None:
            return None

        now_episode_title = episode_info['cti']

        manga_url = episode_info['url']
        manga_ident = re.search('data/([^/]*)/', manga_url).group(1)
        manga_url = self.manga_page_url + manga_ident + '/'

        return self.get_manga_info(manga_url, now_episode_title)

    def get_manga_info(self, url, now_episode_title=None):
        r = self.session.get(url, headers=self.headers)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['title']))
        episodes = []

        top_episode = html.xpath(self.xpath['top_episode'])[0]
        top_episode_title = ''.join(top_episode.xpath(self.xpath['episode_title']))
        top_episode_url = ''.join(top_episode.xpath(self.xpath['episode_url']))

        episodes.append({
            "sel": now_episode_title == top_episode_title,
            "episode": top_episode_title,
            "pageSize": "", "status": "", "raw": {
                "url": top_episode_url
            }
        })

        episodes_etree = html.xpath(self.xpath['episodes'])
        for episode in episodes_etree:
            episode_title = ''.join(episode.xpath(self.xpath['episode_title']))
            if len(episode_title) == 0:
                continue
            episode_url = ''.join(episode.xpath(self.xpath['episode_url']))
            sel = False
            if now_episode_title is not None and now_episode_title == episode_title:
                sel = True
            episodes.append({
                "sel": sel, "episode": episode_title,
                "pageSize": "", "status": "", "raw": {
                    "url": episode_url
                }
            })
        return {
            "title": title,
            "episodes": episodes
        }

    def done(self):
        try:
            self.task_pool.poll(True)
        except threadpool.NoResultsPending:
            return True
        return False

    def get_download_episode(self, data):
        down_episodes = []
        for episode in data['episodes']:
            if episode['sel']:
                images_data = self.get_episode_images(episode["raw"]["url"])
                episode['raw']['episode_storage_url'] = images_data['episode_storage_url']
                episode['raw']['images_data'] = images_data['images_data']
                episode['pageSize'] = len(images_data['images_data']['configuration']['contents'])
                down_episodes.append(episode)
        return down_episodes

    def get_episode_images(self, url):
        episode_storage_info = self.get_episode_storage_info(url)
        images_api_url = episode_storage_info['url'] + 'configuration_pack.json'
        r = self.session.get(images_api_url, headers=self.headers)
        image_data = r.json()
        return {
            "episode_storage_url": episode_storage_info['url'],
            "images_data": image_data
        }

    def download_image_data(self, url, save_path, a3f_data):
        r = self.session.get(url)
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

    def gen_a3f(self, width, height, pattern):
        base_width = 64
        base_height = 64
        return self.a3f(width, height, base_width, base_height, pattern)

    def download_image(self, episode_storage_url, episode_dir, image_data):
        save_path = os.path.join(episode_dir, str(image_data['index']) + '.jpg')

        no = image_data['extend']['FileLinkInfo']['PageLinkInfoList'][0]['Page']['No']
        no = str(no)
        image_url = episode_storage_url + image_data['original-file-path'] + '/' + no + '.jpeg'
        page_data = image_data['extend']['FileLinkInfo']['PageLinkInfoList'][0]['Page']
        content_area = page_data['ContentArea']
        width = content_area['Width'] + page_data['DummyWidth']
        height = content_area['Height'] + page_data['DummyHeight']
        pattern = self.gen_pattern(image_data['original-file-path'] + '/' + no)

        a3f_data = self.gen_a3f(width, height, pattern)

        self.download_image_data(image_url, save_path, a3f_data)

    def download(self, data):
        episodes = self.get_download_episode(data)
        self.task_pool = threadpool.ThreadPool(self.num_workers)
        task_args_list = []
        for episode in episodes:
            episode_dir = self.mk_episode_dir(self.save_dir, data['title'], episode['episode'])
            if episode_dir is None:
                continue
            episode['status'] = "开始下载"
            episode_storage_url = episode['raw']['episode_storage_url']
            for image_data in episode['raw']['images_data']['configuration']['contents']:
                extend_data = episode['raw']['images_data'][image_data['original-file-path']]
                image_data['extend'] = extend_data
                task_args = [episode_storage_url, episode_dir, image_data]
                task_args_list.append((task_args, None))

        task_requests = threadpool.makeRequests(self.download_image, task_args_list)

        [self.task_pool.putRequest(req) for req in task_requests]

    def info(self):
        if re.search("//(www.)?comic-earthstar.jp", self.url) is not None:
            return self.get_manga_info(self.url)
        return self.get_episode_info(self.url)

    # From http://viewer.comic-earthstar.jp/js/viewer_1.0.1_2017-01-16.js
    @staticmethod
    def calcPositionWithRest_(a, f, b, e):
        return a * e + (b if a >= f else 0)

    @staticmethod
    def calcXCoordinateXRest_(a, f, b):
        return (a + 61 * b) % f

    @staticmethod
    def calcYCoordinateXRest_(a, f, b, e, d):
        c = (1 == d % 2)
        if c if a < f else not c:
            e = b
            f = 0
        else:
            e = e - b
            f = b
        return (a + 53 * d + 59 * b) % e + f

    @staticmethod
    def calcXCoordinateYRest_(a, f, b, e, d):
        c = (1 == d % 2)
        if c if a < b else not c:
            e = e - f
            b = f
        else:
            e = f
            b = 0
        return (a + 67 * d + f + 71) % e + b

    @staticmethod
    def calcYCoordinateYRest_(a, f, b):
        return (a + 73 * b) % f

    def a3f(self, a, f, b, e, d):
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
                "srcX": k,
                "srcY": m,
                "destX": k,
                "destY": m,
                "width": a,
                "height": f
            })

        if 0 < f:
            for t in range(c):
                p = self.calcXCoordinateXRest_(t, c, d)
                k = self.calcYCoordinateXRest_(p, h, l, g, d)
                p = self.calcPositionWithRest_(p, h, a, b)
                r = k * e
                k = self.calcPositionWithRest_(t, h, a, b)
                m = l * e
                v.append({
                    "srcX": k,
                    "srcY": m,
                    "destX": p,
                    "destY": r,
                    "width": b,
                    "height": f
                })
        if 0 < a:
            for q in range(g):
                k = self.calcYCoordinateYRest_(q, g, d)
                p = self.calcXCoordinateYRest_(k, h, l, c, d)
                p *= b
                r = self.calcPositionWithRest_(k, l, f, e)
                k = h * b
                m = self.calcPositionWithRest_(q, l, f, e)
                v.append({
                    "srcX": k,
                    "srcY": m,
                    "destX": p,
                    "destY": r,
                    "width": a,
                    "height": e
                })

        for t in range(c):
            for q in range(g):
                p = (t + 29 * d + 31 * q) % c
                k = (q + 37 * d + 41 * p) % g
                r = (a if p >= self.calcXCoordinateYRest_(k, h, l, c, d) else 0)
                m = (f if k >= self.calcYCoordinateXRest_(p, h, l, g, d) else 0)
                p = p * b + r
                r = k * e + m
                k = t * b + (a if (t >= h) else 0)
                m = q * e + (f if (q >= l) else 0)
                v.append({
                    "srcX": k,
                    "srcY": m,
                    "destX": p,
                    "destY": r,
                    "width": b,
                    "height": e
                })
        return v
