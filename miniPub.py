#!/usr/bin/env python3

#-*- coding: utf-8 -*-'

## @markdown
# TODO: 
# - read YFM and apply scoped configure.
# - add CallOut
## markdown@ 
        
import unittest
import argparse
import markdown2
import os
import json
import re
import yaml

import csv
# import copy
# from wcwidth import wcswidth
import unicodedata
from pathlib import Path
# from tempfile import TemporaryFile
import tempfile
import pathlib
import shutil

class bg:
    # https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797
    OKFOLDER = '\033[94m'       # blue
    OKCMD = '\033[92m'          # green
    OKFILE = '\033[93m'         #
    FAIL = '\033[91m'           # red
    WARN = '\033[95m'           # magenta
    ENDC = '\033[0m'

def warn(msg, detail):
    print(f'{bg.WARN}WARN-{msg}{bg.ENDC}{detail}')

options = []
abs_css = ''

class ReMarkdown:
    def __init__(self):
        # super().__init__()
        self.re_import_embdded = re.compile(r'^(#{1,5})\s(@import-embedded)\s*"(.*)"')
        self.re_import = re.compile(r'^(#{1,5})\s(@import)\s*\[\[(.*)\]\]')
        self.re_link = re.compile(r'(.*)(@link)\s*\[\[(.*)\]\]\s*\((.*)\)')    # ------
        self.re_number_level = re.compile(r'^(#{1,5})\s+(.*)')
        self.re_markdown_begin = re.compile(r'^(\s*)(\/\*\*\s@markdown)')
        self.re_markdown_end   = re.compile(r'^(\s*)(@markdown \*\*\/)')
        self.re_obsidian_image = re.compile(r'(.*)!\[\[(.*)\]\]')
        self.re_obsidian_link = re.compile(r'(.*)\s*\[\[(.*)\]\]')

    def proc_link(self, line, line_num) -> str:
        """ # @link [[도움말_요약]](../04. user manual/도움말_요약.md) """
        m = self.re_link.match(line)
        prefix = m[1]
        name = m[3]
        link = m[4]
        line = line + f'{prefix}[{name}]({link})'
        if os.path.isfile(dir + os.sep + link):
            print(f'      link {link}:{line_num}')
        else:
            warn( 'file not found: ', link)
        return line

    def proc_obsidian_link(self, line, line_num) -> str:
        """ [[name]] """
        m = self.re_obsidian_link.match(line)
        md = m[2]
        link = os.path.relpath(get_link(md + '.md'), os.getcwd())
        html = link.replace('.md', '.html')
        line = f'[{md}]({html})\n'
        if os.path.isfile(link):
            print(f'      ob_lnk: {link}:{line_num}')
        else:
            warn( 'file not found: ', link)
        return line

    def proc_obsidian_image(self, line, line_num) -> str:
        """ ![[name.png]] """
        m = self.re_obsidian_image.match(line)
        img = re.sub('#center', '', m[2])
        link = os.path.relpath(get_link(img), os.getcwd())
        line = f'![]({link})\n'
        if os.path.isfile(link):
            print(f'      ob_img: {link}:{line_num}')
        else:
            warn( 'file not found: ', link)
        return line

    def proc_import(self, line, line_num, depth=0) -> str:
        """ # @import [[도움말_요약]] """
        m = self.re_import.match(line)
        level_bias = m[1]
        md = m[3]
        import_md = os.path.relpath(get_link(md + '.md'), os.getcwd())
        try:
            print(f'      import: "{import_md}": {line_num}')
            line = self.get_md(import_md, depth+1, level_bias)
        except:
            warn( 'file not found: ', import_md) 
        return line
        # if temp.md: del it

    def proc_embeded(self, line, line_num, depth=0) -> str:
        """ ## @import-embedded "../sample.src/WD/WDPowershell.cs" """
        m = self.re_import_embdded.match(line)
        level_bias = m[1]
        src = m[3]
        import_src = os.path.relpath(src, os.getcwd())
        import_md = os.path.join(tempfile.mkdtemp(), '__temp__.md')
        if not os.path.exists(import_src):
            warn('file not found: ', f'{os.cwd()}:{import_src}')
        self.gen_embed2md(import_src, import_md)
        try:
            print(f'      import-emb: {src} -> "{import_md}": {line_num}')
            line = self.get_md(import_md, depth+1, level_bias)
            if len(line) == 0:
                warn('EMPTY embedded: ', import_md)
                line = f'WARN EMPTY embedded: {import_md}'
            os.remove(import_md)
        except:
            warn( 'file not found: ', import_md) 
        return line

    def gen_embed2md(self, src, md) -> str:
        """
        Generate a tempory markdown from Embeded files like ended with .cs, .cpp, .java. 
        Files applied with left spaces as its left trimming.
        """
        markdown = False
        tab_size = options['do']['tab-size']
        left_spaces = 0
        # CHECK extention here ++++  cs, c, cpp, java, NOT py yet
        with open(src, 'r', encoding='utf-8') as f, open(md, 'w', encoding='utf-8') as w:
            for line in f:
                if self.re_markdown_end.match(line):
                    markdown = False
                if markdown == True:
                    line = line.replace('\t', ' '*int(tab_size))
                    line = line[left_spaces:512]   # ++++ LINE SEP ????
                    if len(line) == 0:
                        line = os.linesep
                    w.write(line)
                if self.re_markdown_begin.match(line):
                    m = self.re_markdown_begin.match(line)
                    left_spaces = len(m[1].replace('\t', ' '*4))
                    markdown = True
        return line
            
    def get_md(self, md, depth = 0, bias = '#') -> str:
        """ 
        get a md file recursively imported - WARN: depth not limited. 
        """
        # print(f'====DEPTH: {depth}, bias: {bias}')
        line_num = 1
        lines = ''
        try:
            f = open(md, encoding='utf8')
            for line in f:
                if self.re_import_embdded.match(line):
                    line = self.proc_embeded(line, line_num, depth)

                if self.re_import.match(line):
                    line = self.proc_import(line, line_num, depth)
                elif self.re_link.match(line):
                    line = self.proc_link(line, line_num)
                elif self.re_obsidian_image.match(line):
                    line = self.proc_obsidian_image(line, line_num)
                elif self.re_obsidian_link.match(line):
                    line = self.proc_obsidian_link(line, line_num)

                line = re.sub(r'^(#)', f'{bias}', line)     # adjust the header bias
                if self.re_number_level.match(line):
                    m = self.re_number_level.match(line)
                    header_and_numbers = self.get_levels(m[1])
                    title = m[2]
                    line = f'{header_and_numbers} {title}\n'
                lines = lines + line   ### +++ REPLACE string builder
                line_num = line_num + 1
            f.close()
            return lines
        except:
            warn( 'File not found: ', md)
            return f'File not found: "{md}"\n'
        
    def clear_levels(self):
        """ clear all level counter """
        self.h1 = 0
        self.h2 = 0
        self.h3 = 0
        self.h4 = 0
        self.h5 = 0

    def get_levels(self, headers):
        """ get level number """
        global options
        self.number_level = options['do']['number-level']  # +++ NOT DEV YET
        if headers == '#':
            self.h1 = self.h1+1
            self.h2 = self.h3 = self.h4 = self.h5 = 0
            return_str = f'{headers} {self.h1}'
        elif headers == '##':
            self.h2 = self.h2+1
            self.h3 = self.h4 = self.h5 = 0
            return_str = f'{headers} {self.h1}.{self.h2}'
        elif headers == '###':
            self.h3 = self.h3+1
            self.h4 = self.h5 = 0
            return_str = f'{headers} {self.h1}.{self.h2}.{self.h3}'
        elif headers == '####':
            self.h4 = self.h4+1
            self.h5 = 0
            return_str = f'{headers} {self.h1}.{self.h2}.{self.h3}.{self.h4}'
        elif headers == '#####':
            self.h5 = self.h5+1
            return_str = f'{headers} {self.h1}.{self.h2}.{self.h3}.{self.h4}.{self.h5}'
        else:
            return_str = f'{headers}'
        return return_str + '.'        

