# coding:utf-8

from abc import ABCMeta, abstractmethod
import os


class MangaCrawler:
    __metaclass__ = ABCMeta

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'}


    @abstractmethod
    def done(self):
        pass

    @abstractmethod
    def download(self, data):
        pass

    @abstractmethod
    def info(self):
        pass

    @staticmethod
    def mk_episode_dir(save_dir, title, episode_title):
        episode_dir = os.path.join(save_dir, title, episode_title)
        if os.path.exists(os.path.normpath(episode_dir)):
            return None
        os.makedirs(os.path.normpath(episode_dir))
        return episode_dir
