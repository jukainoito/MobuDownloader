# coding:utf-8

from .manga_crawler import MangaCrawler
import re
import os
from lxml import etree
import threadpool
from urllib.parse import urljoin
from PIL import Image

from io import BytesIO as Bytes2Data


class HutabashaWeblish(MangaCrawler):

    domain_url = 'http://futabasha.pluginfree.com'
    image_base_url = 'http://futabasha.pluginfree.com/cgi-bin/widget.cgi'
    xpath = {
        'decode_key': '//*[@id="cKV"]/@title',
        'web_key': '//*[@id="hCN"]/@title',
        'init_data': '//*[@id="DATA"]/text()',
        'uid': '//*[@id="UID"]/@title',

        'page_num': '//*[@id="tPN"]/@title',
        'manga_key': '//*[@id="sHN"]/@title',
        'image_key': '//*[@id="sIS"]/@title',
        'episode_title': '//*[@id="sKey2"]/@title',

    }

    def __init__(self,  url, save_dir='.', num_workers=8):
        self.save_dir = save_dir
        self.url = url
        self.num_workers = num_workers
        self.task_pool = None

    @staticmethod
    def expand(_src, _key):
        bbc = [0, 1, 3, 7, 15, 31, 63, 127, 255, 511, 1023, 2047, 4095]
        kBase = "zBCfA!c#e@-UHTOtLEaDPVbXYjgNrRQlyFWpZ$+no*qIhKSvuxGk~siwm%:dJ/M?"
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
            _cs += kBase.index(_src[i])
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

    def get_episode_info(self, url):
        r = self.session.get(url, headers=self.headers)
        r.encoding = 'utf-8'
        html = etree.HTML(r.text)
        decode_key = ''.join(html.xpath(self.xpath['decode_key']))
        uid = ''.join(html.xpath(self.xpath['uid']))
        web_key = ''.join(html.xpath(self.xpath['web_key']))

        init_url = urljoin(url, 'InitVal.html')
        ir = self.session.get(init_url, headers=self.headers)
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
            "sel": True,
            "episode": episode_title,
            "pageSize": int(page_size),
            "status": "",
            "raw": {
                "size": int(page_size),
                "uid": uid,
                "base_a": base_a,
                "image_key": image_key
            }
        }]
        return {
            "title": title,
            "episodes": episodes
        }

    @staticmethod
    # page start 1  mag=6,9,12,15 x y
    # sm = image_key
    def getIpntStr(_npn, _nsn, sm, _x, _y):
        rTbl = [495, 510, 411, 433, 6, 425, 82, 889, 71, 422, 57, 445, 830, 260, 21, 649, 324, 249, 239,
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
        if rTbl and sm and _npn:
            _nsn = int(_nsn)
            st = ((_npn + _nsn) % 17) * 30 + _x + sm
            bx = str(rTbl[st % 510]).zfill(3)
            st = ((_npn + _nsn + _x) % 17) * 30 + _y + sm + 13
            by = str(rTbl[st % 510]).zfill(3)
        else:
            bx = str(_x).zfill(3)
            by = str(_y).zfill(3)

        return '_' + bx + '_' + by

    def get_manga_info(self, url):
        return None

    def get_episode_images(self, url):
        r = self.session.get(url, headers=self.headers)
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
                down_episodes.append(episode)
        return down_episodes

    @staticmethod
    def save_image(save_name, data):
        open(save_name, 'wb').write(data)

    def download_image(self, episode_data, page, save_name):
        page_str = str(page).zfill(3)
        image_url = self.image_base_url + '?uid=' + episode_data['uid'] + '&a=' + episode_data['base_a'] + page_str

        images = []
        x = 0
        max_pos_x = 0
        max_pos_y = 0
        while True:
            y = 0
            pre_pos_y = 0
            while True:
                tmp = self.getIpntStr(page, 6, episode_data['image_key'], x, y)
                part_image_url = image_url + '_06' + tmp + '.jpg'
                image_resp = self.session.get(part_image_url, headers=self.headers)
                if image_resp.status_code == 404:
                    break
                else:
                    im = Image.open(Bytes2Data(image_resp.content))
                    width, height = im.size
                    images.append({
                        "x": x*480,
                        "y": pre_pos_y,
                        "data": im
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
        image = Image.new("RGB", (max_pos_x, max_pos_y))
        for img in images:
            image.paste(img['data'], (img['x'], img['y']))
        if len(images) != 0:
            image.save(save_name)

    def download(self, data):
        episodes = self.get_download_episode(data)

        self.task_pool = threadpool.ThreadPool(self.num_workers)
        task_args_list = []
        for episode in episodes:
            episode_dir = self.mk_episode_dir(self.save_dir, data['title'], episode['episode'])
            episode['status'] = "开始下载"
            if episode_dir is not None:
                for i in range(episode['raw']['size']):
                    image_save_path = os.path.join(episode_dir, str(i + 1) + '.jpg')
                    task_args = [episode['raw'], i + 1, image_save_path]
                    task_args_list.append((task_args, None))

        task_requests = threadpool.makeRequests(self.download_image, task_args_list)

        [self.task_pool.putRequest(req) for req in task_requests]

    def info(self):
        return self.get_episode_info(self.url)
