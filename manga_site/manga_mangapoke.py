# coding:utf-8

from .manga_crawler import MangaCrawler
import requests
from lxml import etree
from PIL import Image
import json
import os
import threadpool
import re


from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


session = requests.Session()
retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

class MangaPoke(MangaCrawler):

    xpaths = {
        'title': '//*[@class="series-header-title"]/text()',
        'episode_new_open': '//*[@id="page-viewer"]/section[3]/div[2]/div[1]/div/ul[1]/li/a',
        'episode_old_open': '//*[@id="page-viewer"]/section[3]/div[2]/div[1]/ul/li/a',
        'episode_more_url': '//*[@id="page-viewer"]/section[3]/div[2]/div/section/button/@data-read-more-endpoint',
        'episode_more_open': '/html/body/ul/li/a',
        'cur_episode': {
            'title': '//*[@class="episode-header-title"]/text()',
            'images': '//*[@class="image-container js-viewer-content"]/p/img/@data-src'
        },
    }

    EPISODES_URL = "https://pocket.shonenmagazine.com/api/viewer/readable_products"

    def __init__(self, url, save_dir='.', num_workers=8):
        self.save_dir = save_dir
        self.url = url
        self.num_workers = num_workers
        self.cur_episode_id = re.search("\\d*$", self.url).group(0)
        self.task_pool = None

    # def get_manga_index(self, url):
    #     page = session.get(url, headers=self.headers)
    #     page.encoding = 'utf-8'
    #
    #     html = etree.HTML(page.text)
    #
    #     title = ''.join(html.xpath(self.xpaths['title']))
    #     episode_new_open = html.xpath(self.xpaths['episode_new_open'])
    #     episode_old_open = html.xpath(self.xpaths['episode_old_open'])
    #     episode_open = episode_new_open + episode_old_open
    #
    #     episode_more_url = ''.join(html.xpath(self.xpaths['episode_more_url']))
    #     if len(episode_more_url) != 0:
    #         r_more = session.get(episode_more_url, headers=self.headers)
    #         more_data = json.loads(r_more.text)
    #         more_html = etree.HTML(more_data['html'])
    #         episode_more_open = more_html.xpath(self.xpaths['episode_more_open'])
    #         episode_open = episode_open + episode_more_open
    #
    #     episodes = list()
    #
    #     for episode in episode_open:
    #         open_status = ''.join(episode.xpath('div[2]/span[2]/@class'))
    #         if 'private' not in open_status:
    #             episodes.append(''.join(episode.xpath('@href')))
    #
    #     cur_episode_title = ''.join(html.xpath(self.xpaths['cur_episode']['title']))
    #     cur_episode_images = html.xpath(self.xpaths['cur_episode']['images'])
    #
    #     return {
    #         'title': title,
    #         'episodes': episodes,
    #         'cur_episode': {
    #             'title': cur_episode_title,
    #             'images': cur_episode_images
    #         }
    #     }

    def get_manga_info(self, url):
        page = session.get(url, headers=self.headers)
        page.encoding = 'utf-8'

        html = etree.HTML(page.text)
        # manga_title = ''.join(html.xpath(self.xpaths['title']))
        # cur_episode_title = ''.join(html.xpath(self.xpaths['cur_episode']['title']))

        return {
            "title": ''.join(html.xpath(self.xpaths['title'])),
            "episodes": self.get_episodes(''.join(html.xpath(self.xpaths['cur_episode']['title'])))
        }

    def get_episodes(self, cur_episode_title):
        episodes = []
        params = {
            "current_readable_product_id": self.cur_episode_id,
            "number_since": 250,
            "number_until": -1,
            "read_more_num": 250,
            "type": "episode"
        }
        r = session.get(self.EPISODES_URL, params=params)
        html = r.json()["html"]
        html = etree.HTML(html)
        free_episodes = html.xpath('//*[@class="test-readable-product-is-free series-episode-list-is-free"]/../..')
        for episode in free_episodes:
            url = ''.join(episode.xpath("@href"))
            title = ''.join(episode.xpath('./div[2]/h4/text()'))
            sel = False
            if title == cur_episode_title:
                sel = True
                url = self.url
            episodes.append({
                "sel": sel,
                "episode": title,
                "pageSize": "",
                "status": "", "raw": {
                    "url": url
                }
            })
        return episodes

    def get_episode_images(self, url):
        page = session.get(url, headers=self.headers)
        page.encoding = 'utf-8'

        html = etree.HTML(page.text)
        # cur_episode_title = ''.join(html.xpath(self.xpaths['cur_episode']['title']))
        cur_episode_images = html.xpath(self.xpaths['cur_episode']['images'])

        # return {
        #     'title': cur_episode_title,
        #     'images': cur_episode_images
        # }
        return cur_episode_images

    def download_image(self, url, save_name):
        r = session.get(url)
        with open(save_name, "wb") as file:
            file.write(r.content)
            self.handle_image(save_name)
        # print(save_name)

    @staticmethod
    def handle_image(save_name):
        im = Image.open(save_name)
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
                images = self.get_episode_images(episode["raw"]["url"])
                episode['pageSize'] = len(images)
                episode['raw']['images'] = images
                down_episodes.append(episode)
        return down_episodes

    def download(self, data):
        episodes = self.get_download_episode(data)
        self.task_pool = threadpool.ThreadPool(self.num_workers)
        task_args_list = []
        for episode in episodes:
            episode_dir = self.mk_episode_dir(self.save_dir, data['title'], episode['episode'])
            if episode_dir is None:
                continue
            episode['status'] = "开始下载"
            for i, image_url in enumerate(episode['raw']['images']):
                image_save_path = os.path.join(episode_dir, str(i + 1) + '.jpg')
                task_args = [image_url, image_save_path]
                task_args_list.append((task_args, None))

        task_requests = threadpool.makeRequests(self.download_image, task_args_list)

        [self.task_pool.putRequest(req) for req in task_requests]

    def info(self):
        return self.get_manga_info(self.url)
