import json
from collections import abc

from typing import Callable


def one_dimension_dic(muldd, prt_key:str='', sep:str='.'):
    array = []
    for k, v in muldd.items():
        k = str(k)
        new_key = prt_key + sep + k if prt_key else k
        if isinstance(v, dict):
            array.extend(one_dimension_dic(v, new_key, sep=sep).items())
        else:
            array.append((new_key, v))
    return dict(array)

def get_plain(muldd):
    result = [{key: value} for key, value in one_dimension_dic(muldd).items()]
    return result


class JSON(dict):
    TYPE_DICT = {
        'integer': int,
        'number': float,
        'object': dict,
        'array': list,
        'boolean': bool,
        'string': str,
        'null': None
    }
    VALID = True
    def __init__(self, some_dict: dict):
        super ().__init__ ()
        self.update(some_dict)

    def __missing__(self, key):
        if isinstance(key, tuple):
            res = self[key[0]]
            for num in range (1, len (key)):
                if not res:
                    return None
                if (res is None) or ((num != (len(key))) and (not isinstance(res, dict))):
                    return None
                if res.__contains__(key[num]):
                    res = res.__getitem__(key[num])
                else:
                    return None
            return res
        return None

    def new_dic(self, key, val):
        mew_dic = {}
        mew_dic[key] = val
        return mew_dic

    def plain(self):
        res = [{key: value} for key, value in one_dimension_dic (self).items ()]
        return res

    def init_validate_func(self, warning_callback, error_callback):
        self.VALID = True
        self.warnings = warning_callback
        self.error = error_callback
    @staticmethod
    def validate_type(type_:type, data, enum=None):
        # type - required type
        if enum:
            if data in enum:
                return data, None
            else:
                return False, f'Value must be from {enum}'
        if isinstance(data, type_): # if type of data matches the required type
            return data, None
        else:
            if (data in [1, 0]) and (isinstance(type_, bool)):
                return bool(data), f'Value must be {type_}, not {type(data)}'
            else:
                try:
                    val = type_(data)
                    return val, f'Value must be {type_}, not {type(data)}'
                except ValueError:
                    return False, f'Unsupported format {type(data)} it must be {type_}'
                except TypeError:
                    return False, f'Unsupported format {type(data)} it must be {type_}'

    def validate(self, schema:dict, data='init_None', error_callback: Callable = None, warning_callback: Callable=None):
        # VALID - schema status. If False - dict is invalid (one and more errors)
        """schema must be the type of dict"""
        if data == 'init_None':
            data = self
            self.init_validate_func(warning_callback, error_callback) # init callbacks functions

        match schema:
            case {'type': 'object', 'required': required}:

                # testing if all req in here cuz properties tested in the lover levels
                if not isinstance(data, dict):
                    self.VALID = False
                    return f'must be the type of dict not {type(data)}'
                for req in required:
                    if req not in data:
                        dflt = schema[req].get('default') if schema.get(req) else None # check if default value are present
                        dflt = schema.get('properties')[req].get('default') if (dflt is None) and (schema.get('properties')) else dflt
                        if dflt is not None:
                            data[req] = dflt
                            self.warnings(f'WARNING! key "{req}" is required, set to default - "{dflt}"') if self.warnings else ''
                        else:
                            self.error(f'ERROR! key "{req}" is required.') if self.error else ''
                            self.VALID = False
                val = schema.get('properties')
                schema = val if val else schema

            case {'type': 'object', 'properties': properties}:
                val = schema.get ('properties')
                schema = val if val else schema

            case {'type': 'array', 'items': {'type':type_}} if type_ in ('integer', 'boolean', 'string', 'number'): # check if all values in array are matched the given type
                type_ = self.TYPE_DICT[type_]
                if not isinstance(data, abc.Sequence):
                    self.VALID = False
                    return 'must be iterable'
                if not all(isinstance(i, type_) for i in data): # check all data in the array
                    try:
                        data = [type_(dat) for dat in data]
                        self.warnings(f'WARNING! Value "{data}" in the array must be {str(type_)}') if self.warnings else ''

                    except ValueError:
                        self.VALID = False
                        return f'must be the  type of  {type_}'

        for key, value in schema.items():
            match value:
                case {'type': end_type} if end_type in ('integer', 'boolean', 'string', 'number'): # end of the array or dict no more recursion is needed

                    if key in data: # testing format
                        enum = value.get('enum')
                        val, warning = self.validate_type(self.TYPE_DICT[end_type], data[key], enum)
                        if val is not False:
                            self.warnings(f'WARNING! key - "{key}". {warning}') if warning and self.warnings else ''
                            data[key] = val
                        else:
                            self.error(f'ERROR! key - "{key}" {warning}') if warning and self.error else ''
                            self.VALID = False if warning else self.VALID


                case {'type': 'array', 'items': items}:
                    if key not in data:
                        self.warnings(f'WARNING! Missing key - "{key}"') if self.warnings else ''
                    elif not isinstance(data[key], abc.Sequence):
                        self.error (f'ERROR! Key- "{key}". Items must be iterable.') if self.warnings else ''
                        self.VALID = False
                    else:
                        for i in data[key]:
                            warning = self.validate(items, i)
                            self.error(f'ERROR! Items in the array "{key}" {warning}') if (isinstance(warning, str) and self.error) else ''

                case {'properties': prop}: # properties in object check it
                    if key not in data and value.get('default') is None:
                        self.warnings(f'WARNING! Missing key "{key}"') if self.warnings else ''
                    elif not isinstance(data[key], dict):
                        self.error(f'ERROR! key "{key}" must be the type of dict') # occurs if instead of the dict another type are given
                    else:
                        self.validate(value, data[key])

                case {'type': 'object'}:
                    if key in data:
                        if not isinstance (data[key], dict):
                            self.error(f'ERROR! Unsupported type for the key "{key}" it must be dict') if self.error else ''
                            self.VALID = False
                    else:
                        deflt = value.get('default')
                        if deflt:
                            data[key] = deflt

        return self.VALID

    def __setitem__(self, key, value):
        if '.' in key:
            item = tuple (reversed([i for i in key.split ('.')]))
            new_dic = {}
            new_dic[item[0]] = value
            for i in item[1:-1]:
                new_dic = self.new_dic(i, new_dic)
            super (JSON, self).__setitem__ (item[-1], new_dic)
        elif isinstance (key, list|tuple):
            item = tuple (reversed([i for i in key]))
            new_dic = {}
            new_dic[item[0]] = value
            for i in item[1:-1]:
                new_dic = self.new_dic (i, new_dic)
            super (JSON, self).__setitem__ (item[-1], new_dic)

        else:
            super(JSON, self).__setitem__(key, value)

    def __getitem__(self, item):
        if '.' in item:
            item = tuple(i for i in item.split('.'))
        if isinstance(item, list):
            item = tuple(i for i in item)
        return super(JSON, self).__getitem__(item)





