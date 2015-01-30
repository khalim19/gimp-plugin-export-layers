#-------------------------------------------------------------------------------
#
# This file is part of pygimplib.
#
# Copyright (C) 2014 khalim19 <khalim19@gmail.com>
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
#-------------------------------------------------------------------------------

"""
This module:
* defines setting classes that can be used to create plug-in settings
"""

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import os
import abc
from collections import OrderedDict

import gimp
import gimpenums

from .lib import enum

from . import pgpath
from . import pgsettingpresenter

#===============================================================================

pdb = gimp.pdb

#===============================================================================


class PdbRegistrationModes(enum.Enum):
  automatic = 0
  registrable = 1
  not_registrable = 2


#===============================================================================


class SettingValueError(Exception):
  """
  This exception class is raised when a value assigned to a `Setting` object is
  invalid.
  """
  
  pass


class SettingDefaultValueError(SettingValueError):
  """
  This exception class is raised when the default value specified during the
  `Setting` object initialization is invalid.
  """
  
  def __init__(self, message):
    self._message_invalid_default_value = _(
      "If you need to turn off validation of the default value, "
      "pass `validate_default_value=False` when creating a Setting object."
    )
    self.message = '\n'.join((message,self._message_invalid_default_value))
    
  def __str__(self):
    return self.message


#===============================================================================


