# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2018 OzzieIsaacs
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import division, print_function, unicode_literals
import os
import re

from . import logger, isoLanguages
from .constants import BookMeta


log = logger.create()


try:
    from comicapi.comicarchive import ComicArchive, MetaDataStyle
    use_comic_meta = True
except ImportError as e:
    log.debug('cannot import comicapi, extracting comic metadata will not work: %s', e)
    import zipfile
    import tarfile
    use_comic_meta = False


def extractCover(tmp_file_name, original_file_extension):
    if use_comic_meta:
        archive = ComicArchive(tmp_file_name)
        cover_data = None
        for index, name in enumerate(archive.getPageNameList(sort_list=True)):
            ext = os.path.splitext(name)
            if len(ext) > 1:
                extension = ext[1].lower()
                if extension in {'.jpg', '.jpeg', '.png'}:
                    cover_data = archive.getPage(index)
                    break
    else:
        if original_file_extension.upper() in {'.CBZ', '.ZIP'}:
            cf = zipfile.ZipFile(tmp_file_name)
            for name in sorted(cf.namelist()):
                ext = os.path.splitext(name)
                if len(ext) > 1:
                    extension = ext[1].lower()
                    if extension in {'.jpg', '.jpeg', '.png'}:
                        cover_data = cf.read(name)
                        break
        elif original_file_extension.upper() in {'.CBT', '.TAR'}:
            cf = tarfile.TarFile(tmp_file_name)
            for name in sorted(cf.getnames()):
                ext = os.path.splitext(name)
                if len(ext) > 1:
                    extension = ext[1].lower()
                    if extension in {'.jpg', '.jpeg', '.png'}:
                        cover_data = cf.extractfile(name).read()
                        break

    prefix = os.path.dirname(tmp_file_name)
    if cover_data:
        tmp_cover_name = prefix + '/cover' + extension
        image = open(tmp_cover_name, 'wb')
        image.write(cover_data)
        image.close()
    else:
        tmp_cover_name = None
    return tmp_cover_name


def get_comic_info(tmp_file_path, original_file_name, original_file_extension):
    if use_comic_meta:
        archive = ComicArchive(tmp_file_path)
        if archive.seemsToBeAComicArchive():
            if archive.hasMetadata(MetaDataStyle.CIX):
                style = MetaDataStyle.CIX
            elif archive.hasMetadata(MetaDataStyle.CBI):
                style = MetaDataStyle.CBI
            else:
                style = None

            # if style is not None:
            loadedMetadata = archive.readMetadata(style)

            lang = loadedMetadata.language
            if lang:
                if len(lang) == 2:
                     loadedMetadata.language = isoLanguages.get(part1=lang).name
                elif len(lang) == 3:
                     loadedMetadata.language = isoLanguages.get(part3=lang).name
            else:
                 loadedMetadata.language = ""

        return BookMeta(
                file_path=tmp_file_path,
                extension=original_file_extension,
                title=loadedMetadata.title or original_file_name,
                author=" & ".join([credit["person"] for credit in loadedMetadata.credits if credit["role"] == "Writer"]) or u'Unknown',
                cover=extractCover(tmp_file_path, original_file_extension),
                description=loadedMetadata.comments or "",
                tags="",
                series=loadedMetadata.series or "",
                series_id=loadedMetadata.issue or "",
                languages=loadedMetadata.language)
    else:

        info_dict = get_komidl_info(tmp_file_path, original_file_extension)

        return BookMeta(
            file_path=tmp_file_path,
            extension=original_file_extension,
            title=info_dict.get('TITLE', original_file_name),
            author=info_dict.get('CREDIT', u'UNKNOWN'),
            cover=extractCover(tmp_file_path, original_file_extension),
            description=info_dict.get('DESC', ""),
            tags=info_dict.get('TAGS', ""),
            series=info_dict.get('SERIES', ""),
            series_id="",
            languages=info_dict.get('LANGUAGES', ""))


def get_komidl_info(tmp_file_name, original_file_extension):
    """Return a dictionary of parsed values from KomiDL tags"""
    info_str = get_komidl_info_str(tmp_file_name, original_file_extension)
    return parse_komidl_info(info_str)


def parse_komidl_info(info_str):
    """Parse the KomiDL tags from the string and return a dict"""
    if not info_str:
        return {}
    lines = info_str.splitlines()
    # Each key-val may split into >2 fields if a ':' char exists in val
    # Ex. ['URL', 'http', '//...']
    key_vals = (list(line.split(':')) for line in lines)
    # Join with ':' for lists with >2 fields
    return {token[0]: ':'.join(token[1:]) for token in key_vals}


def get_komidl_info_str(tmp_file_name, original_file_extension):
    """Return the raw string data from the KomiDL tag file"""
    if original_file_extension.upper() == '.CBZ':
            cf = zipfile.ZipFile(tmp_file_name)
            filenames = list(sorted(cf.namelist()))
            if 'info.txt' == os.path.split(filenames[-1])[1]:
                    info_str = cf.read(filenames[-1])
                    return info_str.decode('utf-8')
    elif original_file_extension.upper() == '.CBT':
            cf = tarfile.TarFile(tmp_file_name)
            filenames = list(sorted(cf.getnames()))
            if 'info.txt' == os.path.split(filenames[-1])[1]:
                    info_str = cf.extractfile(filenames[-1]).read()
                    return info_str.decode('utf-8')
    return None
