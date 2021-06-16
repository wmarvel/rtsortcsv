#!/usr/bin/env python3
"""
rt_sort_csv.py: Sort csv files exported from RT Systems Radio Programmers.

Copyright 2021, Wendall A. Marvel.
Redistributable under the terms of the MIT license, refer to the LICENSE file for
more information.

Per https://www.rtsystemsinc.com/sort-via-export-and-import.html, RT Systems
radio programmers do not support a native sort of the channel list. This
utility reads a csv file exported from the radio programmer and writes a
csv file containing the input channel data sorted by the receive frequency.

The input CSV file is read, treating the first line as a header line. The rest
of the lines are read, sorted, and renumbered, filtering out any lines that
have no data other than the initial row number.

The sorted rows are then written to the output file.

Note that the field comparisons are currently done lexicographically, and
not by converting the field value to a float type. This works for me as
the string values in the frequency fields appear to always be the same
length. However, I only own one RT Systems radio programmer, so your mileage
may vary.

usage: rt_sort_csv.py [-h] [--sortfield SORTFIELD] input output

positional arguments:
  input                 The input .csv file name.
  output                The output .csv file name.

optional arguments:
  -h, --help            show this help message and exit
  --sortfield SORTFIELD
                        The field to use for sorting. Defaults to 1, for
                        receive frequency.

"""

import csv as csv
import sys as sys
import argparse as ap
import functools as ft


# Argument parsing related constants
_ARG_INPUT = 'input'
_ARG_OUTPUT = 'output'
_ARG_SORT_FIELD = '--sortfield'
_HELP_INPUT = 'The input .csv file name.'
_HELP_OUTPUT = 'The output .csv file name.'
_HELP_SORT_FIELD = 'The field to use for sorting. Defaults to 1, for receive frequency.'


@ft.total_ordering
class CSVRecord:
    """A CSVRecord represents a single row in a CSV file.

    A total ordering is implemented so that records can be sorted by fields,
    with the sort field specified by CSVRecord.sortfield
    """
    sortfield = 1

    def __init__(self, fields):
        self._fields = fields

    def __repr__(self):
        return str(self._fields)

    def __eq__(self, other) -> bool:
        return isinstance(other, CSVRecord) and self._fields == other._fields

    def __lt__(self, other) -> bool:
        if isinstance(other, CSVRecord):
            return self._fields[self.sortfield] < other._fields[other.sortfield]
        return False

    def __iter__(self):
        return self._fields.__iter__()

    def has_data(self):
        """Determine if a record has data required in the output."""
        for field in self._fields[1:]:
            if field is not '':
                return True
        return False

    def set_index(self, value):
        """Set the record index (first) field to the given value."""
        self._fields[0] = str(value + 1)


def _create_parser():
    """Create an argument parser configured for parsing expected arguments."""
    parser = ap.ArgumentParser(sys.argv[0])
    parser.add_argument(_ARG_INPUT, help=_HELP_INPUT)
    parser.add_argument(_ARG_OUTPUT, help=_HELP_OUTPUT)
    parser.add_argument(_ARG_SORT_FIELD, type=int,
                        default=1, help=_HELP_SORT_FIELD)
    return parser


def _parse_args():
    """Parse the command line arguments

    Parses the command line arguments. If the argument parser can determine
    that arguments are missing or incorrect, a usage message will be printed
    and the program will exit. Otherwise a Namespace containing the parsed
    arguments is returned.
    """
    parser = _create_parser()
    return parser.parse_args()


def _process_input(filename, field):
    """Read, filter, and sort the input file specified by the arguments."""
    print(f'Reading data from {filename}')
    CSVRecord.sortfield = field
    with open(filename, newline='') as infile:
        csv_reader = csv.reader(infile)
        csv_rows = list(csv_reader)
        header = CSVRecord(csv_rows[0])
        rows = sorted(filter(lambda r: r.has_data(), map(CSVRecord, csv_rows[1:])))
        return header, rows


def _write_output(filename, header, rows):
    """Write the header and rows to the output file.

    The rows will be renumbered as they are written.
    """
    with open(filename, 'w', newline='') as outfile:
        csv_writer = csv.writer(outfile)
        csv_writer.writerow(header)
        for index, row in enumerate(rows):
            row.set_index(index)
            csv_writer.writerow(row)
    print(f'Wrote data to {filename}')


if __name__ == "__main__":
    _args = _parse_args()
    _header, _rows = _process_input(_args.input, _args.sortfield)
    _write_output(_args.output, _header, _rows)
