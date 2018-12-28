from abc import ABCMeta, abstractmethod

class MangaCrawler:
    __metaclass__ = ABCMeta

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'}


    @abstractmethod
    def download(self):
        pass