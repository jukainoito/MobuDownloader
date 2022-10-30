# coding:utf-8

from .manga_crawler import MangaCrawler
import re, os
from lxml import etree
from urllib.parse import urljoin
from PIL import Image

from io import BytesIO as Bytes2Data

import asyncio

import logging

logger = logging.getLogger(__name__)


class HutabashaWeblish(MangaCrawler):
    domainUrl = 'http://futabasha.pluginfree.com'
    imageBaseUrl = 'http://futabasha.pluginfree.com/cgi-bin/widget.cgi'
    xpath = {
        'manga_info_title': '//*[@id="webcomic_center"]/hgroup/h1/text()',
        'manga_info_episodes': '//*[@id="backno"]/li/a',
        'manga_info_episode_title': 'text()',
        'manga_info_episode_link': '@href',

        'decode_key': '//*[@id="cKV"]/@title',
        'web_key': '//*[@id="hCN"]/@title',
        'init_data': '//*[@id="DATA"]/text()',
        'uid': '//*[@id="UID"]/@title',

        'page_num': '//*[@id="tPN"]/@title',
        'manga_key': '//*[@id="sHN"]/@title',
        'image_key': '//*[@id="sIS"]/@title',
        'episode_title': '//*[@id="sKey2"]/@title',

    }

    @staticmethod
    def expand(_src, _key):
        bbc = [0, 1, 3, 7, 15, 31, 63, 127, 255, 511, 1023, 2047, 4095]
        k_base = "zBCfA!c#e@-UHTOtLEaDPVbXYjgNrRQlyFWpZ$+no*qIhKSvuxGk~siwm%:dJ/M?"
        _tbl = [0] * 10240
        _byt = [0] * 4
        _ky = []
        _ret = [''] * 10240
        _pst = ''
        j = _cs = _bis = _cd = _bit = _ss = _rn = 0
        i = 0
        while i < 4:
            _ky.append(_key & 255)
            _key >>= 8
            i += 1
        _pn = 130
        _cbt = 8
        i = 0
        while i < len(_src):
            _cs *= 64
            _cs += k_base.index(_src[i])
            _bis += 6
            if _bis >= 8:
                _byt[j] = (_cs >> (_bis - 8)) & 255
                j += 1
                _bis -= 8
                _cs = _cs & bbc[_bis]
                if j == 4:
                    j = 0
                    while j < 4:
                        _bit += 8
                        _cd <<= 8
                        _cd += _byt[j] ^ _ky[j]
                        if _bit >= _cbt:
                            _ss = (_cd >> (_bit - _cbt)) & bbc[_cbt]
                            _bit -= _cbt
                            _cd = _cd & bbc[_bit]
                            if _ss != 128 and _ss != 129 and _ss <= _pn:
                                if _ss < 128:
                                    _ks = chr(_ss)
                                elif _ss == _pn:
                                    _ks = _pst + _pst[0]
                                else:
                                    _ks = _tbl[_ss]
                                _ret[_rn] = _ks
                                _rn += 1
                                if _pst and _ks:
                                    _tbl[_pn] = _pst + _ks[0]
                                    _pn += 1
                                _pst = _ks
                            if _ss == 129 or _ss > _pn:
                                break
                            elif _ss == 128 or _pn >= 4096:
                                _pst = ''
                                _pn = 130
                                _cbt = 8
                            elif _pn == 255 or _pn == 511 or _pn == 1023 or _pn == 2047:
                                _cbt += 1
                        j += 1
                    if j < 4:
                        break
                    j = 0
            i += 1
        _rt = ''.join(_ret)
        return _rt

    @staticmethod
    def convert_manga_url(url):
        if url.find('index.shtml') == -1:
            return re.sub('/([^/]*)$', '/index.shtml', url)

        return url

    def get_episode_info(self, url):

        r = self.web_get(url)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)
        decode_key = ''.join(html.xpath(self.xpath['decode_key']))
        uid = ''.join(html.xpath(self.xpath['uid']))
        web_key = ''.join(html.xpath(self.xpath['web_key']))

        init_url = urljoin(url, 'InitVal.html')
        ir = self.web_get(init_url)
        ir.encoding = 'utf-8'
        init_html = etree.HTML(ir.text)
        init_data = ''.join(init_html.xpath(self.xpath['init_data']))
        init_data = self.expand(init_data, int(decode_key))
        init_html = etree.HTML(init_data)

        episode_title = ''.join(init_html.xpath(self.xpath['episode_title']))
        s = re.sub(r'%u([a-fA-F0-9]{4}|[a-fA-F0-9]{2})', lambda m: chr(int(m.group(1), 16)), episode_title)
        search = re.search('\\$\\$\\{(.*)\u3000(.*)/.*', s)
        title = search.group(1)
        episode_title = search.group(2)

        page_size = ''.join(init_html.xpath(self.xpath['page_num']))
        manga_key = ''.join(init_html.xpath(self.xpath['manga_key']))
        image_key = ''.join(init_html.xpath(self.xpath['image_key']))
        base_a = web_key + manga_key + '/' + manga_key + '_'

        episodes = [{
            'episode': episode_title,
            'page_size': int(page_size),
            'raw': {
                'url': url,
                'size': int(page_size),
                'uid': uid,
                'base_a': base_a,
                'image_key': image_key
            }
        }]
        return {
            'title': title,
            'episodes': episodes
        }

    @staticmethod
    # page start 1  mag=6,9,12,15 x y
    # sm = image_key
    def get_ipnt_str(_npn, _nsn, sm, _x, _y):
        r_tbl = [495, 510, 411, 433, 6, 425, 82, 889, 71, 422, 57, 445, 830, 260, 21, 649, 324, 249, 239,
                 632, 894, 691, 345, 363, 521, 465, 725, 122, 542, 519, 154, 219, 626, 567, 841, 481, 423,
                 757, 539, 553, 797, 606, 873, 532, 40, 974, 545, 973, 990, 353, 580, 796, 429, 272, 247,
                 117, 706, 77, 842, 557, 957, 880, 959, 28, 850, 380, 568, 161, 717, 131, 897, 309, 240, 551,
                 989, 9, 111, 326, 602, 38, 348, 844, 747, 360, 579, 175, 852, 251, 777, 480, 684, 174, 775,
                 106, 171, 926, 942, 170, 793, 89, 950, 890, 695, 328, 20, 468, 173, 546, 564, 791, 694, 451,
                 625, 735, 110, 23, 357, 213, 85, 610, 289, 27, 832, 507, 992, 909, 119, 872, 146, 185, 615,
                 798, 2, 108, 197, 756, 773, 22, 782, 264, 181, 884, 285, 454, 629, 596, 92, 19, 15, 367, 1,
                 877, 918, 734, 199, 486, 723, 783, 585, 840, 760, 443, 72, 708, 534, 437, 303, 322, 818, 399,
                 715, 977, 895, 538, 385, 109, 349, 987, 269, 273, 104, 915, 681, 617, 211, 620, 576, 645, 435,
                 961, 476, 808, 205, 656, 593, 675, 79, 716, 453, 204, 859, 306, 820, 920, 572, 641, 227, 980,
                 24, 976, 388, 287, 854, 8, 812, 200, 813, 616, 784, 340, 292, 788, 623, 408, 290, 555, 355, 496,
                 231, 701, 330, 635, 700, 392, 683, 144, 962, 347, 494, 279, 393, 662, 657, 382, 230, 646, 838,
                 491, 943, 903, 921, 126, 378, 595, 806, 748, 208, 436, 14, 746, 902, 624, 651, 207, 492, 670,
                 856, 182, 916, 999, 139, 256, 863, 742, 270, 373, 130, 899, 713, 52, 774, 604, 772, 698, 323,
                 676, 216, 351, 68, 857, 252, 537, 504, 931, 73, 640, 192, 944, 821, 952, 540, 924, 660, 305,
                 878, 609, 48, 685, 994, 366, 892, 607, 851, 642, 118, 379, 428, 36, 497, 177, 543, 673, 826,
                 839, 159, 427, 471, 690, 794, 265, 814, 463, 769, 482, 133, 666, 867, 368, 917, 120, 554, 209,
                 105, 226, 763, 978, 771, 834, 583, 705, 789, 244, 720, 295, 712, 96, 206, 87, 958, 586, 907, 659,
                 440, 603, 153, 223, 172, 424, 67, 377, 722, 141, 669, 115, 372, 262, 822, 299, 520, 935, 293, 829,
                 644, 668, 473, 84, 707, 384, 450, 236, 802, 370, 65, 78, 7, 312, 904, 544, 965, 512, 584, 296, 447,
                 985, 336, 922, 145, 342, 47, 614, 416, 319, 513, 787, 267, 352, 218, 655, 565, 648, 194, 807, 314,
                 905, 846, 228, 466, 37, 438, 412, 461, 654, 767, 121, 738, 809, 732, 548, 10, 728, 672, 304, 229,
                 845, 770, 335, 137, 589, 375, 790, 26, 843, 827, 25, 637, 276, 879, 941, 741, 506, 474, 928, 577,
                 991, 731, 459, 426, 811, 86, 594, 611, 971, 501, 43, 627, 338, 291, 41, 780, 203, 490, 39, 996,
                 74, 165, 891, 277, 246, 3, 960, 271, 143, 765, 46, 967, 925, 934, 280, 536, 90, 664, 819, 191,
                 156, 83, 588, 888, 792, 919, 686]
        _npn = int(_npn)
        sm = int(sm)
        if r_tbl and sm and _npn:
            _nsn = int(_nsn)
            st = ((_npn + _nsn) % 17) * 30 + _x + sm
            bx = str(r_tbl[st % 510]).zfill(3)
            st = ((_npn + _nsn + _x) % 17) * 30 + _y + sm + 13
            by = str(r_tbl[st % 510]).zfill(3)
        else:
            bx = str(_x).zfill(3)
            by = str(_y).zfill(3)

        return '_' + bx + '_' + by

    def get_manga_info(self, url):

        r = self.web_get(url)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)
        title = ''.join(html.xpath(self.xpath['manga_info_title'])).strip()
        episodes_etree = html.xpath(self.xpath['manga_info_episodes'])

        episodes = []
        for episode in episodes_etree:
            episode_title = ''.join(episode.xpath(self.xpath['manga_info_episode_title']))
            episode_link = ''.join(episode.xpath(self.xpath['manga_info_episode_link']))

            episode_link = self.convert_manga_url(episode_link)
            episode_info = self.get_episode_info(episode_link)
            episode_info = episode_info['episodes'][0]
            episodes.append(episode_info)

        return {
            'title': title,
            'episodes': episodes
        }

    def get_episode_images(self, url):
        r = self.web_get(url)
        html = etree.HTML(r.text)
        images = (html.xpath(self.xpath['episode_image_url']))
        title = ''.join(html.xpath(self.xpath['cur_episode_title']))

        return title, list(map(lambda img: self.domainUrl + img, images))

    @staticmethod
    def save_image(save_path, data):
        open(save_path, 'wb').write(data)

    @MangaCrawler.update_pbar
    async def download_image(self, episode_data, page, save_path):
        if os.path.exists(save_path):
            return

        logger.info('Download image from: {} to : {}'.format(episode_data, save_path))

        page_str = str(page).zfill(3)
        image_url = self.imageBaseUrl + '?uid=' + episode_data['uid'] + '&a=' + episode_data['base_a'] + page_str

        images = []
        x = 0
        max_pos_x = 0
        max_pos_y = 0
        while True:
            y = 0
            pre_pos_y = 0
            while True:
                tmp = self.get_ipnt_str(page, 6, episode_data['image_key'], x, y)
                part_image_url = image_url + '_06' + tmp + '.jpg'
                image_resp = self.web_get(part_image_url)
                if image_resp.status_code == 404:
                    break
                else:
                    im = Image.open(Bytes2Data(image_resp.content))
                    width, height = im.size
                    images.append({
                        'x': x * 480,
                        'y': pre_pos_y,
                        'data': im
                    })
                    pre_pos_x = x * 480 + width
                    pre_pos_y = pre_pos_y + height
                    if pre_pos_x > max_pos_x:
                        max_pos_x = pre_pos_x
                    if pre_pos_y > max_pos_y:
                        max_pos_y = pre_pos_y
                y += 1
            if y == 0:
                break
            x += 1
        image = Image.new('RGB', (max_pos_x, max_pos_y))
        for img in images:
            image.paste(img['data'], (img['x'], img['y']))
        if len(images) != 0:
            image.save(save_path)

    async def download(self, info):
        episode_dir = self.mk_episode_dir(self.save_dir, info['title'], info['episode'])

        with self.tqdm.tqdm(total=info['raw']['size'], ncols=75, unit='page') as pbar:
            self.pbar = pbar
            tasks = []
        # for i in self.tqdm.trange(info['raw']['size'], ncols=75, unit='page'):
        for i in range(info['raw']['size']):
            image_save_path = os.path.join(episode_dir, str(i + 1) + '.jpg')
            task = asyncio.ensure_future(self.download_image(info['raw'], i + 1, image_save_path))
            tasks.append(task)
            await asyncio.gather(*tasks)
            self.pbar = None

    def get_info(self, url):
        if url.find(self.domainUrl) == -1:
            logger.info('Type: Manga')

            episodes = self.get_manga_info(url)
            episodes['isEpisode'] = False
        else:
            logger.info('Type: Episode')

            episodes = self.get_episode_info(url)
            episodes['isEpisode'] = True
            episodes['episodes'][0]['isCurEpisode'] = True
        return episodes
