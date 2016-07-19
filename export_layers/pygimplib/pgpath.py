#
# This file is part of pygimplib.
#
# Copyright (C) 2014, 2015 khalim19 <khalim19@gmail.com>
#
# pygimplib is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pygimplib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pygimplib.  If not, see <http://www.gnu.org/licenses/>.
#

"""
This module contains functions dealing with strings, filenames, files and
directories.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import abc
import inspect
import os
import re
import types

#===============================================================================


def uniquify_string(str_, existing_strings, uniquifier_position=None,
                    uniquifier_generator=None):
  """
  If string `str_` is in the `existing_strings` list, return a unique string
  by inserting a "uniquifier" (a string that makes the whole input string
  unique) in `str_`. Otherwise, return `str_`.
  
  Parameters:
  
  * `str_` - String to uniquify.
  
  * `existing_strings` - List of strings to compare against `str_`.
  
  * `uniquifier_position` - See `uniquify_string_generic.uniquifier_position`.
  
  * `uniquifier_generator` - See `uniquify_string_generic.uniquifier_generator`.
  """
  
  return uniquify_string_generic(str_,
                                 lambda str_param: str_param not in existing_strings,
                                 uniquifier_position, uniquifier_generator)
  

def uniquify_filename(filename, uniquifier_position=None, uniquifier_generator=None):
  """
  If a file with the specified filename already exists, return a unique filename.
  
  Parameters:
  
  * `filename` - Filename to uniquify.
  
  * `uniquifier_position` - See `uniquify_string_generic.uniquifier_position`.
  
  * `uniquifier_generator` - See `uniquify_string_generic.uniquifier_generator`.
  """
  
  return uniquify_string_generic(filename,
                                 lambda filename_param: not os.path.exists(filename_param),
                                 uniquifier_position, uniquifier_generator)

def uniquify_string_generic(str_, is_unique_func, uniquifier_position=None,
                            uniquifier_generator=None):
  """
  If string `str_` is not unique according to `is_unique_func`, return a unique
  string by inserting a "uniquifier" (a string that makes the whole input string
  unique) in `str_`. Otherwise, return `str_`.
  
  Parameters:
  
  * `str_` - String to uniquify.
  
  * `is_unique_func` - Function that returns True if `str_` is unique, False
    otherwise. `is_unique_func` must contain `str_` as its only parameter.
  
  * `uniquifier_position` - Position (index) where the uniquifier is inserted.
    If the position is None, insert the uniquifier at the end of `str_` (i.e.
    append it).
  
  * `uniquifier_generator` - A generator object that generates a unique string
    (uniquifier) in each iteration. If None, the generator yields default
    strings - " (1)", " (2)", etc.
    
    An example of a custom uniquifier generator:

      def _generate_unique_copy_string():
        uniquifier = " - copy"
        yield uniquifier
        
        uniquifier = " - another copy"
        yield uniquifier
         
        i = 2
        while True:
          yield "{0} {1}".format(uniquifier, i)
          i += 1
    
    This generator yields " - copy", " - another copy", " - another copy 2",
    etc.
  """
  
  def _get_uniquified_string(uniquifier_generator):
    return "{0}{1}{2}".format(str_[0:uniquifier_position],
                              next(uniquifier_generator),
                              str_[uniquifier_position:])

  def _generate_unique_number():
    i = 1
    while True:
      yield " ({0})".format(i)
      i += 1
  
  if is_unique_func(str_):
    return str_
  
  if uniquifier_position is None:
    uniquifier_position = len(str_)
  
  if uniquifier_generator is None:
    uniquifier_generator = _generate_unique_number()
  
  uniq_str = _get_uniquified_string(uniquifier_generator)
  while not is_unique_func(uniq_str):
    uniq_str = _get_uniquified_string(uniquifier_generator)
  
  return uniq_str


#===============================================================================


class StringPatternGenerator(object):
  
  """
  This class generates strings by a given pattern and optionally fields acting
  as variables in the pattern.
  
  To generate a string, create a new instance of `StringPatternGenerator` with
  the desired pattern and fields and then call `generate()`.
  
  `fields` is a dictionary of <field name>: <function> pairs inserted into the
  pattern. Fields in the pattern are enclosed in square brackets ("[field]").
  To insert literal square brackets, double the character ("[[", "]]").
  
  Field arguments (the number depends on the function in the `fields`
  dictionary) are separated by commas (","). To insert literal commas in field
  arguments, enclose the arguments in square brackets. To insert square brackets
  in field arguments, enclose the arguments in square brackets and double the
  square brackets (the ones inside the argument, not the enclosing ones). If the
  last argument is enclosed in square brackets, insert a comma after the
  argument.
  
  If no field is specified or if a number is explicitly specified at the
  beginning or the end of the pattern, an auto-incrementing number is assigned
  to each generated string.
  
  Examples:
  
  * "image" -> "image001", "image002", ...
  * "image1" -> "image1", "image2", ...
  * "001_image" -> "001_image", "002_image", ...
  * "image005" -> "image005", "image006", ...
  * Suppose `fields` contains field "date" returning current date (requiring a
    date format as a parameter). Then:
    "image_[date, %Y-%m-%d]_001" -> "image_2016-07-16_001", "image_2016-07-16_002", ...
  * Field specified, no explicit number specified:
    "[date]" -> "2016-07-16", "2016-07-16", ...
  * "image001_1234" -> "image001_1234", "image001_1235", ...
  * "image[001]_1234" -> "image001_1234", "image002_1234", ...
  * "[[image]]" -> "[image]001", "[image]002", ...
  * "[date, [[[%Y,%m,%d]]],]_001" -> "[2016,07,16]_001", "[2016,07,16]_002", ...
  """
  
  def __init__(self, pattern, fields=None):
    self._pattern = pattern
    self._fields = fields if fields is not None else {}
    
    self._number_generators = []
    
    self._pattern_parts = self._parse_pattern(self._pattern, self._fields)
  
  def generate(self):
    """
    Generate string from the pattern and fields given in the instance of this
    class. For more information about string generation, refer to the class
    documentation.
    """
    
    pattern_parts = []
    for part in self._pattern_parts:
      if isinstance(part, types.StringTypes):
        pattern_parts.append(part)
      else:
        pattern_parts.append(self._process_field(part))
    
    return "".join(pattern_parts)
  
  def _parse_pattern(self, pattern, fields):
    index = 0
    start_of_field_index = 0
    last_constant_substring_index = 0
    has_pattern_number_field = False
    has_fields = False
    field_depth = 0
    
    pattern_parts = []
    
    def _add_substring(end_index=None):
      start_index = max(last_constant_substring_index, start_of_field_index)
      if end_index is not None:
        pattern_parts.append(pattern[start_index:end_index])
      else:
        pattern_parts.append(pattern[start_index:])
    
    while index < len(pattern):
      if pattern[index] == "[":
        is_escaped = self._is_field_symbol_escaped(pattern, index, "[")
        if field_depth == 0 and is_escaped:
          _add_substring(index)
          pattern_parts.append("[")
          last_constant_substring_index = index + 2
          index += 2
          continue
        elif field_depth == 0 and not is_escaped:
          _add_substring(index)
          start_of_field_index = index
          field_depth += 1
        elif field_depth == 1:
          field_depth += 1
        elif field_depth > 1 and is_escaped:
          index += 2
          continue
        elif field_depth > 1 and not is_escaped:
          field_depth += 1
      elif pattern[index] == "]":
        is_escaped = self._is_field_symbol_escaped(pattern, index, "]")
        if field_depth == 0 and is_escaped:
          _add_substring(index)
          pattern_parts.append("]")
          last_constant_substring_index = index + 2
          index += 2
          continue
        elif field_depth == 0 and not is_escaped:
          index += 1
          continue
        elif field_depth == 1:
          field_depth -= 1
        elif field_depth > 1 and is_escaped:
          index += 2
          continue
        elif field_depth > 1 and not is_escaped:
          field_depth -= 1
          index += 1
          continue
        
        field_str = pattern[start_of_field_index + 1:index]
        field = self._parse_field(field_str)
        
        if field[0] in fields and self._is_field_valid(field):
          has_fields = True
          pattern_parts.append(field)
        elif self._is_field_number(field[0]) and not field[1]:
          has_fields = True
          has_pattern_number_field = True
          self._add_number_field(field[0])
          
          pattern_parts.append(field)
        else:
          _add_substring(index + 1)
        
        last_constant_substring_index = index + 1
      
      index += 1
    
    _add_substring()
    
    if not has_pattern_number_field:
      pattern_parts = self._parse_number(pattern_parts, has_fields)
    
    return pattern_parts

  def _parse_field(self, field_str):
    field_name_end_index = field_str.find(",")
    if field_name_end_index == -1:
      return field_str.strip(), []
    
    field_name = field_str[:field_name_end_index].strip()
    field_args_str = field_str[field_name_end_index + 1:]
    # Make parsing simpler without having to post-process the last argument outside the main loop.
    field_args_str += ","

    is_in_field_arg = False
    last_field_arg_end_index = 0
    index = 0
    field_args = []
    
    def _process_field_args(field_args):
      processed_field_args = []
      for field_arg in field_args:
        processed_arg = field_arg.strip()
        if not processed_arg:
          continue
        
        if processed_arg[0] == "[" and processed_arg[-1] == "]":
          processed_arg = processed_arg[1:-1]
        processed_arg = processed_arg.replace("[[", "[").replace("]]", "]")
        
        processed_field_args.append(processed_arg)
      
      return processed_field_args
    
    while index < len(field_args_str):
      if field_args_str[index] == ",":
        if is_in_field_arg:
          index += 1
          continue
        else:
          field_args.append(field_args_str[last_field_arg_end_index:index])
          last_field_arg_end_index = index + 1
      elif field_args_str[index] == "[":
        if self._is_field_symbol_escaped(field_args_str, index, "["):
          index += 2
          continue
        else:
          is_in_field_arg = True
      elif field_args_str[index] == "]":
        if self._is_field_symbol_escaped(field_args_str, index, "]"):
          index += 2
          continue
        else:
          is_in_field_arg = False
      
      index += 1
    
    return field_name, _process_field_args(field_args)
  
  def _process_field(self, field):
    return str(self._fields[field[0]](*field[1]))
  
  def _is_field_valid(self, field):
    field_func = self._fields[field[0]]
    
    argspec = inspect.getargspec(field_func)
    
    if argspec.keywords:
      raise ValueError("{0}: field functions with variable keyword arguments (**kwargs) are not supported"
                       .format(field_func.__name__))
    
    if not argspec.varargs:
      num_defaults = len(argspec.defaults) if argspec.defaults is not None else 0
      num_mandatory_args = len(argspec.args) - num_defaults
      if len(field[1]) < num_mandatory_args or len(field[1]) > len(argspec.args):
        return False
    
    return True
  
  def _is_field_symbol_escaped(self, pattern, index, symbol):
    return index + 1 < len(pattern) and pattern[index + 1] == symbol
  
  def _is_field_number(self, field_name):
    return bool(re.search(r"^[0-9]+$", field_name))
  
  def _parse_number(self, pattern_parts, has_fields):
    should_create_number_generator = True
    
    number_substr_match = re.search(r"[0-9]+$", pattern_parts[-1])
    if number_substr_match:
      number_str = number_substr_match.group()
      pattern_parts[-1] = pattern_parts[-1][:-len(number_str)]
      pattern_parts.append((number_str, []))
    else:
      number_substr_match = re.search(r"^[0-9]+", pattern_parts[0])
      if number_substr_match:
        number_str = number_substr_match.group()
        pattern_parts[0] = pattern_parts[0][len(number_str):]
        pattern_parts.insert(0, (number_str, []))
      else:
        number_str = "001"
        if has_fields:
          should_create_number_generator = False
        else:
          pattern_parts.append((number_str, []))
    
    if should_create_number_generator:
      self._add_number_field(number_str)
    
    return pattern_parts
  
  def _add_number_field(self, field_name):
    number_generator = self._generate_number(padding=len(field_name), initial_number=int(field_name))
    self._number_generators.append(number_generator)
    
    self._fields[field_name] = lambda: next(number_generator)
  
  def _generate_number(self, padding, initial_number):
    i = initial_number
    while True:
      str_i = str(i)
      
      if len(str_i) < padding:
        str_i = "0" * (padding - len(str_i)) + str_i
      
      yield str_i
      i += 1


#===============================================================================


def get_file_extension(str_, to_lowercase=True):
  """
  Return the file extension from the specified string in lower case and strip
  the leading period. If the string has no file extension, return empty string.
  
  A string has file extension if it contains a "." character and a substring
  following this character.
  
  Parameters:
  
  * `to_lowercase` - If True, convert the file extension to lowercase.
  """
  
  file_ext = os.path.splitext(str_)[1].lstrip(".")
  
  if to_lowercase:
    return file_ext.lower()
  else:
    return file_ext


# Taken from StackOverflow: http://stackoverflow.com/
# Question: http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
# Answer: http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python/600612#600612
def make_dirs(path):
  """
  Recursively create directories from the specified path.
  
  Do not raise exception if the path already exists.
  """
  
  try:
    os.makedirs(path)
  except OSError as exc:
    if exc.errno == os.errno.EEXIST and os.path.isdir(path):
      pass
    elif exc.errno == os.errno.EACCES and os.path.isdir(path):
      # This can happen if `os.makedirs` is called on a root directory
      # in Windows (e.g. `os.makedirs("C:\\")`).
      pass
    else:
      raise


def split_path(path):
  """
  Split the specified path into separate path components.
  """
  
  path = os.path.normpath(path)
  path_components = []
  
  head = path
  while True:
    head, tail = os.path.split(head)
    if tail:
      path_components.insert(0, tail)
    else:
      if head:
        path_components.insert(0, head)
      break
  
  return path_components


#===============================================================================


def N_(str_):
  return str_


class FileValidatorErrorStatuses(object):
  ERROR_STATUSES = (
    IS_EMPTY,
    HAS_INVALID_CHARS,
    DRIVE_HAS_INVALID_CHARS,
    HAS_TRAILING_SPACES,
    HAS_TRAILING_PERIOD,
    HAS_INVALID_NAMES,
    EXISTS_BUT_IS_NOT_DIR
  ) = range(7)


class StringValidator(object):
  
  """
  This class is an interface to validate strings.
  
  Strings are assumed to be Unicode strings.
  
  This class does not specify what strings are valid (whether they contain
  invalid characters, substrings, etc.). This should be handled by subclasses.
  """
  
  __metaclass__ = abc.ABCMeta
  
  ERROR_STATUSES_MESSAGES = {}
  
  @classmethod
  def is_valid(cls, string_to_check):
    """
    Check if the specified string is valid.
    
    Returns:
      
      * `is_valid` - True if the string is valid, False otherwise.
      
      * `status_messages` - If the string is invalid, `status_messages` is
        a list of (status code, status message) tuples describing why the string
        is invalid. Otherwise it is an empty list.
    """
    
    pass
  
  @classmethod
  def validate(cls, string_to_validate):
    """
    Modify the specified string to make it valid.
    """
    
    pass
  
  @classmethod
  def _status_tuple(cls, status):
    return (status, _(cls.ERROR_STATUSES_MESSAGES[status]))


class FilenameValidator(StringValidator):
  
  """
  This class is used to validate filenames (not their full path, only the
  name itself, also called "basenames").
  
  In this class, filenames are considered valid if they:
    
    * don't contain control characters with ordinal numbers 0-31 and 127-159
    
    * don't contain the following special characters:
      
      <>:"/\|?*
    
    * don't start or end with spaces
    
    * don't end with one or more periods
    
    * don't have invalid names according to the naming conventions for the
      Windows platform:
      
      http://msdn.microsoft.com/en-us/library/aa365247%28VS.85%29
    
    * are not empty or None
  """
  
  _INVALID_CHARS_PATTERN = r"[\x00-\x1f\x7f-\x9f<>:\"\\/|?*]"
  
  # Invalid names for the Windows platform. Taken from:
  # http://msdn.microsoft.com/en-us/library/windows/desktop/aa365247%28v=vs.85%29.aspx
  _INVALID_NAMES = {
   "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6",
   "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6",
   "LPT7", "LPT8", "LPT9"
  }
  
  ERROR_STATUSES_MESSAGES = {
    FileValidatorErrorStatuses.IS_EMPTY: N_("Filename is not specified."),
    FileValidatorErrorStatuses.HAS_INVALID_CHARS: N_("Filename contains invalid characters."),
    FileValidatorErrorStatuses.HAS_TRAILING_SPACES: N_("Filename cannot end with spaces."),
    FileValidatorErrorStatuses.HAS_TRAILING_PERIOD: N_("Filename cannot end with a period."),
    FileValidatorErrorStatuses.HAS_INVALID_NAMES: N_(
      "\"{0}\" is a reserved name that cannot be used in filenames.\n"),
  }
  
  @classmethod
  def is_valid(cls, filename):
    """
    Check whether the specified filename is valid.
    
    See the class description for details about when the filename is valid.
    """
    
    if not filename or filename is None:
      return False, [cls._status_tuple(FileValidatorErrorStatuses.IS_EMPTY)]
    
    status_messages = []
    
    if re.search(cls._INVALID_CHARS_PATTERN, filename):
      status_messages.append(cls._status_tuple(FileValidatorErrorStatuses.HAS_INVALID_CHARS))
    
    if filename.endswith(" "):
      status_messages.append(cls._status_tuple(FileValidatorErrorStatuses.HAS_TRAILING_SPACES))
    
    if filename.endswith("."):
      status_messages.append(cls._status_tuple(FileValidatorErrorStatuses.HAS_TRAILING_PERIOD))
    
    root, unused_ = os.path.splitext(filename)
    if root.upper() in cls._INVALID_NAMES:
      status_messages.append(cls._status_tuple(FileValidatorErrorStatuses.HAS_INVALID_NAMES))
    
    is_valid = not status_messages
    return is_valid, status_messages
  
  @classmethod
  def validate(cls, filename):
    """
    Validate the specified filename by removing invalid characters.
    
    If the filename is one of the reserved names for the Windows platform,
    append " (1)" to the filename (before the file extension if it has one).
    
    If the filename is truncated to an empty string, return "Untitled".
    """
    
    filename = (
      re.sub(cls._INVALID_CHARS_PATTERN, "", filename)
        .strip(" ")
        .rstrip(".")
    )
    
    root, ext = os.path.splitext(filename)
    # For reserved names, the comparison must be case-insensitive
    # (because Windows has case-insensitive filenames).
    if root.upper() in cls._INVALID_NAMES:
      filename = root + " (1)" + ext
    
    if not filename:
      filename = _("Untitled")
    
    return filename


class FilePathValidator(StringValidator):
  
  """
  This class is used to validate file paths (relative or absolute).
  
  The same validation rules that apply to filenames in the `FilenameValidator`
  class apply to file paths in this class, with the following exceptions:
    
    * "/" and "\" characters are allowed
    
    * ":" character is allowed to appear at the root level only (as a part of a
      drive letter, e.g. "C:\")
  """
  
  _INVALID_CHARS = r"\x00-\x1f\x7f-\x9f<>\"|?*"
  _VALID_DRIVE_CHARS = r":"
  
  _INVALID_CHARS_PATTERN_WITHOUT_DRIVE = "[" + _INVALID_CHARS + "]"
  _INVALID_CHARS_PATTERN = "[" + _INVALID_CHARS + _VALID_DRIVE_CHARS + "]"
  
  _INVALID_NAMES = FilenameValidator._INVALID_NAMES
  
  ERROR_STATUSES_MESSAGES = {
    FileValidatorErrorStatuses.IS_EMPTY: N_("File path is not specified."),
    FileValidatorErrorStatuses.DRIVE_HAS_INVALID_CHARS: N_("Drive letter contains invalid characters."),
    FileValidatorErrorStatuses.HAS_INVALID_CHARS: N_("File path contains invalid characters."),
    FileValidatorErrorStatuses.HAS_TRAILING_SPACES: N_(
      "Path components in the file path cannot end with spaces."),
    FileValidatorErrorStatuses.HAS_TRAILING_PERIOD: N_(
      "Path components in the file path cannot end with a period."),
    FileValidatorErrorStatuses.HAS_INVALID_NAMES: N_(
      "\"{0}\" is a reserved name that cannot be used in file paths.\n"),
  }
  
  @classmethod
  def is_valid(cls, filepath):
    if not filepath or filepath is None:
      return False, [cls._status_tuple(FileValidatorErrorStatuses.IS_EMPTY)]
    
    status_messages = []
    statuses = set()
    invalid_names_status_message = ""
    
    filepath = os.path.normpath(filepath)
    
    drive, path = os.path.splitdrive(filepath)
    
    if drive:
      if re.search(cls._INVALID_CHARS_PATTERN_WITHOUT_DRIVE, drive):
        status_messages.append(cls._status_tuple(FileValidatorErrorStatuses.DRIVE_HAS_INVALID_CHARS))
    
    path_components = split_path(path)
    for path_component in path_components:
      if re.search(cls._INVALID_CHARS_PATTERN, path_component):
        statuses.add(FileValidatorErrorStatuses.HAS_INVALID_CHARS)
      if path_component.endswith(" "):
        statuses.add(FileValidatorErrorStatuses.HAS_TRAILING_SPACES)
      if path_component.endswith("."):
        statuses.add(FileValidatorErrorStatuses.HAS_TRAILING_PERIOD)
      
      root, unused_ = os.path.splitext(path_component)
      if root.upper() in cls._INVALID_NAMES:
        statuses.add(FileValidatorErrorStatuses.HAS_INVALID_NAMES)
        invalid_names_status_message += (
          cls.ERROR_STATUSES_MESSAGES[FileValidatorErrorStatuses.HAS_INVALID_NAMES].format(root))
    
    if FileValidatorErrorStatuses.HAS_INVALID_CHARS in statuses:
      status_messages.append(cls._status_tuple(FileValidatorErrorStatuses.HAS_INVALID_CHARS))
    if FileValidatorErrorStatuses.HAS_TRAILING_SPACES in statuses:
      status_messages.append(cls._status_tuple(FileValidatorErrorStatuses.HAS_TRAILING_SPACES))
    if FileValidatorErrorStatuses.HAS_TRAILING_PERIOD in statuses:
      status_messages.append(cls._status_tuple(FileValidatorErrorStatuses.HAS_TRAILING_PERIOD))
    if FileValidatorErrorStatuses.HAS_INVALID_NAMES in statuses:
      invalid_names_status_message = invalid_names_status_message.rstrip("\n")
      status_messages.append((FileValidatorErrorStatuses.HAS_INVALID_NAMES, invalid_names_status_message))
    
    is_valid = not status_messages
    return is_valid, status_messages
  
  @classmethod
  def validate(cls, filepath):
    filepath = os.path.normpath(filepath)
    drive, path = os.path.splitdrive(filepath)
    
    if drive:
      drive = re.sub(cls._INVALID_CHARS_PATTERN_WITHOUT_DRIVE, "", drive)
    
    path_components = split_path(path)
    for i in range(len(path_components)):
      path_component = re.sub(cls._INVALID_CHARS_PATTERN, "", path_components[i])
      path_component = path_component.strip(" ").rstrip(".")
      
      root, ext = os.path.splitext(path_component)
      if root.upper() in cls._INVALID_NAMES:
        path_component = root + " (1)" + ext
      
      path_components[i] = path_component
    
    # Normalize again, since the last path component might be truncated to an
    # empty string, resulting in a trailing slash.
    filepath = os.path.normpath(os.path.join(drive, *path_components))
    
    return filepath


class DirectoryPathValidator(FilePathValidator):
   
  """
  This class is used to validate directory paths (relative or absolute).
  
  The same validation rules that apply to file paths in the `FilePathValidator`
  class apply to directory paths in this class, with the following additions:
  
    * the specified path must be a directory
  """
  
  ERROR_STATUSES_MESSAGES = {
    FileValidatorErrorStatuses.IS_EMPTY: N_("Directory path is not specified."),
    FileValidatorErrorStatuses.DRIVE_HAS_INVALID_CHARS: N_("Drive letter contains invalid characters."),
    FileValidatorErrorStatuses.HAS_INVALID_CHARS: N_("Directory path contains invalid characters."),
    FileValidatorErrorStatuses.HAS_TRAILING_SPACES: N_(
      "Path components in the directory path cannot end with spaces."),
    FileValidatorErrorStatuses.HAS_TRAILING_PERIOD: N_(
      "Path components in the directory path cannot end with a period."),
    FileValidatorErrorStatuses.HAS_INVALID_NAMES: N_(
      "\"{0}\" is a reserved name that cannot be used in directory paths.\n"),
    FileValidatorErrorStatuses.EXISTS_BUT_IS_NOT_DIR: N_("Specified path is not a directory.")
  }
  
  @classmethod
  def is_valid(cls, dirpath):
    unused_, status_messages = super(DirectoryPathValidator, cls).is_valid(dirpath)
    
    if os.path.exists(dirpath) and not os.path.isdir(dirpath):
      status_messages.append(cls._status_tuple(FileValidatorErrorStatuses.EXISTS_BUT_IS_NOT_DIR))
    
    is_valid = not status_messages
    return is_valid, status_messages
  

class FileExtensionValidator(StringValidator):
  
  """
  This class is used to validate file extensions.
  
  In this class, file extensions are considered valid if they:
    
    * don't contain control characters with ordinal numbers 0-31 and 127-159
    
    * don't contain the following special characters:
      
      <>:"/\|?*
    
    * don't end with spaces or periods
  """
  
  _INVALID_CHARS_PATTERN = FilenameValidator._INVALID_CHARS_PATTERN
  
  ERROR_STATUSES_MESSAGES = {
    FileValidatorErrorStatuses.IS_EMPTY: N_("File extension is not specified."),
    FileValidatorErrorStatuses.HAS_INVALID_CHARS: N_("File extension contains invalid characters."),
    FileValidatorErrorStatuses.HAS_TRAILING_SPACES: N_("File extension cannot end with spaces."),
    FileValidatorErrorStatuses.HAS_TRAILING_PERIOD: N_("File extension cannot end with a period.")
  }
  
  @classmethod
  def is_valid(cls, file_ext):
    if not file_ext or file_ext is None:
      return False, [cls._status_tuple(FileValidatorErrorStatuses.IS_EMPTY)]
    
    status_messages = []
    
    if re.search(cls._INVALID_CHARS_PATTERN, file_ext):
      status_messages.append(cls._status_tuple(FileValidatorErrorStatuses.HAS_INVALID_CHARS))
    
    if file_ext.endswith(" "):
      status_messages.append(cls._status_tuple(FileValidatorErrorStatuses.HAS_TRAILING_SPACES))
      
    if file_ext.endswith("."):
      status_messages.append(cls._status_tuple(FileValidatorErrorStatuses.HAS_TRAILING_PERIOD))
    
    is_valid = not status_messages
    return is_valid, status_messages
  
  @classmethod
  def validate(cls, file_ext):
    file_ext = (
      re.sub(cls._INVALID_CHARS_PATTERN, "", file_ext)
        .rstrip(" ")
        .rstrip(".")
    )
    
    return file_ext
