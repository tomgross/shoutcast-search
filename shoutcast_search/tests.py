# -*- coding: utf-8 -*-
import io
import sys
from os.path import dirname, join
from unittest import TestCase

from shoutcast_search.shoutcast_search import Provider
from shoutcast_search.shoutcast_search import _expression_param
from shoutcast_search.shoutcast_search import _from_UTF_8
from shoutcast_search.shoutcast_search import _fail_exit
from shoutcast_search.shoutcast_search import get_egg_description
from shoutcast_search.shoutcast_search import _generate_list_sorters
from shoutcast_search.shoutcast_search import main
from shoutcast_search.shoutcast_search import search
from shoutcast_search.shoutcast_search import filter_results


class DummyParser(object):

    def error(self, message):
        sys.exit(2)


class TestProvider(Provider):

    search_url = 'file://' + join(dirname(__file__), 'test_data', 'search.xml')
    by_id_url = 'file://' + join(dirname(__file__), 'test_data', 'byid.xml')
    genres_url = 'file://' + join(dirname(__file__), 'test_data', 'genres.xml')

    extra_headers = {'a': 'b'}


def redirect_stdout():
    sys.stderr = stdout = io.StringIO()
    return stdout


def reset_stdout(stdout):
    sys.stdout = sys.__stdout__
    return stdout.getvalue()


