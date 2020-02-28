# coding:utf-8

from .manga_crawler import MangaCrawler
from lxml import etree
from PIL import Image
import os
import threadpool
import re

from io import BytesIO as Bytes2Data


import logging

logger = logging.getLogger(__name__)


class MangaPoke(MangaCrawler):

    xpath = {
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

    def getInfo(self, url):
        page = self.session.get(url, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)
        page.encoding = 'utf-8'
        html = etree.HTML(page.text)

        episode_title = ''.join(html.xpath(self.xpath['cur_episode']['title']))
        episode_id = self.getEpisodeId(url)
        return {
            "isEpisode": True,
            "title": ''.join(html.xpath(self.xpath['title'])),
            "episodes": self.getEpisodes(url, curEpisode={
                'title': episode_title,
                'id': episode_id,
                'url': url
            })
        }

    def getEpisodeId(self, url):
        return re.search("\\d*$", url).group(0)

    def getEpisodes(self, url, curEpisode=None):
        episodes = []
        params = {
            "current_readable_product_id": self.getEpisodeId(url),
            "number_since": 250,
            "number_until": -1,
            "read_more_num": 250,
            "type": "episode"
        }
        r = self.session.get(self.EPISODES_URL, params=params, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)
        html = r.json()["html"]
        html = etree.HTML(html)
        free_episodes = html.xpath('//*[@class="test-readable-product-is-free series-episode-list-is-free"]/../..')
        for episode in free_episodes:
            episoodeUrl = ''.join(episode.xpath("@href"))
            title = ''.join(episode.xpath('./div[2]/h4/text()'))
            episodeInfo = {
                "episode": title,
                "pageSize": "",
                "raw": {
                    "url": episoodeUrl
                }
            }
            if curEpisode is not None and title == curEpisode['title']:
                episodeInfo['isCurEpisode'] = True
                episodeInfo['raw']['url'] = url
            episodes.append(episodeInfo)
        return episodes


    def getEpisodeImages(self, url):
        page = self.session.get(url+'.json', headers=self.headers)
        page.encoding = 'utf-8'
        data = page.json()
        imageData = data['readableProduct']['pageStructure']['pages']
        return list(filter(lambda image: 'src' in image.keys(), imageData))

    def downloadImage(self, url, savePath):
        if os.path.exists(savePath):
            return
        logger.info('Dwonload image from: {} to: {}'.format(url, savePath))

        r = self.session.get(url)
        logger.debug('Start handle image: {}'.format(savePath))
        self.handleImage(r.content, savePath)

    @staticmethod
    def handleImage(img_data, save_name):
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


    def getDownloadEpisodeData(self, info):
        images = self.getEpisodeImages(info["raw"]["url"])
        info['pageSize'] = len(images)
        info['raw']['images'] = images
        return info

    def download(self, info):
        episodeDir = self.mkEpisodeDir(self.saveDir, 
            info['title'], info['episode'])
        info = self.getDownloadEpisodeData(info)
        for i, image in enumerate(info['raw']['images']):
            imageSavePath = os.path.join(episodeDir, str(i + 1) + '.jpg')
            self.downloadImage(image['src'], imageSavePath)