class Setting(object):
  
  """
  This class holds data about a plug-in setting.
  
  Properties and methods in this class can be used in multiple scenarios, such as:
  * using setting values as variables in the main logic of plug-ins
  * registering GIMP Procedural Database (PDB) parameters to plug-ins
  * managing GUI element properties (values, labels, tooltips, etc.)
  
  It is recommended to use an appropriate subclass for a setting, as they offer
  the following features:
  * automatic validation of input values
  * readily available GUI element, keeping the GUI and the setting value in sync
  
  It is also possible to attach an event handler to the setting when the value
  of the setting changes (i.e. when `set_value()` method is called). This way,
  other settings and their GUI elements can be adjusted automatically.
  
  This class in particular:
  * allows to use any PDB type or no type
  * does not validate input values
  * does not have a GUI element assigned
  
  Attributes:
  
  * `name` (read-only) - A name (string) that uniquely identifies the setting.
  
  * `value` (read-only) - The setting value. To set the value, call the
    `set_value()` method. `value` is initially set to `default_value`.
  
  * `default_value` (read-only) - Default value of the setting assigned upon its
    initialization or after the `reset()` method is called.
  
  * `gui` (read-only) - `SettingPresenter` instance acting as a wrapper of a GUI
    element. With `gui`, you may modify GUI-specific attributes, such as
    visibility or sensitivity (enabled/disabled).
  
  * `display_name` (read-only) - Setting name in human-readable format. Useful
    e.g. as GUI labels.
  
  * `description` (read-only) - Describes the setting in more detail. Useful for
    documentation purposes as well as GUI tooltips.
  
  * `short_description` (read-only) - Usually `display_name` plus additional
    information in parentheses (such as boundaries for numeric values). Useful
    as a setting description when registering the setting as a plug-in parameter
    to the GIMP Procedural Database (PDB).
  
  * `pdb_type` (read-only) - GIMP PDB type, used when
    registering the setting as a plug-in parameter to the PDB. In the Setting
    class, any PDB type can be assigned. In Setting subclasses, only
    specific PDB types are allowed. Refer to the documentation of the subclasses
    for the list of allowed PDB types.
  
  * `pdb_registration_mode` (read-only) - Indicates how to register the setting
    as a PDB parameter. Possible values:
      
      * `PdbRegistrationModes.automatic` - automatically determine whether the
        setting can be registered based on `pdb_type`, if `pdb_type` is not None,
        allow the setting to be registered, otherwise disallow it.
        
      * `PdbRegistrationModes.registrable` - allow the setting to be registered.
        If this attribute is set to `registrable` and `pdb_type` is None, this
        is an error.
      
      * `PdbRegistrationModes.not_registrable` - do not allow the setting to be
      registered.
  
  * `pdb_name` (read-only) - Setting name as it appears in the GIMP PDB as
    a PDB parameter name.
  
  * `resettable_by_group` (read-only) - If True, the setting is allowed to be
    reset to its default value if the `reset()` method from the corresponding
    `SettingGroup` is called. False by default.
  
  * `error_messages` (read-only) - A dict of error messages containing
    (message name, message contents) pairs, which can be used e.g. if a value
    assigned to the setting is invalid. You can add your own error messages and
    assign them to one of the "default" error messages (such as 'invalid_value'
    in several `Setting` subclasses) depending on the context in which the value
    assigned is invalid.
  """
  
  _ALLOWED_PDB_TYPES = None
  
  def __init__(self, name, default_value, validate_default_value=True,
               display_name=None, description=None,
               pdb_type=None, pdb_registration_mode=PdbRegistrationModes.automatic,
               resettable_by_group=True,
               error_messages=None):
    
    """
    Described are only those parameters that do not correspond to
    any attribute in this class, or parameters requiring additional information.
    
    Parameters:
    
    * `validate_default_value` - If True, check whether the default value of the
       setting is valid. If it is invalid, raise `SettingDefaultValueError`. If
       you need to skip the validation, e.g. because you need to specify an
       "empty" value as the default value (e.g. an empty string for
       FileExtensionSetting), set this to False.
    
    * `pdb_type` - If None and this is a Setting subclass, assign the default
      PDB type from the list of allowed PDB types. If None and this is the
      Setting class, use None.
    
    * `error_messages` - A dict containing (message name, message contents)
      pairs. Use this to pass custom error messages. This way, you may also
      override default error messages defined in classes.
    """
    
    self._name = name
    self._default_value = default_value
    self._display_name = self._get_display_name(display_name)
    self._description = description if description is not None else ""
    self._pdb_type = self._get_pdb_type(pdb_type)
    self._pdb_registration_mode = self._get_pdb_registration_mode(pdb_registration_mode)
    self._resettable_by_group = resettable_by_group
    
    self._value = self._default_value
    self._pdb_name = self._get_pdb_name(self._name)
    
    self._value_changed_event_handler = None
    self._value_changed_event_handler_args = []
    
    self._setting_value_synchronizer = pgsettingpresenter.SettingValueSynchronizer()
    self._setting_value_synchronizer.apply_gui_value_to_setting = self._apply_gui_value_to_setting
    
    self._gui = pgsettingpresenter.NullSettingPresenter(self, self._setting_value_synchronizer)
    
    self._error_messages = {}
    self._init_error_messages()
    if error_messages is not None:
      self._error_messages.update(error_messages)
    
    if validate_default_value:
      self._validate_default_value()
  
  @property
  def name(self):
    return self._name
  
  @property
  def value(self):
    return self._value
  
  @property
  def default_value(self):
    return self._default_value
  
  @property
  def gui(self):
    return self._gui
  
  @property
  def display_name(self):
    return self._display_name
  
  @property
  def description(self):
    return self._description
  
  @property
  def short_description(self):
    return self.display_name
  
  @property
  def pdb_type(self):
    return self._pdb_type
  
  @property
  def pdb_registration_mode(self):
    return self._pdb_registration_mode
  
  @property
  def pdb_name(self):
    return self._pdb_name
  
  @property
  def resettable_by_group(self):
    return self._resettable_by_group
  
  @property
  def error_messages(self):
    return self._error_messages
  
  def set_value(self, value):
    """
    Set the setting value.
    
    Before the assignment, validate the value. If the value is invalid, raise
    `SettingValueError`.
    
    Update the value of the GUI element. Even if the setting has no GUI element
    assigned, the value is recorded. Once a GUI element is assigned to the
    setting, the recorded value is copied over to the GUI element.
    
    If an event handler is connected (via `connect_value_changed_event()`), call
    the event handler.
    
    Note: This is a method and not a property because of the additional overhead
    introduced by validation, GUI updating and event handling. `value` still
    remains a property for the sake of brevity.
    """
    
    self._assign_and_validate_value(value)
    self._setting_value_synchronizer.apply_setting_value_to_gui(value)
    if self._is_value_changed_event_connected():
      self._value_changed_event_handler(self, *self._value_changed_event_handler_args)
  
  def _assign_and_validate_value(self, value):
    self._validate(value)
    self._value = value
  
  def _apply_gui_value_to_setting(self, value):
    self._assign_and_validate_value(value)
    if self._is_value_changed_event_connected():
      self._value_changed_event_handler(self, *self._value_changed_event_handler_args)
  
  def reset(self):
    """
    Reset setting value to its default value.
    
    This is different from
    
      setting.set_value(setting.default_value)
    
    in that `reset()` does not validate the default value.
    
    `reset()` also updates the GUI and calls the event handler.
    """
    
    self._value = self._default_value
    self._setting_value_synchronizer.apply_setting_value_to_gui(self._default_value)
    if self._is_value_changed_event_connected():
      self._value_changed_event_handler(self, *self._value_changed_event_handler_args)
  
  def set_gui(self, gui_type, gui_element):
    """
    Assign new GUI object for this setting. The state of the previous GUI object
    is copied to the new GUI object (such as its value, visibility and
    sensitivity).
    
    Parameters:
    
    * `gui_type` - `SettingPresenter` type to wrap `gui_element` around.
    
    * `gui_element` - A GUI element.
    """
    
    self._gui = gui_type(self, gui_element, setting_value_synchronizer=self._setting_value_synchronizer,
                         old_setting_presenter=self._gui)
  
  def connect_value_changed_event(self, event_handler, *event_handler_args):
    """
    Connect an event handler that triggers when `set_value()` is called.
    
    The `event_handler` (a function) must always contain at least one argument.
    The first argument must be the setting from which the event handler is
    invoked.
    
    Parameters:
    
    * `event_handler` - Function to be called when `set_value()` from this
      setting is called.
    
    * `*event_handler_args` - Additional arguments to `event_handler`. Can be
      any arguments, including `Setting` objects.
    """
    
    if not callable(event_handler):
      raise TypeError("not a function")
    
    self._value_changed_event_handler = event_handler
    self._value_changed_event_handler_args = event_handler_args
  
  def remove_value_changed_event(self):
    """
    Remove the event handler set by the `connect_value_changed_event()` method.
    """
    
    if self._value_changed_event_handler is None:
      raise TypeError("no event handler was previously set")
    
    self._value_changed_event_handler = None
    self._value_changed_event_handler_args = []
  
  def _is_value_changed_event_connected(self):
    return self._value_changed_event_handler is not None
  
  def _validate(self, value):
    """
    Check whether the specified value is valid. If the value is invalid, raise
    `SettingValueError`.
    """
    
    pass
  
  def _init_error_messages(self):
    """
    Initialize custom error messages in the `error_messages` dict.
    """
    
    pass
  
  def _validate_default_value(self):
    """
    Check whether the default value of the setting is valid. If the default
    value is invalid, raise `SettingDefaultValueError`.
    """
    
    try:
      self._validate(self._default_value)
    except SettingValueError as e:
      raise SettingDefaultValueError(e.message)
  
  def _get_display_name(self, display_name):
    if display_name is not None:
      return display_name
    else:
      return self._generate_display_name()
  
  def _generate_display_name(self):
    return self.name.replace('_', ' ').capitalize()
  
  def _get_pdb_type(self, pdb_type):
    if not self._is_any_pdb_type_allowed():
      if pdb_type is None:
        return self._get_default_pdb_type()
      elif pdb_type in self._ALLOWED_PDB_TYPES:
        return pdb_type
      else:
        raise ValueError("GIMP PDB type " + str(pdb_type) + " not allowed; "
                         "for the list of allowed PDB types, refer to "
                         "the documentation of the appropriate Setting class")
    else:
      return pdb_type
  
  def _is_any_pdb_type_allowed(self):
    return self._ALLOWED_PDB_TYPES is None
  
  def _get_default_pdb_type(self):
    if self._ALLOWED_PDB_TYPES:
      return self._ALLOWED_PDB_TYPES[0]
    else:
      return None
  
  def _get_pdb_registration_mode(self, registration_mode):
    if registration_mode == PdbRegistrationModes.automatic:
      if self._pdb_type is not None:
        return PdbRegistrationModes.registrable
      else:
        return PdbRegistrationModes.not_registrable
    elif registration_mode == PdbRegistrationModes.registrable:
      if self._pdb_type is not None:
        return PdbRegistrationModes.registrable
      else:
        raise ValueError("setting cannot be registered to the GIMP PDB because "
                         "it has no PDB type set")
    elif registration_mode == PdbRegistrationModes.not_registrable:
      return PdbRegistrationModes.not_registrable
    else:
      raise ValueError("invalid PDB registration mode")
  
  def _get_pdb_name(self, name):
    """
    Return mangled setting name, useful when using the name in the short
    description (GIMP PDB automatically mangles setting names, but not
    descriptions).
    """
    
    return name.replace('_', '-')
  
  def _value_to_str(self, value):
    """
    Prepend `value` to an error message if `value` that is meant to be assigned
    to this setting is invalid.
    
    Don't prepend anything if `value` is empty or None.
    """
    
    if value:
      return '"' + str(value) + '": '
    else:
      return ""