class UtilityTestCase(TestCase):

    def test_get_egg_description(self):
        self.assertIn('shoutcast', get_egg_description().lower())

    def test_fail_exit(self):
        stdout = redirect_stdout()
        self.assertRaises(SystemExit, _fail_exit, 3, 'exited with code 3')
        self.assertIn('code 3', reset_stdout(stdout))

    def test_expression_param_noval(self):
        self.assertTrue(_expression_param(None, None)(None))

    def test_expression_param_invalid(self):
        argparser = DummyParser()
        self.assertRaises(SystemExit, _expression_param, '%50', argparser)

    def test_expression_param_equals(self):
        self.assertTrue(_expression_param('=50', None)(50))
        self.assertFalse(_expression_param('=50', None)(42))

    def test_expression_param_greater(self):
        self.assertTrue(_expression_param('>50', None)(51))
        self.assertFalse(_expression_param('>50', None)(50))
        self.assertFalse(_expression_param('>50', None)(49))

    def test_expression_param_lesser(self):
        self.assertTrue(_expression_param('<50', None)(49))
        self.assertFalse(_expression_param('<50', None)(50))
        self.assertFalse(_expression_param('<50', None)(51))

    def test_from_UTF_8(self):
        self.assertEqual(_from_UTF_8(b'\xc3\xb6l'), 'öl')

    def test_generate_list_sorters_l(self):
        sorters, sorters_description = _generate_list_sorters()
        self.assertEqual(sorters[0]([{'lc': '1'}, {'lc': '2'}]),
                         [{'lc': '2'}, {'lc': '1'}])
        self.assertEqual(sorters_description, ['listeners desc'])

    def test_generate_list_sorters_r(self):
        sorters, sorters_description = _generate_list_sorters('r')
        self.assertEqual(len(sorters[0]([{'lc': '1'}, {'lc': '2'}])), 2)
        self.assertEqual(sorters_description, ['random order'])

    def test_generate_list_sorters_b(self):
        sorters, sorters_description = _generate_list_sorters('b')
        self.assertEqual(sorters[0]([{'br': '1'}, {'br': '2'}]),
                         [{'br': '2'}, {'br': '1'}])
        self.assertEqual(sorters_description, ['bitrate desc'])

    def test_generate_list_sorters_n(self):
        sorters, sorters_description = _generate_list_sorters('n1')
        self.assertEqual(sorters[0]([{'br': '1'}, {'br': '2'}]),
                         [{'br': '1'}])
        self.assertEqual(sorters_description, ['top 1'])

    def test_generate_list_sorters_asc_b(self):
        sorters, sorters_description = _generate_list_sorters('^b')
        self.assertEqual(sorters[0]([{'br': '2'}, {'br': '1'}]),
                         [{'br': '1'}, {'br': '2'}])
        self.assertEqual(sorters_description, ['bitrate asc'])

    def test_generate_list_sorters_invalid_sorter(self):
        stdout = redirect_stdout()
        self.assertRaises(SystemExit, _generate_list_sorters, 'x')
        self.assertIn('error: invalid sorter: x', reset_stdout(stdout))

    def test_generate_list_sorters_invalid_number(self):
        stdout = redirect_stdout()
        self.assertRaises(SystemExit, _generate_list_sorters, 'n')
        self.assertIn('error: missing number', reset_stdout(stdout))

    def test_generate_list_sorters_combination(self):
        sorters, sorters_description = _generate_list_sorters('^bn2')
        stations = [{'br': '2'}, {'br': '1'}, {'br': '3'}]
        for sorter in sorters:
            stations = sorter(stations)
        self.assertEqual(stations, [{'br': '1'}, {'br': '2'}])
        self.assertEqual(sorters_description, ['bitrate asc', 'top 2'])

    def test_search_mt(self):
        provider = TestProvider()
        provider.get_search_results = lambda opt_dict: opt_dict
        self.assertEqual(search(mime_type='ogg', provider=provider),
                         {'mt': 'ogg', 'genre': 'Top500'})

    def test_search_nokeyword(self):
        provider = TestProvider()
        provider.get_search_results = lambda opt_dict: opt_dict
        self.assertEqual(search(mime_type='mp3', provider=provider),
                         {'mt': 'mp3', 'genre': 'Top500'})

    dummy_result = [{'br': 128, 'lc':10, 'name':'TestStation1',
                     'genre': 'Dub', 'ct':'foo'},
                    {'br': 256, 'lc':15, 'name':'TestStation2',
                     'genre': 'Country', 'ct':'bar'},
                    {'br': 64, 'lc':35, 'name':'TestStation3',
                     'genre': 'Classic', 'ct':'foobar'},
                     ]

    def test_filter_station(self):
        result =filter_results(self.dummy_result, station=['TestStation1'])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'TestStation1')

    def test_filter_genre(self):
        result =filter_results(self.dummy_result, genre=['Classic'])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'TestStation3')

    def test_filter_song(self):
        result =filter_results(self.dummy_result, song=['bar'])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'TestStation3')

    def test_filter_limit(self):
        result =filter_results(self.dummy_result, limit=2)
        self.assertEqual(len(result), 2)

    def test_filter_sorters(self):
        sorter = lambda list: sorted(list, key=lambda a: int(a['br']))
        result =filter_results(self.dummy_result, sorters=[sorter])
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['name'], 'TestStation3')

    def test_filter_randomize(self):
        result =filter_results(self.dummy_result, randomize=True)
        self.assertEqual(len(result), 3)

class ProviderTestCase(TestCase):

    def _make_one(self):
        return TestProvider()

    def test_build_search_url(self):
        provider = self._make_one()
        provider.search_url = 'http://yp.shoutcast.com/sbin/newxml.phtml?{0}'
        self.assertEqual(provider._build_search_url({'foo': 'bar'}),
                         'http://yp.shoutcast.com/sbin/newxml.phtml?foo=bar')

    def test_get_genres(self):
        provider = self._make_one()
        self.assertIn('Acid Jazz', provider.get_genres())
        self.assertEqual(len(provider.get_genres()), 19)


class MainTestCase(TestCase):

    def test_main(self):
        provider = TestProvider()
        main(provider)

    def test_main_verbose(self):
        sys.argv = ['shoutcast-search', '-v', 'test']
        provider = TestProvider()
        main(provider)

    def test_main_genres(self):
        sys.argv = ['shoutcast-search', '--list-genres']
        provider = TestProvider()
        main(provider)