def asian_pad(input_s, max_size=40, fill_char=' '):
    """
    - 길이가 긴 문자는 2칸으로 체크하고, 짧으면 1칸으로 체크함. 
    - 최대 길이(max_size)는 40이며, input_s의 실제 길이가 이보다 짧으면 남은 문자를 fill_char로 채운다.
    https://frhyme.github.io/python-libs/print_kor_and_en_full_half_width/
    """
    l = 0 
    for c in input_s:
        if unicodedata.east_asian_width(c) in ['F', 'W']:
            l+=2
        else: 
            l+=1
    return input_s+fill_char*(max_size-l)    

def pretty_dics(_list):
    if options['do']['verbose'] == 'True':
        for key, value in _list.items():
            _ = asian_pad(key)
            print( f'  {_} -> {value:100}')

def get_option(level1, level2) -> str:
    try:
        ret = options[level1][level2]
        return ret
    except:
        warn('No Value: ', f'{level1}.{level2}')
        raise Exception('No value: {level1}.{level2}')

links = {}
links_unused = {}

def find_links(folder='.'):
    """ find all obsidian link files endswith .md, .jpg, .png, etc. """
    global links, links_unused
    print('\n# STEP 1. find image & md files\n')
    for root, _, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(('.md', '.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                file_path = os.path.join(root, file)
                if file in links:
                    warn('Name collision detected: ', f'{links[file]} -> {file_path}')
                links[file] = os.path.abspath(file_path)
    print(f'Dictionary: {len(links)}')    # {pretty_dict}
    # pretty_dics(links)
    for key in links:
        if not '.md' in key:
            links_unused[key] = links[key]

def get_link(key):
    """ get a physical file location from the 'links' and remove from 'link_unused' dict. """
    global links, links_unused
    if key in links_unused:
        del links_unused[key]
    if key in links:
        return links[key]
    else:
        return f'"{key}"'

remark = ReMarkdown()

def convert_markdown_to_html(source_file, build_file):
    """ convert a markdown file to a html. """
    global base_css
    css = os.path.relpath(base_css, os.getcwd())
    title = pathlib.Path(os.path.basename(build_file)).stem

    remark.clear_levels()
    markdown_text = remark.get_md(source_file)
    with open(source_file + '.markdown', 'w', encoding='utf-8') as f:
         f.write(markdown_text)

    header = f'''
    <!DOCTYPE html>
    <html xmlns="http://www.w3.org/1999/xhtml" lang="" xml:lang="">
    <head>
      <meta charset="utf-8" />
      <meta name="generator" content="pandoc" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes" />
      <title> {title} </title>
      <link rel="stylesheet" href="{css}" />
    </head>
    <body>    
    '''

    tailer = r'''
    </body>
    </html>
    '''

    converter = markdown2.Markdown(extras=['tables', 'footnotes', 'fenced-code-blocks', 'header-ids', 'strike'])  
      # use-file-vars
    html_content = converter.convert(markdown_text)
    os.makedirs(os.path.dirname(build_file), exist_ok=True)
    with open(build_file, 'w', encoding='utf-8') as f:
        f.write(header)
        f.write(html_content)
        f.write(tailer)

    #  --toc --toc-depth=5
    # opt = '--css=../css/markdown7.css'
    # os.system(f'pandoc "{source_file}.markdown" -o "{build_file}" -f markdown {opt} --standalone --metadata pagetitle="{build_file}"')
    # os.remove

base_build = ''
base_css=''

# BUILD
def build(source, build):
    global base_css, base_build
    base_build = os.path.abspath(get_option('folders', 'build'))
    base_css = os.path.abspath(get_option('do', 'css'))
    print('\n# STEP 2. from md to target\n')
    os.chdir(source)
    base = os.getcwd()
    root = base
    ignores = get_option('do', 'ignores')
    sync_files(base, base_build, ('.css', '.jpg', '.jpeg', '.png', '.gif', '.bmp'), use_verbose=True)
    for root, _, files in os.walk(root):
        if any(word in root for word in ignores):
            continue
        print(f'  {bg.OKCMD}{root}{bg.ENDC}')        
        os.chdir(root)
        for file in files:
            if file.endswith('.md'):
                source_file = os.path.join(root, file)
                build_path = root.replace(base, base_build)
                os.makedirs(build_path, exist_ok=True)             
                build_file = os.path.join(build_path, file.replace('.md', '.html'))
                if not os.path.exists(build_file) or os.path.getmtime(source_file) >= os.path.getmtime(build_file):
                    print(f'    {bg.OKFILE}convert: {source_file}{bg.ENDC}')
                    convert_markdown_to_html(source_file, build_file)

# CLEAN
def clean(folder):
    for root, _, files in os.walk(folder):
        print(f'  {bg.OKCMD}{root}{bg.ENDC}')
        for file in files:
            if file.endswith(('.html', '.mark', '.markdown')):
                file_path = os.path.join(root, file)
                print(f'    cleaned: {file_path}')
                os.remove(file_path)

def sync_files(src, dest, extentions, use_verbose=True):   # ----------------
    if options['do']['verbose'] == 'True':
        use_verbose = True
    else:
        use_verbose = False

    ignores = get_option('do', 'ignores')
    for root, _, files in os.walk(src):
        if any(word in root for word in ignores):
            continue
        if use_verbose:
            print(f'  {bg.OKCMD}{root}{bg.ENDC}')
        for file in files:
            if file.endswith(extentions):
                path_from = os.path.join(root, file)
                path_to = path_from.replace(src, dest)
                if use_verbose:
                    print(f'    copy {path_from} -> {path_to}')
                if path_from == path_to:
                    continue
                try:
                    destination_dir = os.path.dirname(path_to)
                    os.makedirs(destination_dir, exist_ok=True)
                    shutil.copy2(path_from, path_to)
                except shutil.SameFileError:
                    pass
                except Exception as e:
                    print("Error:", e)

# DEPLOY
def deploy():
    base_build = os.path.abspath(get_option('folders', 'build'))
    base_deploy = os.path.abspath(get_option('folders', 'deploy'))
    extentions = ('.html', '.css', '.jpg', '.jpeg', '.png', '.gif', '.bmp')
    sync_files(base_build, base_deploy, extentions)
    
# TEST
class Test(unittest.TestCase):
    def test_flow(self):
        # touch two files for testing.
        Path('./sample.md/README.md').touch()
        Path('./sample.md/05. GS/03. 사용자취급설명서.html').touch()
        Path('./sample.md/05. GS/03. 사용자취급설명서.md').touch()
        # os_walk()
        # exit()
        self.assertTrue(True, True)        

if __name__ == '__main__':
    with open('miniPub.yml') as f:
        options = yaml.load(f, Loader=yaml.FullLoader)
        print('Options:\n', yaml.dump(options, default_flow_style=False))

    # parse args
    parser = argparse.ArgumentParser(description="Convert Markdown files to HTML")
    parser.add_argument("action", choices=['build', 'clean', 'deploy', 'test'], 
                        help="Action to perform: 'build' to convert Markdown to HTML,"
                        + " 'clean' to delete the build directory")
    parser.add_argument("--source", default=options['folders']['source'], help="source directory containing Markdown files")
    parser.add_argument("--build", default=options['folders']['build'], help="build directory to save HTML files")
    args = parser.parse_args()
    try:
        print(f'\n# {args.action}\n')
        if args.action == 'build':
            pushd = os.getcwd()
            # if not args.source or not args.build:
            #     parser.error("Please provide both source and build directories.")
            # phase 1
            find_links(args.source)
            # phase 2
            build(args.source, args.build)
            os.chdir(pushd)
            file = 'unused.csv'
            if os.path.exists(file):
                os.remove(file)
            if(len(links_unused) > 0):
                warn('Check: ', 'Unused links')
                print(f'Unused Dic: {len(links_unused)} / {len(links)}, Check {file}')
                pretty_dics(links_unused)
                with open('unused.csv','w', encoding='utf-8-sig') as f:
                    for key, value in links_unused.items():
                        f.write(f'{value}, {key}\n')
        elif args.action == 'clean':
            clean(args.build)
        elif args.action == 'test':
            unittest.main()
        elif args.action == 'deploy':
            deploy()
        else:
            parser.usage()
    except Exception as e:
            print(e)
            print(f'{bg.FAIL} This sw may has some problem.{bg.ENDC}')
    print('\n# finished.')
