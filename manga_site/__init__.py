from .manga_crawler import MangaCrawler
from .manga_mangapoke import MangaPoke
from .manga_walker import MangaWalker

sites = {
    "pocket.shonenmagazine.com": MangaPoke,
    "comic-walker.com": MangaWalker
}