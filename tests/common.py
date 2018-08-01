# -*- coding: utf-8 -*-

import unittest


class CommonTest(unittest.TestCase):
    def runTest(self):
        import tproc
        tproc.main()


if __name__ == '__main__':
    unittest.main()
