# coding:utf-8
import argparse
import logging
import os
import sys

import yaml

from manga import sites, MangaDownloader

parser = argparse.ArgumentParser()
parser.add_argument('urls', nargs='*', help='input download url')
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


def get_value_of_dict(key, dict_data):
    if key in dict_data:
        return dict_data[key]
    else:
        return None


def has_value_of_dict(key, dict_data):
    if key in dict_data:
        return True
    else:
        return False


def read_config_from_yaml(file):
    if file is not None:
        with open(file) as f:
            try:
                yaml_config = yaml.safe_load(f)
                global_proxy = get_value_of_dict('proxy', yaml_config)
                if get_value_of_dict('log', yaml_config) is None:
                    yaml_config['log'] = DEFAULT_LOG_PATH
                if 'sites' not in yaml_config or yaml_config['sites'] is None:
                    yaml_config['sites'] = dict()
                for site in sites.keys():
                    site_config = get_value_of_dict(site, yaml_config['sites'])
                    if site_config is None:
                        yaml_config['sites'][site] = {
                            'proxy': global_proxy,
                            'cookies_file': None
                        }
                    else:
                        if not has_value_of_dict('proxy', site_config):
                            site_config['proxy'] = global_proxy
                        if get_value_of_dict('cookies_file', site_config) is None:
                            site_config['cookies_file'] = None
                return yaml_config
            except yaml.scanner.ScannerError:
                print('YAML file read error, using default')
    yaml_config = {
        'log': DEFAULT_LOG_PATH,
        'proxy': None,
        'sites': {}
    }
    for site in sites.keys():
        yaml_config['sites'][site] = {
            'proxy': None,
            'cookies_file': None
        }
    return yaml_config


def main():
    yaml_config = read_config_from_yaml(YAML_CONFIG_PATH)

    global logger

    logging.basicConfig(level=logging.DEBUG if IS_DEBUG else logging.INFO,
                        filename=None if IS_DEBUG else yaml_config['log'], filemode='a',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger = logging.getLogger(__name__)

    logger.debug('Load config: {}'.format(yaml_config))
    manga = MangaDownloader(yaml_config['sites'], DEFAULT_DOWNLOAD_DIR_PATH, default_proxy=yaml_config['proxy'])
    for url in INPUT_URLS:
        infos = manga.get_info(url)
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
