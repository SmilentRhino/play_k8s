#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A helper function to get deep value from dictionary
"""

from functools import reduce
def deep_get(dictionary, *keys):
    '''
    Get value from deep nested dict
    '''
    return reduce(lambda d, key: d.get(key, None)
                  if isinstance(d, dict)
                  else None, keys, dictionary)