#-------------------------------------------------------------------------------


class NumericSetting(Setting):
  
  """
  This is an abstract class for numeric settings - integers and floats.
  
  When assigning a value, it checks for the upper and lower bounds if they are set.
  
  Additional attributes:
  
  * `min_value` - Minimum allowed numeric value.
  
  * `max_value` - Maximum allowed numeric value.
  
  Raises:
  
  * `SettingValueError` - If `min_value` is not None and the value assigned is
    less than `min_value`, or if `max_value` is not None and the value assigned
    is greater than `max_value`.
  
  Error messages:
  
  * `'below_min'` - The value assigned is less than `min_value`.
  
  * `'above_max'` - The value assigned is greater than `max_value`.
  """
  
  __metaclass__ = abc.ABCMeta
  
  def __init__(self, name, default_value, min_value=None, max_value=None, **kwargs):
    self._min_value = min_value
    self._max_value = max_value
    
    super(NumericSetting, self).__init__(name, default_value, **kwargs)
  
  def _init_error_messages(self):
    self.error_messages['below_min'] = _("Value cannot be less than {0}.").format(self._min_value)
    self.error_messages['above_max'] = _("Value cannot be greater than {0}.").format(self._max_value)
  
  @property
  def min_value(self):
    return self._min_value
  
  @property
  def max_value(self):
    return self._max_value
  
  @property
  def short_description(self):
    if self._min_value is not None and self._max_value is None:
      return self._pdb_name + " >= " + str(self._min_value)
    elif self._min_value is None and self._max_value is not None:
      return self._pdb_name + " <= " + str(self._max_value)
    elif self._min_value is not None and self._max_value is not None:
      return str(self._min_value) + " <= " + self._pdb_name + " <= " + str(self._max_value)
    else:
      return self._display_name
  
  def _validate(self, value):
    if self._min_value is not None and value < self._min_value:
      raise SettingValueError(self._value_to_str(value) + self.error_messages['below_min'])
    if self._max_value is not None and value > self._max_value:
      raise SettingValueError(self._value_to_str(value) + self.error_messages['above_max'])


