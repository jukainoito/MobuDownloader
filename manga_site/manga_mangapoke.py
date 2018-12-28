from .manga_crawler import MangaCrawler
import requests
from lxml import etree
from PIL import Image
import json
import os
import threadpool

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

    def __init__(self,  url, save_dir='.', num_workers=8):
        self.save_dir = save_dir
        self.url = url
        self.num_workers = num_workers

    def get_manga_index(self, url):
        page = requests.get(url, headers=self.headers)
        page.encoding = 'utf-8'

        html = etree.HTML(page.text)

        title = ''.join(html.xpath(self.xpaths['title']))
        episode_new_open = html.xpath(self.xpaths['episode_new_open'])
        episode_old_open = html.xpath(self.xpaths['episode_old_open'])
        episode_open = episode_new_open + episode_old_open

        episode_more_url = ''.join(html.xpath(self.xpaths['episode_more_url']))
        if len(episode_more_url) != 0:
            r_more = requests.get(episode_more_url, headers=self.headers)
            more_data = json.loads(r_more.text)
            more_html = etree.HTML(more_data['html'])
            episode_more_open = more_html.xpath(self.xpaths['episode_more_open'])
            episode_open = episode_open + episode_more_open

        episodes = list()

        for episode in episode_open:
            open_status = ''.join(episode.xpath('div[2]/span[2]/@class'))
            if 'private' not in open_status:
                episodes.append(''.join(episode.xpath('@href')))

        cur_episode_title = ''.join(html.xpath(self.xpaths['cur_episode']['title']))
        cur_episode_images = html.xpath(self.xpaths['cur_episode']['images'])

        return {
            'title': title,
            'episodes': episodes,
            'cur_episode': {
                'title': cur_episode_title,
                'images': cur_episode_images
            }
        }

    def get_episode_info(self, url):
        page = requests.get(url, headers=self.headers)
        page.encoding = 'utf-8'

        html = etree.HTML(page.text)
        cur_episode_title = ''.join(html.xpath(self.xpaths['cur_episode']['title']))
        cur_episode_images = html.xpath(self.xpaths['cur_episode']['images'])

        return {
            'title': cur_episode_title,
            'images': cur_episode_images
        }

    def download_episode(self, episode, dir):

        episode_dir = os.path.join(dir, episode['title'])
        if os.path.exists(os.path.normpath(episode_dir)):
            return False
        os.makedirs(os.path.normpath(episode_dir))

        task_pool = threadpool.ThreadPool(self.num_workers)
        task_args_list = []
        for i, image_url in enumerate(episode['images']):
            image_save_path = os.path.join(episode_dir, str(i + 1) + '.jpg')
            task_args = [image_url, image_save_path]
            task_args_list.append((task_args, None))


        task_requests = threadpool.makeRequests(self.download_image, task_args_list)

        [task_pool.putRequest(req) for req in task_requests]

        task_pool.wait()

    def download_image(self, url, save_name):
        r = requests.get(url)
        with open(save_name, "wb") as file:
            file.write(r.content)
            self.handle_image(save_name)
        print(save_name)

    def handle_image(self,save_name):
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
                if (start_y < im.height + 10 and start_y > im.height - 10):
                    start = (int(start[0] + w_step), 0)
                else:
                    start = (start[0], start_y)
        start = (0, 0)

        for i in range(0, 4):
            for j in range(0, 4):
                end = (start[0] + w_step, start[1] + h_step)
                im.paste(ims[i * 4 + j], start + end)

                start_x = int(start[0] + w_step)
                if (start_x < im.width + 10 and start_x > im.width - 10):
                    start = (0, start[1] + h_step)
                else:
                    start = (start_x, start[1])
        im.save(save_name)

    def download(self):
        manga_index = self.get_manga_index(self.url)
        manga_dir = os.path.join(self.save_dir, manga_index['title'])
        self.download_episode(manga_index['cur_episode'], manga_dir)
        # 不抓取其他episode
        # for episodes_url in manga_index['episodes']:
        #     episode_info = get_episode_info(episodes_url)
        #     download_episode(episode_info, manga_dir)