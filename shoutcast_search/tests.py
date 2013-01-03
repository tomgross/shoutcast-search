from unittest import TestCase

from shoutcast_search.shoutcast_search import _build_search_url

class UtilityTestCase(TestCase):

    def test_build_search_url(self):
        self.assertEqual(
                _build_search_url({'foo': 'bar'}),
                'http://yp.shoutcast.com/sbin/newxml.phtml?foo=bar')