class IntSetting(NumericSetting):
  
  """
  This class can be used for integer settings.
  
  Allowed GIMP PDB types:
  
  * PDB_INT32 (default)
  * PDB_INT16
  * PDB_INT8
  """
  
  _ALLOWED_PDB_TYPES = [gimpenums.PDB_INT32, gimpenums.PDB_INT16, gimpenums.PDB_INT8]


class FloatSetting(NumericSetting):
  
  """
  This class can be used for float settings.
  
  Allowed GIMP PDB types:
  
  * PDB_FLOAT
  """
  
  _ALLOWED_PDB_TYPES = [gimpenums.PDB_FLOAT]
    

class BoolSetting(Setting):
  
  """
  This class can be used for boolean settings.
  
  Since GIMP does not have a boolean PDB type defined, use one of the integer
  types.
  
  Allowed GIMP PDB types:
  
  * PDB_INT32 (default)
  * PDB_INT16
  * PDB_INT8
  """
  
  _ALLOWED_PDB_TYPES = [gimpenums.PDB_INT32, gimpenums.PDB_INT16, gimpenums.PDB_INT8]
  
  @property
  def short_description(self):
    return self.display_name + "?"
  
  def set_value(self, value):
    value = bool(value)
    super(BoolSetting, self).set_value(value)


