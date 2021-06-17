#!/usr/bin/env python3
"""
rt_sort_csv.py: Sort csv files exported from RT Systems Radio Programmers.

Copyright 2021, Wendall A. Marvel.
Redistributable under the terms of the MIT license, refer to the LICENSE file for
more information.

The RT Systems programmer I have does not appear to be able to sort the channel
list into a particular order while using the programmer.

Per https://www.rtsystemsinc.com/sort-via-export-and-import.html, RT Systems
recommends exporting to CSV, ordering how you like, and then importing,
instead of supporting being able to sort the channel list by fields in the
programmer.
This utility reads a csv file exported from the radio programmer and writes a
csv file containing the input channel data sorted by the receive frequency.

The input CSV file is read, treating the first line as a header line. The rest
of the lines are read, sorted, and renumbered, filtering out any lines that
have no data other than the initial row number.

The sorted rows are then written to the output file.

If no sort and channel name field indexes are specified via the command line,
the indexes to use will be determined from the header line. Depending on the
header line content, it is possible to fail while attempting to determine the
indexes.

Note that the rows are currently sorted using lexicographic comparisons.
The compared strings are created using padding to ensure that various
fields in the sort all compare correctly, and the frequencies in the file
exported by my RT Systems programmer all have the same length, making a
lexicographic comparison equivalent to a numeric comparison. Your mileage
may vary, as I have no idea if *every* RT Systems radio programmer exports
csv with the frequencies padded to the same length.

usage: rt_sort_csv.py [-h]
                      [--sortfield SORTFIELD]
                      [--namefield NAMEFIELD]
                      input output

positional arguments:
  input                 The input .csv file name.
  output                The output .csv file name.

optional arguments:
  -h, --help            show this help message and exit
  --sortfield SORTFIELD
                        The field index to use for sorting.
  --namefield NAMEFIELD
                        The field index to use for the channel name.
"""

import csv as csv
import sys as sys
import argparse as ap
import functools as ft


# Argument parsing related constants
_ARG_INPUT = 'input'
_ARG_OUTPUT = 'output'
_ARG_SORT_FIELD = '--sortfield'
_ARG_NAME_FIELD = '--namefield'
_HELP_INPUT = 'The input .csv file name.'
_HELP_OUTPUT = 'The output .csv file name.'
_HELP_SORT_FIELD = 'The field index to use for sorting.'
_HELP_NAME_FIELD = 'The field index to use for the channel name.'

# List of header fields for detection of sort and name fields.
# This is done this way so it will be easy to support other programmers if
# they have fields in different columns and/or with different column names
# in the header, by adding appropriate values to the following two lists.
_SORT_FIELDS = ['Receive Frequency']
_NAME_FIELDS = ['Name']

# List of specially-handled radio services that use channels.
# I own a couple of FRS radios and want to be able to listen to those
# frequencies on my amateur radio HT.
# Channels named 'FRS/GMRS X', where X is a number, will go to the end of the
# list, ordered by the channel number X
# This is written to be able to extend to other radio services just by adding on
# to this list, in which case the channels for a given service would end up
# together, with the blocks for the services in alphabetical order.
_CHANNEL_SERVICES = ['FRS/GMRS']


@ft.total_ordering
class CSVRecord:
    """A CSVRecord represents a single row in a CSV file.

    A total ordering is implemented so that records can be sorted by fields,
    with the sort field specified by CSVRecord.sortfield
    """
    sort_field = 1
    name_field = 7

    def __init__(self, fields):
        self._fields = fields
        name_words = self._fields[self.name_field].split(' ')
        if len(name_words) > 1 and name_words[0] in _CHANNEL_SERVICES:
            self._service_name = name_words[0]
            self._service_channel = int(name_words[1])
        else:
            self._service_name = ''
            self._service_channel = 0

    def __repr__(self):
        return str(self._fields)

    def __eq__(self, other) -> bool:
        return isinstance(other, CSVRecord)\
               and self._service_name == other._service_name\
               and self._service_channel == other._service_channel\
               and self._fields == other._fields

    def __lt__(self, other) -> bool:
        if isinstance(other, CSVRecord):
            return self._lexicographic_value() < other._lexicographic_value()
        return False

    def __iter__(self):
        return self._fields.__iter__()

    def _lexicographic_value(self):
        """Convert to a string appropriate for a lexicographic comparison."""
        name = self._service_name
        channel = self._service_channel
        field = self._fields[self.sort_field]
        return f'{name:16}{channel:02}{field:9}'

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
                        default=-1, help=_HELP_SORT_FIELD)
    parser.add_argument(_ARG_NAME_FIELD, type=int,
                        default=-1, help=_HELP_NAME_FIELD)
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


def _field_index(header, field_names, index):
    """Determine a field index.

    If the index passed is already a valid index, that index is returned.
    Otherwise, the header is searched for a field name matching any of
    the passed field names, and the index of the first one found is
    returned.

    If no matching field can be found, a ValueError is raised.
    """
    if index > -1:
        return index
    for index, value in enumerate(header):
        if value in field_names:
            print(f'Detected field \'{value}\' at index {index}')
            return index
    expected_names = ', '.join(field_names)
    raise ValueError(f'No header field is named any of {expected_names}')


def _process_input(filename, sort_field, name_field):
    """Read, filter, and sort the input file specified by the arguments."""
    print(f'Reading data from {filename}')
    with open(filename, newline='') as infile:
        csv_reader = csv.reader(infile)
        csv_rows = list(csv_reader)
        header = CSVRecord(csv_rows[0])
        CSVRecord.sort_field = _field_index(header, _SORT_FIELDS, sort_field)
        CSVRecord.name_field = _field_index(header, _NAME_FIELDS, name_field)
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
    _header, _rows = _process_input(_args.input, _args.sortfield, _args.namefield)
    _write_output(_args.output, _header, _rows)
