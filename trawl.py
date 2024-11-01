import re
import sys
import os
import glob
import shutil
import os.path as pp
from zipfile import ZipFile
from bs4 import BeautifulSoup
from tempfile import TemporaryDirectory
import logging
import requests as req
from datetime import datetime as dt
from argparse import ArgumentParser


logging.basicConfig(format='[%(asctime)s] [%(levelname)s] %(message)s', level=logging.DEBUG, filename="run.log")


def get_timestamp():
    return dt.now().strftime("%y%m%d_%H%M%S")


def extract_epub_to_temodir(epub_path: str, extract_to: str):
    logging.debug("Extracting epub file: `%s`", epub_path)
    with ZipFile(epub_path) as fp:
        fp.extractall(extract_to)
    logging.debug("    Extracted to: `%s`", extract_to)


def trawl_http_imgs(epub_epath: str) -> list:
    # for item in os.scandir(path):
    logging.debug("Finding *.html file(s) in `%s`", epub_epath)
    html_files = glob.glob(f"{epub_epath}/**/*.html", recursive=True)
    logging.debug("    Found %s *.html file(s)", len(html_files))
    found_http_imgs = []
    for html_file in html_files:
        html_file_name = pp.basename(html_file)
        logging.debug("Parsing `%s`", html_file_name)
        with open(html_file) as fp:
            bs = BeautifulSoup(fp, 'html.parser')
            http_imgs = bs.find_all("img", attrs={
                "src": re.compile(r"^http.*")
            })
            if not http_imgs:
                logging.debug("    Not found HTTP image(s)")
                continue
            found_http_imgs.extend([(i['src'], html_file) for i in http_imgs])
            logging.debug("    Found %s HTTP image(s)", len(http_imgs))
    return found_http_imgs


def localise_http_images(http_imgs: list, extract_to: str, save_epub_path: str = None, save_epub_alt: bool = False):

    def get_max_id(pool: list) -> int:
        max_int = 0
        for i in pool:
            matched = re.match(i['id'], r"^id(\d+)")
            if matched:
                cur_int = int(matched.group(1))
                max_int = max(cur_int, max_int)
        return max_int

    def get_media_type(path: str) -> int:
        reftab = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg'
        }
        matched = re.match("^.*\.(\w+)$", path)
        if matched:
            ext = matched.group(1)
            if ext not in reftab:
                logging.fatal('Ext %s not supported now', ext)
                exit(1)
            return reftab[ext]
        else:
            logging.fatal('No ext found for %s.', ext)
            exit(1)

    localized_images = []
    for (http_img_url, file_path) in http_imgs:
        res = req.get(http_img_url)
        img_name = pp.basename(http_img_url)

        article_path = pp.dirname(file_path)
        # 把图片保存到原本的位置，feed_X/article_X/images/中
        article_image_dpath = pp.join(article_path, 'images')
        if not pp.exists(article_image_dpath):
            article_image_dpath = pp.join(extract_to, 'images')
            if not pp.exists(article_image_dpath):
                os.makedirs(article_image_dpath, exist_ok=True)

        article_image_path = pp.join(article_image_dpath, img_name)
        with open(article_image_path, 'wb') as fi:
            fi.write(res.content)
            fi.close()

        # 替换.html文件中的<img src="">路径
        article_image_rpath = pp.relpath(article_image_path, article_path)
        with open(file_path) as fp:
            new_content = fp.read().replace(http_img_url, article_image_rpath, 1)
            fp.close()
            with open(file_path, 'w') as fpo:
                fpo.write(new_content)
                fpo.close()

        localized_images.append(article_image_path)


    # opf
    with open(pp.join(extract_to, 'content.opf')) as fp:
        fp.seek(0)
        bs = BeautifulSoup(fp, 'xml')
        manifest = bs.package.manifest
        manifest_items = manifest.find_all('item')
        max_id = get_max_id(manifest_items)

        for img_fpath in localized_images:
            img_rpath = pp.relpath(img_fpath, extract_to)
            media_type = get_media_type(img_rpath)
            new_item = bs.new_tag('item', id=f'id{max_id+1}', href=img_rpath, attrs={
                'media-type': media_type
            })
            manifest_items.append(new_item)
            max_id += 1
        fp.close()
        with open(pp.join(extract_to, 'content.opf'), 'w') as fpo:
            new_bs = bs.prettify(encoding='utf-8').decode()
            fpo.write(new_bs)
            fpo.close()

    if save_epub_alt and save_epub_path:
        new_epub_dir = pp.dirname(save_epub_path)
        shutil.make_archive(
            save_epub_path.replace('.epub', ''),
            'zip',
            extract_to,
            None)
        logging.debug("Saved as %s", save_epub_path)
        shutil.move(
            save_epub_path.replace('.epub', '.zip'),
            save_epub_path)

def parse_cmdargs():
    parser = ArgumentParser(
        description="Replenish the missing images of The economist epub file downloaded from calibre.",
        add_help=True)
    subparsers = parser.add_subparsers(dest='command', help='subcommand help')
    parser.add_argument('files', action='append',
                        metavar='EPUB_FILE',
                        help="specify the epub files")

    parser_a = subparsers.add_parser('check',
                                     help="only checks if there is missing images.")
    parser_a.add_argument('-l', '--list', action='store_true', help='show all missing images. only count by default.')


    parser_b = subparsers.add_parser('replenish',
                                     help="create a new epub file with missing images patched.")
    parser_b.add_argument('-r', '--override', action='store_true', help='replace the original file with new content.')


    return parser

if __name__ == '__main__':
    logging.info('--' * 12)

    prog = parse_cmdargs()
    args = prog.parse_args(sys.argv[1:])

    if args.command not in ('check', 'replenish'):
        prog.print_help()
        exit(1)

    not_existed_paths = [i for i in args.files if not pp.exists(i) or not pp.isfile(i)]
    if not_existed_paths:
        print("[Error] File(s) not exist:\n  ", '\n  '.join(not_existed_paths))
        logging.error("[Error] File(s) not exist:\n  ", '\n  '.join(not_existed_paths))
        exit(0)

    for epub_file in args.files:
        extract_to = TemporaryDirectory(prefix="epub_localimage.").name
        os.makedirs(extract_to, exist_ok=True)

        # 删除未被正常清除的temp
        temp_dir = pp.dirname(extract_to)
        for i in glob.glob(f"{temp_dir}/epub_localimage.*"):
            if pp.samefile(extract_to, i):
                continue
            shutil.rmtree(i)

        # 解压epub文件
        extract_epub_to_temodir(epub_file, extract_to)

        epub_name = pp.basename(epub_file)
        epub_name_new = re.subn(r"\.epub$", f".{get_timestamp()}.epub", epub_name, 1)
        epub_file_new = pp.join(pp.dirname(epub_file), epub_name_new[0])

        # wait = input("wait? (R) ")
        # if wait not in ['R']:
        #     exit(0)

        http_images = trawl_http_imgs(extract_to)

        logging.info("%s HTTP images found.", len(http_images))
        print(f"{len(http_images)} HTTP images found. Check log for details.")
        for (http_image_url, http_image_in_file) in http_images:
            if args.command == 'check' and args.list:
                print(f"[{http_image_in_file}] -> [{http_image_url}]")
            logging.info(f"[{http_image_in_file}] -> [{http_image_url}]")

        if args.command == 'plenish':
            epub_file_if = epub_file if args.override else epub_file_new
            localise_http_images(http_images, extract_to, save_epub_path=epub_file_if, save_epub_alt=True)

        logging.debug("Binning tempdir: `%s`", extract_to)
        shutil.rmtree(extract_to)
