#! /usr/bin/env python
#
#   shoutcast_search.py - a library to search shoutcast.com
#
#   Copyright (c) 2009-2010 by the Authors.
#   Please report bugs or feature requests by e-mail. Also, I'd be happy
#   to hear from you if you enjoy this software.
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import argparse
import re
import random
import sys
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET

import pkg_resources


def _from_UTF_8(inbytes):
    return str(inbytes, 'UTF-8')


def _build_search_url(params):
    '''
    Return URL to search web service with appropriately encoded parameters.
      params - See urllib.urlencode
    '''
    return 'http://yp.shoutcast.com/sbin/newxml.phtml?{0}'.format(
        urllib.parse.urlencode(params))


def _retrieve_search_results(params):
    ''' Perform search against shoutcast.com web service.
        params - See urllib.urlencode and
                 http://forums.winamp.com/showthread.php?threadid=295638
    '''
    req = urllib.request.Request(_build_search_url(params))
    # Fake real user agent
    req.add_header('User-Agent',
                   ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) '
                    'AppleWebKit/537.1 (KHTML, like Gecko) '
                    'Chrome/21.0.1200.0 Iron/21.0.1200.0 Safari/537.1'))
    content = _from_UTF_8(urllib.request.urlopen(req).read())

    root = ET.fromstring(content)
    return [station.attrib for station in root.iter('station')]


def url_by_id(index):
    '''
    Returns the stations URL based on its ID
    '''
    url = 'http://yp.shoutcast.com/sbin/tunein-station.pls?id={0}'
    return url.format(index)


def get_genres():
    '''
    Returns a list of genres (listed by the shoutcast web service).
    Raises urllib2.URLError if network communication fails
    '''
    req = urllib.request.Request('http://yp.shoutcast.com/sbin/newxml.phtml')
    # Fake real user agent
    req.add_header('User-Agent',
                   ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) '
                    'AppleWebKit/537.1 (KHTML, like Gecko) '
                    'Chrome/21.0.1200.0 Iron/21.0.1200.0 Safari/537.1'))
    content = _from_UTF_8(urllib.request.urlopen(req).read())
    root = ET.fromstring(content)
    return [genre.attrib['name'] for genre in root.iter('genre')]


def search(search=[], station=[], genre=[], song=[],
           bitrate_fn=lambda x: True, listeners_fn=lambda x: True,
           mime_type='', limit=0, randomize=False, sorters=[]):
    ''' Search shoutcast.com for streams with given criteria.

    See http://forums.winamp.com/showthread.php?threadid=295638 for details
    and rules. Raises urllib2.URLError if network communication fails.
      search - List of free-form keywords. Searches in station names, genres
               and songs.
      station - List of phrases to find in station names.
      genre - List of phrases to find in genres.
      song - List of phrases to find in "currently playing" string
             e.g artist or song name.
      bitrate_fn - function with bitrate as argument. Should return True
                   if station is a keeper.
      listeners_fn function with number of listeners as argument.
                   Should return True if station is a keeper.
      mime_type - filter stations by MIME type
      limit - maximum number of stations returned. 0 means unlimited.
      randomize - should results be returned in random order? True / False
      sorters - a list of functions accepting the station list and returning
                a modified one. Executed after randomization / sorting by
                number of listeners.

    Returns a list with one dict per station. Each dict contains:
      'name' - station name
      'mt' - mime type
      'id' - station id (used in URL)
      'br' - bitrate in kbps
      'genre' - station genre(s)
      'ct' - currently played track
      'lc' - listener count
    '''

    opt_dict = {}
    keywords = search + station + genre + song

    if mime_type:
        opt_dict['mt'] = mime_type

    if not keywords:   # No content to search, use default
        opt_dict['genre'] = 'Top500'

# Perform search with empty keywords
        results = _retrieve_search_results(opt_dict)
    else:
        # Find everything applicable and filter ourselves, since the API
        # is limited.
        # Not very elegant, and quite slow with big queries.
        # No problem with normal use, though.
        results = []
        known_ids = []  # "cache" found station ids to make code easier below
        for k in keywords:
            opt_dict.update({'search': k})
            results += [row for row in _retrieve_search_results(opt_dict)
                        if row['id'] not in known_ids]
            known_ids = [row['id'] for row in results]

    # Filter for bitrate
    results = [r for r in results if bitrate_fn(r['br'])]
    # Filter by listeners
    results = [r for r in results if listeners_fn(r['lc'])]

    # Now filter all the stations we've got. AND all criteria. Not super fast,
    # but OK for normal use
    for s in station:
        results = [r for r in results if s.upper() in r['name'].upper()]
    for g in genre:
        results = [r for r in results if g.upper() in r['genre'].upper()]
    for s in song:
        results = [r for r in results if s.upper() in r['ct'].upper()]
    for k in keywords:
        results = [r for r in results
                   if k.upper() in '{0} {1} {2}'.format(r['name'], r['genre'],
                                                        r['ct']).upper()]

    if randomize:
        random.shuffle(results)
    else:
        # Sort by listener count
        results.sort(key=lambda x: int(x['lc']), reverse=True)

    for m in sorters:
        results = m(results)

    if limit > 0:
        results = results[:limit]

    return results


