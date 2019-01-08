from .manga_crawler import MangaCrawler
from .manga_mangapoke import MangaPoke
from .manga_walker import MangaWalker
from .web_ace import WebAce
from .cycomi import Cycomi
from .comic_earthstar import ComicEarthStat

sites = {
    "pocket.shonenmagazine.com": MangaPoke,
    "comic-walker.com": MangaWalker,
    "web-ace.jp": WebAce,
    "cycomi.com": Cycomi,
    "viewer.comic-earthstar.jp": ComicEarthStat,
    "www.comic-earthstar.jp": ComicEarthStat,
    "comic-earthstar.jp": ComicEarthStat
}