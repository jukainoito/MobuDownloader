## Usage
```bash
python main.py [OPTION]... URL...
```
### Option
* -c, -config, --config. YAML config file
* -d, -dir, --dir. manga  save directory path
* -a, -all, --all, download url all manga

### Config file
```yaml
log: # log file path, default use run.log
proxy: # global proxy url. e.g., socks5://127.0.0.1:1080
sites: # download site config
  pocket.shonenmagazine.com: # site domain
    proxy: # site use proxy url, default us global proxy url
    cookies_file: # site cookies file path. use EditThisCookie export
  comic-walker.com:
    proxy:
    cookies_file:
  web-ace.jp:
    proxy:
    cookies_file:
  cycomi.com:
    proxy:
    cookies_file:
  www.comic-earthstar.jp:
    proxy:
    cookies_file:
  viewer.comic-earthstar.jp:
    proxy:
    cookies_file:
  www.comic-medu.com:
    proxy:
    cookies_file:
  futabasha.pluginfree.com:
    proxy:
    cookies_file:
  webaction.jp:
    proxy:
    cookies_file:
  www.alphapolis.co.jp:
    proxy:
    cookies_file:

```


## Sites
Only free episode

* [マガポケ](https://pocket.shonenmagazine.com/)
* [コミックウォーカー](https://comic-walker.com/)
* [webエース](https://web-ace.jp/)
* [サイコミ](https://cycomi.com/)
* [コミック　アース・スター](https://comic-earthstar.jp/)
* [COMIC MeDu （こみっくめづ）](http://www.comic-medu.com/)
* ~~[双葉社ＷＥＢアクション(pluginfree)](http://futabasha.pluginfree.com/) (Only episode page, manga from [ＷＥＢアクション](http://webaction.jp) )~~
* [アルファポリス(公式Web漫画)](https://www.alphapolis.co.jp/manga/official)