def get_egg_description():
    dist = pkg_resources.get_distribution("shoutcast-search")
    for line in dist.get_metadata(dist.PKG_INFO).splitlines():
        if line.lower().startswith('description:'):
            return line.split(':', 1)[1].strip()
    return ''


def _station_text(station_info, format):
    url = url_by_id(station_info['id'])

    replacements = {'%g': station_info['genre'],
                    '%p': station_info['ct'],
                    '%s': station_info['name'],
                    '%b': station_info['br'],
                    '%l': station_info['lc'],
                    '%t': station_info['mt'],
                    '%u': url,
                    '%%': '%',
                    '\\n': '\n',
                    '\\t': '\t'}
    resstr = format
    for key, value in replacements.items():
        resstr = resstr.replace(key, str(value))

    return resstr


def _fail_exit(code, msg):
    sys.stderr.write("{0}: {1}\n".format(sys.argv[0], msg))
    sys.exit(code)


def _expression_param(value, argparser):
    if not value:
        return lambda x: True
    if not re.compile('^[=><]?\d+$').match(value):
        argparser.error('invalid expression: {0}'.format(value))

    if value[0] == '>':
        return lambda x: int(x) > int(value.strip('>'))
    elif value[0] == '<':
        return lambda x: int(x) < int(value.strip('<'))
    else:
        return lambda x: int(x) == int(value.strip('='))


def _generate_list_sorters(pattern='l', argparser=None):
    ''' We want to manipulate the list by pruning and sorting.

    Pattern contains a string that defines how the pattern is:
    [^]([bnr]|l\d+):
    ^ set ascending order for the next sorter. Sort order is reset to
      descending for each new sorter.
    b sorts by bitrate.
    l sorts by number of listeners.
    r randomizes list.
    n truncates the list with the number of stations given,
      e.g. n10 for ten stations.

    Examples
    ^b: sort by bitrate ascending
    ln10r: sort by bitrate descending, truncate the list to ten stations,
           randomize order. This is appropriate if you want a random popular
           station, but have a hard time predicting the number of listeners.

    Behaviour with command line parameters '-n 10' is 'ln10' and with
    '-r -n 1' it is 'rn1'.

    Default behaviour is 'l'
    '''
    def _create_sorter(field, descending):
        return lambda list: sorted(list, key=lambda a: int(a[field]),
                                   reverse=descending)

    def _filter_description(fieldname, descending):
        descending_text = 'desc'
        if not descending:
            descending_text = 'asc'
        return '{0} {1}'.format(fieldname, descending_text)

    def _random(list):
        random.shuffle(list)
        return list

    if argparser is None:
        argparser = argparse.ArgumentParser()
    sorters = []
    sorters_description = []
    sort_descending = True

    # I'd rather enumerate or something, but 'n' needs some special attention
    # Not very pretty, though
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == '^':
            sort_descending = False
        elif char == 'b':
            sorters.append(_create_sorter('br', sort_descending))
            sorters_description.append(_filter_description('bitrate',
                                                           sort_descending))
        elif char == 'l':
            sorters.append(_create_sorter('lc', sort_descending))
            sorters_description.append(_filter_description('listeners',
                                                           sort_descending))
        elif char == 'r':
            sorters.append(_random)
            sorters_description.append('random order')
        elif char == 'n':
            number = ''

            while True:
                index += 1
                if index >= len(pattern) or pattern[index] not in '0123456789':
                    break
                number = number + pattern[index]
            index -= 1

            if not number:
                msg_missing_number = 'missing number for sorter n in "{0}"'
                argparser.error(msg_missing_number.format(pattern))
            value = int(number)
            sorters.append(lambda list: list[:value])
            sorters_description.append('top {0}'.format(value))
        else:
            argparser.error('invalid sorter: {0}'.format(char))

        index += 1

    return (sorters, sorters_description)


