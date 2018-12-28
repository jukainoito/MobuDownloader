from manga_site import *
import tkinter
import tkinter.messagebox
import threading
import traceback

from urllib.parse import urlparse

save_dir = '.'

program_title = "mobu tool v0.02b - only support mangapoke and ComicWalker"


def download_manga(url):
    if url.find(r'//') == -1:
        url = '//' + url
    netloc = urlparse(url).netloc
    if netloc == 'pocket.shonenmagazine.com':
        downloader = MangaPoke(url, save_dir)
    elif netloc == 'comic-walker.com':
        downloader = MangaWalker(url, save_dir)
    else:
        tkinter.messagebox.showerror('错误', '只支持以下站点:\n pocket.shonenmagazine.com\n comic-walker.com ')
        return
    downloader.download()


def change_ui():
    global running
    running = not running
    if running:
        edit_url.config(state=tkinter.DISABLED)
        btn_download.config(state=tkinter.DISABLED)
    else:
        edit_url.config(state=tkinter.NORMAL)
        btn_download.config(state=tkinter.NORMAL)

def download_task(url):
    try:
        download_manga(url)
    except:
        tkinter.messagebox.showerror('错误', '抓取网页信息出错')
        traceback.print_exc()
    finally:
        change_ui()

def click_download():
    url = edit_url.get()
    change_ui()
    t = threading.Thread(target=download_task, args=(url,))

    t.start()




def gui():
    root = tkinter.Tk()

    root.title(program_title)
    root.geometry('400x30')
    frame = tkinter.Frame(root)
    frame.pack()

    global running
    running = False

    global edit_url
    edit_url = tkinter.Entry(frame, bd=1, width= 46)
    edit_url.pack(side=tkinter.LEFT)

    global btn_download
    btn_download = tkinter.Button(frame, text='download', command = click_download)
    btn_download.pack(side=tkinter.RIGHT)



    root.mainloop()


gui()
