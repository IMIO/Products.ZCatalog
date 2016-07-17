##############################################################################
#
# Copyright (c) 2011 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

import unittest

from Products.PluginIndexes.UUIDIndex.UUIDIndex import UUIDIndex


class Dummy:

    def __init__(self, foo):
        self._foo = foo

    def foo(self):
        return self._foo

    def __str__(self):
        return '<Dummy: %s>' % self._foo

    __repr__ = __str__


class UUIDIndexTests(unittest.TestCase):

    def setUp(self):
        self._index = UUIDIndex('foo')
        self._marker = []
        self._values = [
            (0, Dummy('a')),
            (1, Dummy('ab')),
            (2, Dummy(123)),
            (3, Dummy(234)),
            (4, Dummy(0))]
        self._forward = {}
        self._backward = {}
        for k, v in self._values:
            self._backward[k] = v
            keys = self._forward.get(v, [])
            self._forward[v] = keys

    def tearDown(self):
        self._index.clear()

    def _populateIndex(self):
        for k, v in self._values:
            self._index.index_object(k, v)

    def _checkApply(self, req, expectedValues):
        result, used = self._index._apply_index(req)
        if hasattr(result, 'keys'):
            result = result.keys()
        self.assertEqual(used, ('foo', ))
        self.assertEqual(len(result), len(expectedValues))
        for k, v in expectedValues:
            self.assertTrue(k in result)

    def test_interfaces(self):
        from Products.PluginIndexes.interfaces import IPluggableIndex
        from Products.PluginIndexes.interfaces import ISortIndex
        from Products.PluginIndexes.interfaces import IUniqueValueIndex
        from zope.interface.verify import verifyClass

        verifyClass(IPluggableIndex, UUIDIndex)
        verifyClass(ISortIndex, UUIDIndex)
        verifyClass(IUniqueValueIndex, UUIDIndex)

    def test_empty(self):
        self.assertEqual(len(self._index), 0)
        self.assertEqual(len(self._index.referencedObjects()), 0)
        self.assertEqual(self._index.numObjects(), 0)
        self._checkApply({'foo': 'a'}, [])

    def test_populated(self):
        self._populateIndex()
        values = self._values
        self.assertEqual(len(self._index), len(values))
        self.assertEqual(self._index.indexSize(), len(values))
        self.assertTrue(self._index.getEntryForObject(10) is None)
        self._checkApply({'foo': 'not'}, [])

        self._index.unindex_object(10) # nothrow

        for k, v in values:
            self.assertEqual(self._index.getEntryForObject(k), v.foo())

        self._checkApply({'foo': 'a'}, [values[0]])
        self._checkApply({'foo': 0}, [values[4]])
        self._checkApply({'foo': ['a', 'ab']}, values[:2])

    def test_none(self):
        # Make sure None is ignored.
        self._index.index_object(10, Dummy(None))
        self.assertFalse(None in self._index.uniqueValues('foo'))
        self._checkApply({'foo': None}, [])

    def test_reindex(self):
        self._populateIndex()
        self._checkApply({'foo': 'a'}, [self._values[0]])
        d = Dummy('world')
        self._index.index_object(0, d)
        self._checkApply({'foo': 'a'}, [])
        self._checkApply({'foo': 'world'}, [(0, d)])
        self.assertEqual(self._index.keyForDocument(0), 'world')
        del d._foo
        self._index.index_object(0, d)
        self._checkApply({'foo': 'world'}, [])
        self.assertRaises(KeyError, self._index.keyForDocument, 0)

    def test_range(self):
        values = []
        for i in range(100):
            obj = (i, Dummy(i))
            self._index.index_object(*obj)
            values.append(obj)

        query = {'foo': {'query': [10, 20], 'range': 'min:max'}}
        self._checkApply(query, values[10:21])

    def test_non_unique(self):
        obj = Dummy('a')
        self._index.index_object(0, obj)
        # second index call fails and logs
        self._index.index_object(1, obj)
        self._checkApply({'foo': 'a'}, [(0, obj)])
