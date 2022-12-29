"""
This module will be designated to do the calculations about the processing statistics
and forward to its sibling 'present.py' that will, as the name implies, present
the statistics in the console.
"""

import pandas as pd
from settings.settings import LOG_DIR


class StatsCalc(object):
    def __init__(self):
        self.df = pd.read_csv(LOG_DIR + "/stats.csv")

    def __str__(self):
        return self.df.to_string()

    def calc_ratio(self):
        print(self.df.groupby("vendor_id"))


if __name__ == "__main__":
    stats = StatsCalc()
    print(stats.calc_ratio())
