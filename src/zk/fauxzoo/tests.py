import doctest
import unittest

def sample_test():
    """
    >>> 1
    1
    """

def test_suite():
    return unittest.TestSuite((
        doctest.DocTestSuite(),
        doctest.DocFileSuite('README.test'),
        ))