class EnumSetting(Setting):
  
  """
  This class can be used for settings with a limited number of values,
  accessed by their associated names.
  
  Allowed GIMP PDB types:
  
  * PDB_INT32 (default)
  * PDB_INT16
  * PDB_INT8
  
  Additional attributes:
  
  * `options` (read-only) - A dict of <option name, option value> pairs. Option name
    uniquely identifies each option. Option value is the corresponding integer value.
  
  * `options_display_names` (read-only) - A dict of <option name, option display name> pairs.
    Option display names can be used e.g. as combo box items in the GUI.
  
  To access an option value:
    setting.options[option name]
  
  To access an option display name:
    setting.options_display_names[option name]
  
  Raises:
  
  * `SettingValueError` - See `'invalid_value'` error message below.
  
  * `ValueError` - See the other error messages below.
  
  * `KeyError` - Invalid key to `options` or `options_display_names`.
  
  Error messages:
  
  * `'invalid_value'` - The value assigned is not one of the options in this setting.
  
  * `'invalid_default_value'` - Option name is invalid (not found in the `options` parameter
    when instantiating the object).
  """
  
  _ALLOWED_PDB_TYPES = [gimpenums.PDB_INT32, gimpenums.PDB_INT16, gimpenums.PDB_INT8]
  
  def __init__(self, name, default_value, options, validate_default_value=True, **kwargs):
    
    """
    Additional parameters:
    
    * `default_value` - Option name (identifier). Unlike other Setting classes,
      where the default value is specified directly, EnumSetting accepts a valid
      option name instead.
    
    * `options` - A list of either (option name, option display name) tuples
      or (option name, option display name, option value) tuples.
      
      For 2-element tuples, option values are assigned automatically, starting
      with 0. Use 3-element tuples to assign explicit option values. Values must be
      unique and specified in each tuple. You cannot combine 2- and 3- element
      tuples - use only 2- or only 3-element tuples.
    """
    
    self._options, self._options_display_names, self._option_values = self._create_option_attributes(options)
    
    orig_validate_default_value = validate_default_value
    
    if default_value in self._options:
      # `default_value` is a string, not an integer. In order to properly
      # initialize the setting, the actual default value must be passed.
      param_default_value = self._options[default_value]
    else:
      param_default_value = default_value
    
    super(EnumSetting, self).__init__(name, param_default_value, validate_default_value=False, **kwargs)
    
    self.error_messages['invalid_value'] = _(
      "Invalid option value; valid values: {0}"
    ).format(list(self._option_values))
    
    self.error_messages['invalid_default_value'] = (
      "invalid identifier for the default value; must be one of {0}"
    ).format(self._options.keys())
    
    if default_value not in self._options:
      if orig_validate_default_value:
        raise SettingDefaultValueError(self.error_messages['invalid_default_value'])
    
    self._options_str = self._stringify_options()
  
  @property
  def short_description(self):
    return self.display_name + " " + self._options_str
  
  @property
  def options(self):
    return self._options
  
  @property
  def options_display_names(self):
    return self._options_display_names
  
  def get_option_display_names_and_values(self):
    """
    Return a list of (option display name, option value) pairs.
    """
    
    display_names_and_values = []
    for option_name, option_value in zip(self._options_display_names.values(), self._options.values()):
      display_names_and_values.extend((option_name, option_value))
    return display_names_and_values
  
  def _validate(self, value):
    if value not in self._option_values:
      raise SettingValueError(self._value_to_str(value) + self.error_messages['invalid_value'])
  
  def _stringify_options(self):
    options_str = ""
    options_sep = ", "
    
    for value, display_name in zip(self._options.values(), self._options_display_names.values()):
      options_str += '{0} ({1}){2}'.format(display_name, value, options_sep)
    options_str = options_str[:-len(options_sep)]
    
    return "{ " + options_str + " }"
  
  def _create_option_attributes(self, input_options):
    options = OrderedDict()
    options_display_names = OrderedDict()
    option_values = set()
    
    if all(len(elem) == 2 for elem in input_options):
      for i, (option_name, option_display_name) in enumerate(input_options):
        options[option_name] = i
        options_display_names[option_name] = option_display_name
        option_values.add(i)
    elif all(len(elem) == 3 for elem in input_options):
      for option_name, option_display_name, option_value in input_options:
        if option_value in option_values:
          raise ValueError("Cannot set the same value for multiple options - they must be unique")
        
        options[option_name] = option_value
        options_display_names[option_name] = option_display_name
        option_values.add(option_value)
    else:
      raise ValueError("Wrong number of tuple elements in options - must be only 2- or only 3-element tuples")
    
    return options, options_display_names, option_values