def main():
    o = argparse.ArgumentParser(description=get_egg_description())
    o.add_argument('keywords', nargs='*', action='store',
                   help='Keywords to search')
    o.add_argument('--list-genres', dest='do_list_genres', action='store_true',
                   default=False, help='list available genres and exit')
    o.add_argument('-n', '--limit', dest='limit', action='store',
                   type=int,
                   default=0, help='maximum number of stations.')
    o.add_argument('-r', '--random', dest='random', action='store_true',
                   default=False,
                   help='sort stations randomly unless --sort is given.')
    o.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                   default=False,
                   help='verbose output, useful for getting search right.')
    fmt = o.add_argument_group('Format',
                               ('Specifies how the found stations should be '
                                'printed. Codes: %u - url, %g - genre, '
                                '%p - current song, %s - station name, '
                                '%b - bitrate, %l - number of listeners, '
                                '%t - MIME / codec, %% - %, \n - newline, '
                                '\t - tab'))
    fmt.add_argument('-f', '--format', dest='format', action='store',
                     default='', help='results formatting.')
    o.add_argument_group(fmt)
    p = o.add_argument_group('Criteria')
    p.add_argument('-g', '--genre', dest='genre', action='append',
                   default=[], help='genre, e.g. \'-g Ambient\'.')
    p.add_argument('-p', '--playing', dest='song', action='append',
                   default=[],
                   help='currently played song / artist, e.g. \'-p Shantel\'.')
    p.add_argument('-s', '--station', dest='station', action='append',
                   default=[],
                   help='station name, e.g. \'-s "Groove Salad"\'.')
    f = o.add_argument_group('Filters',
                             ('Filter the search results. These can NOT be '
                              'used alone, e.g. to search for all stations '
                              'with no listeners. If no criteria or keywords '
                              'are given, the Top500 stations are used.'))
    f.add_argument('-b', '--bitrate', dest='bitrate', action='store',
                   default='',
                   help=('bitrate (kbps), [=><]NNN, e.g. \'-b "=128"\' for '
                         '128kbps.'))
    f.add_argument('-l', '--listeners', dest='listeners', action='store',
                   default='',
                   help=('number of listeners, [=><]NNN, e.g. \'-l ">500"\' '
                         'for more than 500 listeners.'))
    f.add_argument('-t', '--type', dest='codec', action='store',
                   default='', help='"mpeg" for MP3, "aacp" for aacPlus.')
    s = o.add_argument_group('Sorters',
                             ('Manipulate the order of the returned list. '
                              'The list can be sorted by number of listeners '
                              '(l) and bitrate (b), it can be randomized (r) '
                              'and it can be truncated (n), i.e. shortened to '
                              'a specified amount of stations. Sorting is '
                              'performed in written order, for example '
                              '"ln20r" sorts the list by number of '
                              'listeners, trunkates it to twenty stations '
                              'and then randomizes it, giving the top twenty '
                              'random stations matching the search. '
                              '^ is used to set sort order to ascending for '
                              'l and b. The default sort order is reset to '
                              'descending for each new sorter. '
                              'Specifying sorters void the "-r" option.'))
    s.add_argument('--sort', dest='sort_rules', action='store', default='',
                   help=('rules for manipulating the order of the list. '
                         '"l" for number of listeners, "b" for bitrate, '
                         '"r" to randomize order, "n<integer>" to truncate '
                         'list.'))

    args = o.parse_args()

    try:
        if args.do_list_genres:
            genres = get_genres()
            print('\n'.join(genres))
            if genres:
                sys.exit(0)
            else:
                sys.exit(4)

        p_keywords = args.keywords
        p_verbose = args.verbose
        p_random = args.random
        p_genre = args.genre
        p_station = args.station
        p_song = args.song
        p_sort_rules = args.sort_rules
        p_limit = args.limit
        p_bitrate = _expression_param(args.bitrate, o)
        p_listeners = _expression_param(args.listeners, o)

        p_format = '%u'
        if p_verbose:
            p_format = ('%s [%bkbps %t]\\n\\t%u\\n\\t%g, %l listeners\\n\\t'
                        'Now playing: %p\\n')
        if args.format:
            p_format = args.format

        p_mime_type = ''
        if args.codec:
            if args.codec.strip('"') not in ('mpeg', 'aacp'):
                o.error('CODEC must be "mpeg", "aacp" or none')
            p_mime_type = 'audio/' + args.codec.strip('"')

        sorters, sorters_description = _generate_list_sorters(p_sort_rules, o)
        if sorters:
            p_random = False  # Start with sorted list when using sorters

        if p_verbose:   # Print information about query to help debug
            print('Search summary')
            print('-' * 30)
            print(' Keywords: {0}'.format(', '.join(p_keywords)))
            print('   Genres: {0}'.format(', '.join(p_genre)))
            print('  Playing: {0}'.format(', '.join(p_song)))
            print(' Stations: {0}'.format(', '.join(p_station)))
            bitrate_str = args.bitrate or ''
            print('  Bitrate: {0}'.format(bitrate_str))
            listeners_str = args.listeners or ''
            print('Listeners: {0}'.format(listeners_str))
            print('     Type: {0}'.format(args.codec))
            if p_random:
                order_str = 'random'
            elif p_sort_rules:
                order_str = 'by sorters'
            else:
                order_str = 'by no listeners'
            print('    Order: {0}'.format(order_str))
            print('   Sorter: {0}'.format(' | '.join(sorters_description)))
            limit_str = str(p_limit) or ''
            print('    Limit: {0}'.format(limit_str))
            print('   Format: {0}'.format(p_format))
            print('')

        results = search(p_keywords, p_station, p_genre, p_song, p_bitrate,
                         p_listeners, p_mime_type, p_limit, p_random, sorters)

        print('\n'.join(_station_text(el, p_format) for el in results))
        if p_verbose:
            print('\n{0:d} station(s) found.'.format(len(results)))
        if not results:
            _fail_exit(4, 'no station found\n')
    except urllib.error.URLError as e:
        _fail_exit(1, 'network error: {0}'.format(e))
    except Exception as e:
        _fail_exit(3, 'unknown error: {0}'.format(e))


if __name__ == '__main__':
    main()
