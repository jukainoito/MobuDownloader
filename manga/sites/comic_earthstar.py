# coding:utf-8

from .manga_crawler import MangaCrawler
import re
import os
from lxml import etree
import math
from PIL import Image

from urllib import parse 

from io import BytesIO as Bytes2Data

import logging

logger = logging.getLogger(__name__)

class ComicEarthStat(MangaCrawler):

    episodeInfoApiUrl = 'http://api.comic-earthstar.jp/c.php'
    mangaPageUrl = 'https://www.comic-earthstar.jp/detail/'
    xpath = {
        'title': '//*[@id="comic_info"]/div[1]/text()',
        'top_episode': '//*[@valign="top"]',
        'episodes': '//*[@id="ep_list"]/ul/li',
        'episode_url': 'a/@href',
        'episode_title': 'h4/text()',

    }

    def getEpisodeStorageInfo(self, episodeUrl):
        cid = parse.parse_qs(parse.urlparse(episodeUrl).query)['cid']
        if len(cid) == 0:
            return None
        cid = cid[0]
        infoApiUrl = self.episodeInfoApiUrl + '?cid='+cid
        r = self.session.get(infoApiUrl, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)
        episodeInfo = r.json()

        return episodeInfo

    def getEpisodeInfo(self, url):

        episodeInfo = self.getEpisodeStorageInfo(url)
        if episodeInfo is None:
            return None

        nowEpisodeTitle = episodeInfo['cti']

        mangaUrl = episodeInfo['url']
        mangaIdent = re.search('data/([^/]*)/', mangaUrl).group(1)
        mangaUrl = self.mangaPageUrl + mangaIdent + '/'

        episodes = self.getMangaInfo(mangaUrl, nowEpisodeTitle)
        return episodes

    def getMangaInfo(self, url, nowEpisodeTitle=None):

        pattern = re.compile(r'(http[s]?://(www.)comic-earthstar.jp/detail/[^/]*)/?.*')
        findRes = pattern.findall(url)
        if len(findRes) == 0:
            return
        
        jsonUrl = findRes[0][0] + '.json'
        jsonUrl = jsonUrl.replace('detail', 'json/contents/detail')

        r = self.session.get(jsonUrl, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)
        r.encoding = 'utf-8'
        mangaInfo = r.json()
        title = mangaInfo['categorys']['comic_category_title']

        episodes = []
        for episodeRaw in mangaInfo['episodes']:
            temp = {
                "episode": episodeRaw['comic_episode_title'],
                "pageSize": "",
                "raw": episodeRaw
            }
            temp['raw']['url'] = temp['raw']['page_url']
            if nowEpisodeTitle is not None and nowEpisodeTitle == temp['episode']:
                temp['isCurEpisode'] = True
            episodes.append(temp)

        return {
            'title': title,
            'episodes': episodes
        }

    def getEpisodeImages(self, url):
        episodeStorageInfo = self.getEpisodeStorageInfo(url)
        imagesApiUrl = episodeStorageInfo['url'] + 'configuration_pack.json'
        r = self.session.get(imagesApiUrl, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)
        imageData = r.json()
        return {
            "episodeStorageInfoUrl": episodeStorageInfo['url'],
            "data": imageData
        }

    def downloadImageData(self, url, savePath, a3fData):
        r = self.session.get(url, headers=self.headers, cookies=self.cookies, proxies=self.proxies, verify=False)
        self.handleImage(r.content, savePath, a3fData)

    @staticmethod
    def handleImage(imgData, savePath, a3fData):
        im = Image.open(Bytes2Data(imgData))
        newIm = im.copy()
        for data in a3fData:
            imageArea = im.crop((data['destX'], data['destY'],
                                  data['destX'] + data['width'],
                                  data['destY'] + data['height']))
            newIm.paste(imageArea, (data['srcX'], data['srcY']))
        newIm.save(savePath)

    @staticmethod
    def genPattern(name):
        a3h = 4
        chSum = 0
        for ch in name:
            chSum = chSum + ord(ch)
        return chSum % a3h + 1

    def genA3f(self, width, height, pattern):
        baseWidth = 64
        baseHeight = 64
        return self.a3f(width, height, baseWidth, baseHeight, pattern)

    def downloadImage(self, episodeStorageUrl, episodeDir, imageData):
        savePath = os.path.join(episodeDir, str(imageData['index']) + '.jpg')

        if os.path.exists(savePath):
            return

        no = imageData['extend']['FileLinkInfo']['PageLinkInfoList'][0]['Page']['No']
        no = str(no)
        imageUrl = episodeStorageUrl + imageData['original-file-path'] + '/' + no + '.jpeg'
        
        logger.info('Dwonload image from: {} to : {}'.format(imageUrl, savePath))

        pageData = imageData['extend']['FileLinkInfo']['PageLinkInfoList'][0]['Page']
        contentArea = pageData['ContentArea']
        width = contentArea['Width'] + pageData['DummyWidth']
        height = contentArea['Height'] + pageData['DummyHeight']
        pattern = self.genPattern(imageData['original-file-path'] + '/' + no)

        a3fData = self.genA3f(width, height, pattern)

        self.downloadImageData(imageUrl, savePath, a3fData)


    def download(self, info):
        episodeDir = self.mkEpisodeDir(self.saveDir, 
            info['title'], info['episode'])
        imageData = self.getEpisodeImages(info['raw']['url'])
        info['images'] = imageData['data']
        info['pageSize'] = len(imageData['data']['configuration']['contents'])

        episodeStorageUrl = imageData['episodeStorageInfoUrl']
        images = imageData['data']

        for image in images['configuration']['contents']:
                extendData = images[image['original-file-path']]
                image['extend'] = extendData
                self.downloadImage(episodeStorageUrl, episodeDir, image)


    def getInfo(self, url):
        if re.search("//(www.)?comic-earthstar.jp", url) is not None:
            logger.info('Type: Manga')

            episodes = self.getMangaInfo(url)
            episodes['isEpisode'] = False
        else:
            logger.info('Type: Episode')
            
            episodes = self.getEpisodeInfo(url)
            episodes['isEpisode'] = True
        return episodes


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