class ImageSetting(Setting):
  
  """
  This setting class can be used for `gimp.Image` objects.
  
  Allowed GIMP PDB types:
  
  * PDB_IMAGE
  
  Error messages:
  
  * `'invalid_value'` - The image assigned is invalid.
  """
  
  _ALLOWED_PDB_TYPES = [gimpenums.PDB_IMAGE]
    
  def _init_error_messages(self):
    self.error_messages['invalid_value'] = _("Invalid image.")
  
  def _validate(self, image):
    if not pdb.gimp_image_is_valid(image):
      raise SettingValueError(self._value_to_str(image) + self.error_messages['invalid_value'])


class DrawableSetting(Setting):
  
  """
  This setting class can be used for `gimp.Drawable`, `gimp.Layer`,
  `gimp.GroupLayer` or `gimp.Channel` objects.
  
  Allowed GIMP PDB types:
  
  * PDB_DRAWABLE
  
  Error messages:
  
  * `'invalid_value'` - The drawable assigned is invalid.
  """
  
  _ALLOWED_PDB_TYPES = [gimpenums.PDB_DRAWABLE]
    
  def _init_error_messages(self):
    self.error_messages['invalid_value'] = _("Invalid drawable.")
  
  def _validate(self, drawable):
    if not pdb.gimp_item_is_valid(drawable):
      raise SettingValueError(self._value_to_str(drawable) + self.error_messages['invalid_value'])


class StringSetting(Setting):
  
  """
  This class can be used for string settings.
  
  Allowed GIMP PDB types:
  
  * PDB_STRING
  """
  
  _ALLOWED_PDB_TYPES = [gimpenums.PDB_STRING]


class ValidatableStringSetting(StringSetting):
  
  """
  This class is an abstract class for string settings which are meant to be
  validated with one of the `pgpath.StringValidator` subclasses.
  
  To determine whether the string is valid, the `is_valid()` method from the
  subclass being used is called.
  
  Allowed GIMP PDB types:
  
  * PDB_STRING
  
  Error messages:
  
  This class contains empty messages for error statuses from
  the specified `pgpath.StringValidator` subclass. Normally, if the value
  (string) assigned is invalid, status messages returned from `is_valid()`
  are used. If desired, you may fill the error messages with custom messages
  which override the status messages from the method. See `ERROR_STATUSES` in
  the specified `pgpath.StringValidator` subclass for available error statuses.
  """
  
  __metaclass__ = abc.ABCMeta
  
  def __init__(self, name, default_value, string_validator, **kwargs):
    """
    Additional parameters:
    
    * `string_validator` - `pgpath.StringValidator` subclass used to validate
      the value assigned to this object.
    """
    
    self._string_validator = string_validator
    
    super(ValidatableStringSetting, self).__init__(name, default_value, **kwargs)
    
  def _init_error_messages(self):
    for status in self._string_validator.ERROR_STATUSES:
      self.error_messages[status] = ""
  
  def _validate(self, value):
    is_valid, status_messages = self._string_validator.is_valid(value)
    if not is_valid:
      new_status_messages = []
      for status, status_message in status_messages:
        if self.error_messages[status]:
          new_status_messages.append(self.error_messages[status])
        else:
          new_status_messages.append(status_message)
      
      raise SettingValueError(
        self._value_to_str(value) + '\n'.join([message for message in new_status_messages])
      )
  

