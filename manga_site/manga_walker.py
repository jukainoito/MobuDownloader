from .manga_crawler import MangaCrawler
# from urllib.parse import urlparse
# from urllib.parse import parse_qs
from string import Template
import requests
import re
import json
import six
import os
from lxml import etree
import threadpool

class MangaWalker(MangaCrawler):

    api_url_temp = Template('https://ssl.seiga.nicovideo.jp/api/v1/comicwalker/episodes/${cid}/frames')

    def __init__(self,  url, save_dir='.', num_workers=8):
        self.save_dir = save_dir
        self.url = url
        self.num_workers = num_workers


    def getImageData(self, cid):
        # query_params = parse_qs(urlparse(url).query)
        # cid = ''.join(query_params['cid'])
        api_url = self.api_url_temp.substitute(cid=cid)
        r = requests.get(api_url, headers=self.headers)
        api_data = json.loads(r.text)
        if api_data['meta']['status'] == 200:
            return api_data['data']['result']
        else:
            raise RuntimeError('接口调用失败')

    def generateKey(self, hash):
        m = re.findall(r'[\da-f]{2}', hash[0:16])
        key = b''
        for i in m:
            key += six.int2byte(int(i, 16))
        return key

    def downloadImage(self, imageInfo, episode_dir):
        imageKey = self.generateKey(imageInfo['meta']['drm_hash'])

        imageData = requests.get(imageInfo['meta']['source_url'], headers=self.headers)

        key = bytearray(imageKey)
        data = bytearray(imageData.content)

        for i in range(len(data)):
            data[i] ^= key[i % len(key)]

        save_name = os.path.join(episode_dir, str(imageInfo['id']) + '.jpg')
        self.saveImage(save_name, data)

    def saveImage(self, save_name, data):
        open(save_name, 'wb').write(data)

    def getEpisodeInfo(self):
        r = requests.get(self.url, headers=self.headers)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)
        script_str = ''.join(html.xpath('/html/head/script[1]/text()'))
        json_data = script_str[script_str.find('['): script_str.rfind(']')+1]
        episodeInfo = json.loads(json_data)
        return episodeInfo;

    def download(self):
        info = self.getEpisodeInfo()
        for episodeInfo in info:
            episode_dir = os.path.join(self.save_dir, episodeInfo['content_title'], episodeInfo['episode_title'])
            if os.path.exists(os.path.normpath(episode_dir)):
                continue
            os.makedirs(os.path.normpath(episode_dir))
            imageArray = self.getImageData(episodeInfo['episode_id'])



            task_pool = threadpool.ThreadPool(self.num_workers)
            task_args_list = []
            for imageInfo in imageArray:
                task_args = [imageInfo, episode_dir]
                task_args_list.append((task_args, None))

            task_requests = threadpool.makeRequests(self.downloadImage, task_args_list)

            [task_pool.putRequest(req) for req in task_requests]

            task_pool.wait()


            # for imageInfo in imageArray:
            #     self.downloadImage(imageInfo, episode_dir)

