"""Create SQL parser
"""
from pyparsing import OneOrMore
from pyparsing import ParseException
from pyparsing import ZeroOrMore

from .utils import _all
from .utils import _create
from .utils import _db_name
from .utils import _distkey
from .utils import _diststyle
from .utils import _encode
from .utils import _even
from .utils import _foreign_key
from .utils import _key
from .utils import _not_null
from .utils import _null
from .utils import _references
from .utils import _sortkey
from .utils import _table
from .utils import column_types
from .utils import def_field
from .utils import pk_check

from .helpers import existance_check
from .helpers import exists
from .helpers import paranthesis_list
from .helpers import temporary_check
from .helpers import to_dict


FK_REFERENCE = 'fk_reference'


def fk_reference():
    """Get Parser for foreign key references
    """
    fk_reference_columns = paranthesis_list(FK_REFERENCE)
    fk_table = _db_name.setResultsName('fk_table')
    return _references + fk_table + fk_reference_columns


def get_base_parser():
    """Get a pyparsing parser for a create table statement

    Returns:
        table_definition(pyparsing): Parser for create table statements
    """

    temp_check = temporary_check.setResultsName('temporary')
    exists_check = existance_check.setResultsName('exists_checks')

    table_name = _db_name.setResultsName('full_name')

    # Initial portions of the table definition
    def_start = _create + temp_check + _table + table_name + exists_check

    table_def = def_start + paranthesis_list('raw_fields', def_field) + \
                get_attributes_parser()

    return table_def


def get_column_parser():
    """Get a pyparsing parser for a create table column field statement

    Returns:
        column_definition(pyparsing): Parser for column definitions
    """
    column_name = _db_name.setResultsName('column_name')
    column_type = column_types.setResultsName('column_type')

    constraints = exists(_not_null, 'is_not_null')
    constraints |= exists(_null, 'is_null')
    constraints |= exists(pk_check, 'is_primarykey')
    constraints |= exists(_distkey, 'is_distkey')
    constraints |= exists(_sortkey, 'is_sortkey')
    constraints |= fk_reference()
    constraints |= _encode + _db_name.setResultsName('encoding')

    column_def = column_name + column_type + ZeroOrMore(constraints)
    return column_def


def get_constraints_parser():
    """Get a pyparsing parser for a create table constraints field statement

    Returns:
        constraints_definition(pyparsing): Parser for constraints definitions
    """
    # Primary Key Constraints
    def_pk = pk_check + paranthesis_list('pk_columns')

    # Foreign Key Constraints
    def_fk = _foreign_key + paranthesis_list('fk_columns') + fk_reference()

    return def_pk | def_fk


def get_attributes_parser():
    """Get a pyparsing parser for a create table attributes

    Returns:
        attribute_parser(pyparsing): Parser for attribute definitions
    """
    diststyle_def = _diststyle + (_all | _even | _key).setResultsName(
        'diststyle')

    distkey_def = _distkey + paranthesis_list('distkey')
    sortkey_def = _sortkey + paranthesis_list('sortkey')

    return ZeroOrMore(diststyle_def | sortkey_def | distkey_def)


def parse_create_table(string):
    """Parse the create table sql query and return metadata

    Args:
        string(sql): SQL string from a SQL Statement

    Returns:
        table_data(dict): table_data dictionary for instantiating a table object
    """
    # Parse the base table definitions
    table_data = to_dict(get_base_parser().parseString(string))

    # Parse the columns and append to the list
    table_data['columns'] = list()
    table_data['constraints'] = list()

    column_position = 0
    for field in table_data['raw_fields']:
        try:
            column = to_dict(get_column_parser().parseString(field))

            # Add position of the column
            column['position'] = column_position
            column_position += 1

            # Change fk_reference_column to string from list
            if FK_REFERENCE in column:
                column[FK_REFERENCE] = column[FK_REFERENCE][0]

            table_data['columns'].append(column)

        except ParseException:
            try:
                constraint = to_dict(
                    get_constraints_parser().parseString(field))
                table_data['constraints'].append(constraint)
            except ParseException:
                print '[Error] : ', field
                raise

    return table_data
