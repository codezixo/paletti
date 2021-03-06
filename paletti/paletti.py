from collections import namedtuple
from colorama import init, Fore, Style
import colorific
import json
import numpy as np
from PIL import Image, ImageDraw
from prettytable import PrettyTable
import requests
import os.path as osp
from sklearn.cluster import KMeans

from utils import hex2rgb, lab2rgb, rgb2hex, rgb2lab

init()

Palette = namedtuple('Palette', 'colors percent')
RSIZE = 600


def kmeans_palette(fname, k=5):
    """ Extract a color palette using k-means clustering. """
    origimg = Image.open(fname)
    origimg.thumbnail((RSIZE, RSIZE), Image.ANTIALIAS)
    img = rgb2lab(np.asarray(origimg))
    w, h, d = tuple(img.shape)
    assert d == 3
    imarr = np.reshape(img, (w * h, d))
    # Perform k-means clustering
    kmeans = KMeans(n_clusters=k, n_jobs=-1).fit(imarr)
    labels = kmeans.predict(imarr)
    maincolors = kmeans.cluster_centers_
    maincolors = np.expand_dims(maincolors, axis=0)
    maincolors = lab2rgb(maincolors).squeeze()
    maincolors = maincolors.astype('float64') / 255.
    # Save clustered image
    cluster_img = np.zeros(imarr.shape, dtype='float')
    for i, lab in enumerate(labels):
        cluster_img[i] = maincolors[lab]
    Image.fromarray(
        (np.reshape(cluster_img, (w, h, 3)) * 255).astype(
            'uint8')).save('{}_clustered.png'.format(osp.splitext(fname)[0]))
    # Compute percentage of each main color
    percent, _ = np.histogram(labels, bins=len(maincolors), normed=True)
    percent /= float(percent.sum())
    return Palette(maincolors.squeeze(), percent)


def colorific_palette(fname, k=5):
    """ Extract a color palette using colorific. """
    result = np.asarray(colorific.extract_colors(fname, max_colors=k)[0])
    maincolors = np.asarray([list(c) for c in result[:, 0]]) / 255.
    percent = result[:, 1] / np.sum(result[:, 1])
    return Palette(maincolors, percent)


def pil_palette(fname, k=5):
    """ Extract a color palette using PIL. """
    image = Image.open(fname)
    image.thumbnail((RSIZE, RSIZE), Image.ANTIALIAS)
    result = image.convert(
        'P', palette=Image.ADAPTIVE, colors=k).convert('RGB')
    res = result.getcolors(RSIZE ** 2)
    maincolors = np.asarray([x[1] for x in res]) / 255.
    percent = np.asarray([x[0] for x in res], dtype='float')
    percent /= percent.sum()
    return Palette(maincolors, percent)


def pictaculous_palette(fname):
    """ Extract a color palette using the pictaculous API. """
    endpoint = 'http://pictaculous.com/api/1.0/'
    r = requests.post(endpoint, {'image': open(fname, 'rb').read()})
    data = json.loads(r.text)
    maincolors = data['info']['colors']
    maincolors = np.asarray([hex2rgb(c) for c in maincolors]) / 255.
    return Palette(maincolors, [1.0 / len(maincolors)] * len(maincolors))


def get_palette(fname, k=5, method='k-means'):
    """ Extract a color palette from an image using the specified method. """
    if method == 'k-means':
        return kmeans_palette(fname, k=k)
    elif method == 'colorific':
        return colorific_palette(fname, k=k)
    elif method == 'pil':
        return pil_palette(fname, k=k)
    elif method == 'pictaculous':
        return pictaculous_palette(fname)


def print_palette(fname, palette, method):
    """ Print palette colors. """
    print('\nColor palette of ' + Fore.CYAN + Style.BRIGHT + '{}'.format(fname)
          + Style.RESET_ALL + ' using ' + Fore.CYAN + Style.BRIGHT
          + '{}'.format(method) + Style.RESET_ALL + ':\n')
    table = PrettyTable(
        [Fore.CYAN + Style.BRIGHT + "rgb" + Style.RESET_ALL,
         Fore.CYAN + Style.BRIGHT + "hex" + Style.RESET_ALL,
         Fore.CYAN + Style.BRIGHT + "proportion" + Style.RESET_ALL],
        padding_width=5)
    rgbs = [(np.asarray(c) * 255).astype('uint8') for c in palette.colors]
    hexs = [rgb2hex(tuple(c)) for c in rgbs]
    for rgb, h, p in zip(rgbs, hexs, palette.percent):
        table.add_row(
            ['({:3}, {:3}, {:3})'.format(*tuple(rgb)), h, '{:.2}'.format(p)])
    print table


def create_palette(palette, outname='palette.png', save=True, size=(300, 80)):
    """ Create (and save) palette. """
    width, height = size
    img = Image.new('RGB', size)
    draw = ImageDraw.Draw(img)
    maincolors = [(np.array(c) * 255).astype('uint8') for c in palette.colors]
    start_x = 0
    for c, p in zip(maincolors, palette.percent):
        end_x = start_x + (p * width)
        (x1, y1) = (start_x, 0)
        (x2, y2) = (end_x, height-1)
        draw.rectangle([(x1, y1), (x2, y2)], fill=tuple(c))
        start_x = end_x
    if not save:
        return img
    if not outname.endswith('.png'):
        outname = '{}_palette.png'.format(osp.splitext(outname)[0])
        print('\nPalette saved in' + Fore.CYAN + Style.BRIGHT + ' {} ...\n'
              .format(outname))
    img.save(outname, "PNG")
