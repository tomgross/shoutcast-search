import sys
from unittest import TestCase

from shoutcast_search.shoutcast_search import _build_search_url
from shoutcast_search.shoutcast_search import _expression_param


class DummyParser(object):

    def error(self, message):
        sys.exit(2)


class UtilityTestCase(TestCase):

    def test_build_search_url(self):
        self.assertEqual(_build_search_url({'foo': 'bar'}),
                         'http://yp.shoutcast.com/sbin/newxml.phtml?foo=bar')

    def test_expression_param_noval(self):
        self.assertTrue(_expression_param(None, None)(None))

    def test_expression_param_invalid(self):
        argparser = DummyParser()
        self.assertRaises(SystemExit, _expression_param, '%50', argparser)

    def test_expression_param_equals(self):
        self.assertTrue(_expression_param('=50', None)(50))
        self.assertFalse(_expression_param('=50', None)(42))

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
