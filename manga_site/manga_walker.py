# coding:utf-8

from .manga_crawler import MangaCrawler
# from urllib.parse import urlparse
# from urllib.parse import parse_qs
from string import Template
import re
import json
import six
import os
from lxml import etree
import threadpool


class MangaWalker(MangaCrawler):

    api_url_temp = Template('https://ssl.seiga.nicovideo.jp/api/v1/comicwalker/episodes/${cid}/frames')

    xpath = {
        "title": '//*[@id="detailIndex"]/div/h1/text()',
        "episodes": '//*[@id="reversible"]/li',
        "episode_title": './div/div/span/text()',
        "episode_url": './a/@href'
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
        script_str = ''.join(html.xpath('/html/head/script[1]/text()'))
        json_data = script_str[script_str.find('['): script_str.rfind(']')+1]
        episode_info = json.loads(json_data)
        title = episode_info[0]["content_title"]
        episodes = list(map(lambda episode: {"sel": True, "episode": episode["episode_title"],
                                             "pageSize": "", "status": "", "raw": episode}, episode_info))
        return {
            "title": title,
            "episodes": episodes,
            "extend": {
                "content_id": episode_info[0]["contentID"]
            }
        }

    def get_manga_info(self, url):
        r = self.session.get(url, headers=self.headers)
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
                    "url": episode_url,
                    "episode_id": re.match(".*cid=([A-Za-z0-9_]*)", episode_url).group(1)
                }
            })
        return {
            "title": title,
            "episodes": episodes,
            "extend": {
                "content_id": re.match(".*/([^/]+)/?$", url).group(1)
            }
        }

    def get_image_data(self, cid):
        # query_params = parse_qs(urlparse(url).query)
        # cid = ''.join(query_params['cid'])
        api_url = self.api_url_temp.substitute(cid=cid)
        r = self.session.get(api_url, headers=self.headers)
        api_data = json.loads(r.text)
        if api_data['meta']['status'] == 200:
            return api_data['data']['result']
        else:
            raise RuntimeError('接口调用失败')

    @staticmethod
    def gen_key(hash_str):
        m = re.findall(r'[\da-f]{2}', hash_str[0:16])
        key = b''
        for i in m:
            key += six.int2byte(int(i, 16))
        return key

    @staticmethod
    def save_image(save_name, data):
        open(save_name, 'wb').write(data)

    def download_image(self, image_info, episode_dir):
        image_key = self.gen_key(image_info['meta']['drm_hash'])

        image_data = self.session.get(image_info['meta']['source_url'], headers=self.headers)

        key = bytearray(image_key)
        data = bytearray(image_data.content)

        for i in range(len(data)):
            data[i] ^= key[i % len(key)]

        save_name = os.path.join(episode_dir, str(image_info['id']) + '.jpg')
        self.save_image(save_name, data)

    def get_episode_image(self, episode_id):
        image_array = self.get_image_data(episode_id)

        return image_array

    def get_download_episode(self, data):
        down_episodes = []
        for episode in data['episodes']:
            if episode['sel']:
                images = self.get_episode_image(episode["raw"]["episode_id"])
                episode['pageSize'] = len(images)
                episode['raw']['images'] = images
                down_episodes.append(episode)
        return down_episodes

    def done(self):
        try:
            self.task_pool.poll(True)
        except threadpool.NoResultsPending:
            return True
        return False

    def download(self, data):
        episodes = self.get_download_episode(data)

        self.task_pool = threadpool.ThreadPool(self.num_workers)
        task_args_list = []
        for episode in episodes:
            episode_dir = self.mk_episode_dir(self.save_dir, data['title'], episode['episode'])
            episode['status'] = "开始下载"
            if episode_dir is not None:
                for imageInfo in episode['raw']['images']:
                    task_args = [imageInfo, episode_dir]
                    task_args_list.append((task_args, None))

        task_requests = threadpool.makeRequests(self.download_image, task_args_list)

        [self.task_pool.putRequest(req) for req in task_requests]

        # self.task_pool.wait()
        # self.done = True

    # def download(self, data):
    #     info = self.get_episode_info()
    #     for episodeInfo in info["episodes"]:
    #         episode_dir = os.path.join(self.save_dir, episodeInfo['raw']['content_title'], episodeInfo['raw']['episode_title'])
    #         if os.path.exists(os.path.normpath(episode_dir)):
    #             continue
    #         os.makedirs(os.path.normpath(episode_dir))
    #         image_array = self.get_image_data(episodeInfo['raw']['episode_id'])
    #
    #         task_pool = threadpool.ThreadPool(self.num_workers)
    #         task_args_list = []
    #         for imageInfo in image_array:
    #             task_args = [imageInfo, episode_dir]
    #             task_args_list.append((task_args, None))
    #
    #         task_requests = threadpool.makeRequests(self.download_image, task_args_list)
    #
    #         [task_pool.putRequest(req) for req in task_requests]
    #
    #         task_pool.wait()

    def info(self):
        if self.url.find('/contents/') > 0:
            return self.get_manga_info(self.url)
        else:
            return self.get_episode_info(self.url)