class FileExtensionSetting(ValidatableStringSetting):
  
  """
  This setting class can be used for file extensions.
  
  `pgpath.FileExtensionValidator` subclass is used to determine whether the file
  extension is valid.
  
  Allowed GIMP PDB types:
  
  * PDB_STRING
  """
  
  def __init__(self, name, default_value, **kwargs):
    super(FileExtensionSetting, self).__init__(name, default_value, pgpath.FileExtensionValidator, **kwargs)
  

class DirectorySetting(ValidatableStringSetting):
  
  """
  This setting class can be used for directories.
  
  `pgpath.FilePathValidator` subclass is used to determine whether the directory
  name is valid.
  
  Allowed GIMP PDB types:
  
  * PDB_STRING
  """
  
  def __init__(self, name, default_value, **kwargs):
    super(DirectorySetting, self).__init__(name, default_value, pgpath.FilePathValidator, **kwargs)
  
  def update_current_directory(self, current_image, directory_for_current_image):
    """
    Set the directory (setting value) to the value according to the priority list below:
    
    1. `directory_for_current_image` if not None
    2. `current_image` - import path of the current image if not None
    
    If both directories are None, do nothing.
    """
    
    if directory_for_current_image is not None:
      self.set_value(directory_for_current_image)
      return
    
    if current_image.filename is not None:
      self.set_value(os.path.dirname(current_image.filename))
      return


#-------------------------------------------------------------------------------


class ImageIDsAndDirectoriesSetting(Setting):
  
  """
  This setting class stores the list of currently opened images and their import
  directories as a dictionary of (image ID, import directory) pairs.
  Import directory is None if image has no import directory.
  
  This setting cannot be registered to the PDB as no corresponding PDB type exists.
  """
  
  @property
  def value(self):
    # Return a copy to prevent modifying the dictionary indirectly, e.g. via
    # setting individual entries (setting.value[image.ID] = directory).
    return dict(self._value)
  
  def update_image_ids_and_directories(self):
    """
    Remove all (image ID, import directory) pairs for images no longer opened in
    GIMP. Add (image ID, import directory) pairs for new images opened in GIMP.
    """
    
    # Get the list of images currently opened in GIMP
    current_images = gimp.image_list()
    current_image_ids = set([image.ID for image in current_images])
    
    # Remove images no longer opened in GIMP
    self._value = { image_id: self._value[image_id]
                    for image_id in self._value.keys() if image_id in current_image_ids }
    
    # Add new images opened in GIMP
    for image in current_images:
      if image.ID not in self._value.keys():
        self._value[image.ID] = self._get_imported_image_path(image)
  
  def update_directory(self, image_id, directory):
    """
    Assign a new directory to the specified image ID.
    
    If the image ID does not exist in the setting, raise KeyError. 
    """
    
    if image_id not in self._value:
      raise KeyError(image_id)
    
    self._value[image_id] = directory
  
  def _get_imported_image_path(self, image):
    if image.filename is not None:
      return os.path.dirname(image.filename)
    else:
      return None


#-------------------------------------------------------------------------------


class IntArraySetting(Setting):
    
  """
  This setting class can be used for integer arrays.
    
  Allowed GIMP PDB types:
    
  * PDB_INT32ARRAY (default)
  * PDB_INT16ARRAY
  * PDB_INT8ARRAY
  """
  
  #TODO:
  # - validation - value must be an iterable sequence
  #   - this applies to any array setting
  
  _ALLOWED_PDB_TYPES = [gimpenums.PDB_INT32ARRAY, gimpenums.PDB_INT16ARRAY, gimpenums.PDB_INT8ARRAY]


#===============================================================================


class SettingTypes(enum.Enum):
  
  """
  This enum maps Setting classes to more human-readable names.
  """
  
  generic = Setting
  integer = IntSetting
  float = FloatSetting
  boolean = BoolSetting
  enumerated = EnumSetting
  image = ImageSetting
  drawable = DrawableSetting
  string = StringSetting
  file_extension = FileExtensionSetting
  directory = DirectorySetting
  image_IDs_and_directories = ImageIDsAndDirectoriesSetting
  array_integer = IntArraySetting
