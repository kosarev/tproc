# -*- coding: utf-8 -*-

import os
import tproc
import unittest


class CommonTest(unittest.TestCase):
    def collect_output(self, output):
        res = []
        for chunk in output:
            if isinstance(chunk, str) and res and isinstance(res[-1], str):
                res[-1] += chunk
                continue

            res.append(chunk)

        return res


    def compare_outputs(self, a, b):
        a = self.collect_output(a)
        b = self.collect_output(b)
        assert a == b, (a, b)

    def process(self, filename):
        p = tproc.Processor()
        p.process_file(filename)
        self.compare_outputs(p.expand_field('main'),
                             p.expand_field('expected'))

    def runTest(self):
        test_dir = os.path.dirname(__file__)
        for filename in os.listdir(test_dir):
            if filename.endswith('.tproc'):
                self.process(os.path.join(test_dir, filename))


if __name__ == '__main__':
    unittest.main()
