#!/usr/bin/env python3
import gettext
import logging
import lzma
import os.path
import sys

import requests

from lexutils import config
from lexutils.helpers import tui

_ = gettext.gettext


def fetch():
    logger = logging.getLogger(__name__)
    # for now we only support europarl data from
    # https://github.com/egils-consulting/LexUse-data
    # download choosen language file
    url = ("https://github.com/egils-consulting/LexUse-data/raw/master/" +
           f"{config.language_code}.xz")
    # inspired by http://stackoverflow.com/questions/15644964/ddg#15645088
    # this will take only -1 splitted part of the url
    filename = "data_" + url.split('/')[-1]
    txt_filename = filename.replace("xz", "txt")
    if os.path.isfile(txt_filename):
        logging.info(_("Data for {} has ".format(config.language) +
                       "already been downloaded."))
    else:
        tui.europarl_download()
        with open(filename, 'wb') as output_file:
            response = requests.get(url, stream=True)
            total_length = response.headers.get('content-length')
            if total_length is None:
                # no content length header
                output_file.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in response.iter_content(chunk_size=4096):
                    dl += len(data)
                    output_file.write(data)
                    done = int(50 * dl / total_length)
                    sys.stdout.write(
                        "\r[%s%s]" % ('=' * done, ' ' * (50-done))
                    )
                    sys.stdout.flush()

        print('\nDownload Completed!!!')

        if os.path.isfile(filename):
            print("Decompressing file")
            with lzma.open(filename, 'rb') as f:
                # f is now the uncompressed object
                # write it to
                with open(txt_filename, 'wb') as out:
                    out.write(f.read())
        else:
            logging.error("Error. Download failed. Report this bug.")
