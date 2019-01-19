# coding:utf-8

from .manga_crawler import MangaCrawler
import requests
import re
import os
from lxml import etree
import threadpool

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


session = requests.Session()
retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)


class WebMedu(MangaCrawler):

    domain_url = 'http://www.comic-medu.com'
    xpath = {
        'title': '//*[@property="og:title"]/@content',
        'episodes': '//*[@class="episode"]/li/a',
        'episode_url': '@href',
        'episode_title': 'text()',
        'cur_manga_title': '//*[@name="keywords"]/@content',
        'cur_episode_title': '//*[@property="og:title"]/@content',
        'episode_image_url': '//*[@class="swiper-slide"]/img/@src'
    }

    def __init__(self,  url, save_dir='.', num_workers=8):
        self.save_dir = save_dir
        self.url = url
        self.num_workers = num_workers
        self.task_pool = None

    def get_episode_info(self, url):
        r = session.get(url, headers=self.headers)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['cur_manga_title']))
        title = title.split(',')[0]

        episode_title = ''.join(html.xpath(self.xpath['cur_episode_title']))

        episodes = [{
            "sel": True,
            "episode": episode_title,
            "pageSize": "",
            "status": "",
            "raw": {
                "url": url
            }
        }]
        return {
            "title": title,
            "episodes": episodes
        }

    def get_manga_info(self, url):
        r = session.get(url, headers=self.headers)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['title']))
        episodes = []

        episodes_etree = html.xpath(self.xpath['episodes'])
        for episode in episodes_etree:
            episode_title = ''.join(episode.xpath(self.xpath['episode_title']))
            episode_url = ''.join(episode.xpath(self.xpath['episode_url']))
            episodes.append({
                "sel": False, "episode": episode_title,
                "pageSize": "", "status": "", "raw": {
                    "url": self.domain_url + episode_url
                }
            })
        return {
            "title": title,
            "episodes": episodes
        }

    def get_episode_images(self, url):
        r = session.get(url, headers=self.headers)
        html = etree.HTML(r.text)
        images = (html.xpath(self.xpath['episode_image_url']))
        title = ''.join(html.xpath(self.xpath['cur_episode_title']))

        return title, list(map(lambda img: self.domain_url + img, images))

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
                (title, images) = self.get_episode_images(episode["raw"]["url"])
                episode['pageSize'] = len(images)
                episode['raw']['images'] = images
                episode['episode'] = title
                down_episodes.append(episode)
        return down_episodes

    @staticmethod
    def save_image(save_name, data):
        open(save_name, 'wb').write(data)

    def download_image(self, image_url, save_name):

        image = session.get(image_url, headers=self.headers)
        self.save_image(save_name, image.content)

    def download(self, data):
        episodes = self.get_download_episode(data)

        self.task_pool = threadpool.ThreadPool(self.num_workers)
        task_args_list = []
        for episode in episodes:
            episode_dir = self.mk_episode_dir(self.save_dir, data['title'], episode['episode'])
            episode['status'] = "开始下载"
            if episode_dir is not None:
                for i in range(len(episode['raw']['images'])):
                    image_url = episode['raw']['images'][i]
                    image_save_path = os.path.join(episode_dir, str(i + 1) + '.jpg')
                    task_args = [image_url, image_save_path]
                    task_args_list.append((task_args, None))

        task_requests = threadpool.makeRequests(self.download_image, task_args_list)

        [self.task_pool.putRequest(req) for req in task_requests]

    def info(self):
        if re.search(".*/wk/.*", self.url):
            return self.get_manga_info(self.url)
        return self.get_episode_info(self.url)
