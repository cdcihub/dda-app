import dataanalysis as da
import json

class DDATest(da.DataAnalysis):
    cached=True

    def main(self):
        self.output_data = {'test_value': 1}

        fn = "data_file.json"
        json.dump({"test_value_in_file": 2}, open(fn, "w"))

        self.output_file = da.DataFile(fn)
