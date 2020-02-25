# coding:utf-8

from .manga_crawler import MangaCrawler
import re
import os
from lxml import etree
import threadpool


class WebAce(MangaCrawler):

    domain_url = 'https://web-ace.jp'
    xpath = {
        'title': '/html/head/title/text()',
        'episodes': '//*[@id="read"]//ul/li/a',
        'episode_url': '@href',
        'episode_title': 'div/div/p/text()',
        'cur_episode_title': '//*[@class="container-headerArea"]/span/text()'
    }

    def __init__(self,  url, save_dir='.', num_workers=8):
        self.save_dir = save_dir
        self.url = url
        self.num_workers = num_workers
        self.task_pool = None

    def get_episode_info(self, url):
        r = self.session.get(url, headers=self.headers)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)

        title = ''.join(html.xpath(self.xpath['title']))
        title = re.search('「(.*)」', title).group(1)

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
        if re.search("episode/+$", url) is None:
            url = url + '/episode/'
        r = self.session.get(url, headers=self.headers)
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
        url = url + '/json/'
        r = self.session.get(url, headers=self.headers)
        images = r.json()

        return list(map(lambda img: self.domain_url + img, images))

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

    @staticmethod
    def save_image(save_name, data):
        open(save_name, 'wb').write(data)

    def download_image(self, image_url, save_name):

        image = self.session.get(image_url, headers=self.headers)
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
        if re.search("/+episode/+\\d+/*$", self.url) is None:
            return self.get_manga_info(self.url)
        return self.get_episode_info(self.url)
