# coding:utf-8

import yaml

import argparse
import sys, os

import logging

from manga import sites, MangaDownloader

parser = argparse.ArgumentParser()
parser.add_argument('urls', nargs='*',  help='input download url')
parser.add_argument('-c', '-config', '--config', help='YAML config file', action='store')
parser.add_argument('-d', '-dir', '--dir', help='download file save to directory path', action='store')
parser.add_argument('-debug', '--debug', help='debug', action='store_true')
# parser.add_argument('-g', '-gui', '--gui', help='Use gui', action='store_true')
parser.add_argument('-a', '-all', '--all', help='download all episodes', action='store_true')
args = parser.parse_args()


PROGRAM_DIR_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
DEFAULT_LOG_PATH = os.path.join(PROGRAM_DIR_PATH, 'run.log')
DEFAULT_DOWNLOAD_DIR_PATH = os.path.join(PROGRAM_DIR_PATH, 'download')

IS_DEBUG = args.debug

IS_ALL = args.all
# IS_GUI = args.gui
IS_GUI = False


YAML_CONFIG_PATH = None
if args.config is not None:
    YAML_CONFIG_PATH = os.path.normpath(os.path.abspath(args.config))

DOWNLOAD_DIR_PATH = DEFAULT_DOWNLOAD_DIR_PATH
if args.dir is not None:
    DOWNLOAD_DIR_PATH = os.path.normpath(os.path.abspath(args.dir))

INPUT_URLS = args.urls



def getValueOfDict(key, dictData):
    if key in dictData:
        return dictData[key]
    else:
        return None
def hasValueOfDict(key, dictData):
    if key in dictData:
        return True
    else:
        return False


def readConfigFromYAML(file):
    if file is not None:
        with open(file) as f:
            try:
                yamlConfig = yaml.safe_load(f)
                globalProxy = getValueOfDict('proxy', yamlConfig)
                if getValueOfDict('log', yamlConfig) is None:
                    yamlConfig['log'] = DEFAULT_LOG_PATH
                if yamlConfig['sites'] is None:
                    yamlConfig['sites'] = dict()
                for site in sites.keys():
                    siteConfig = getValueOfDict(site, yamlConfig['sites'])
                    if siteConfig is None:
                        yamlConfig['sites'][site] = {
                            'proxy': globalProxy,
                            'cookies_file': None
                        }
                    else:
                        if not hasValueOfDict('proxy', siteConfig):
                            siteConfig['proxy'] = globalProxy
                        if getValueOfDict('cookies_file', siteConfig) is None:
                            siteConfig['cookies_file'] = None
                    return yamlConfig
            except yaml.scanner.ScannerError as e:
                print('YAML file read error, using default')
    yamlConfig = {
        'log': DEFAULT_LOG_PATH,
        'proxy': None,
        'sites': {}
        }
    for site in sites.keys():
        yamlConfig['sites'][site] = {
            'proxy': None,
            'cookies_file': None
        }
    return yamlConfig

def main():
    yamlConfig = readConfigFromYAML(YAML_CONFIG_PATH)


    global logger

    logging.basicConfig(level = logging.DEBUG if IS_DEBUG else logging.INFO,
            filename=None if IS_DEBUG else yamlConfig['log'], filemode='a',
            format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger = logging.getLogger(__name__)

    logger.debug('Load config: {}'.format(yamlConfig))
    manga = MangaDownloader(yamlConfig['sites'], DEFAULT_DOWNLOAD_DIR_PATH)
    for url in INPUT_URLS:
       infos = manga.getInfo(url)
       for info in infos['episodes']:
            episode = info.copy()
            episode['title'] = infos['title']
            if IS_ALL:
                manga.download(infos['site'], episode)
            elif infos['isEpisode']:
                if 'isCurEpisode' in info.keys() and info['isCurEpisode']:
                    manga.download(infos['site'], episode)
                    break
            else:
                manga.download(infos['site'], episode)


if __name__ == '__main__':
    if IS_GUI:
        pass
    else:
        main()

