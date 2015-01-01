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

#===============================================================================

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

str = unicode

#===============================================================================

import unittest

import gimpenums

from ..lib import mock
from . import gimpmocks

from .. import pgsetting
from .. import pgpath

#===============================================================================

LIB_NAME = '.'.join(__name__.split('.')[:-2])

#===============================================================================


class MockSetting(pgsetting.Setting):
  
  def _validate(self, value):
    if value is None:
      raise pgsetting.SettingValueError("value cannot be None")


def streamline_file_extension(file_extension, ignore_invisible):
  if ignore_invisible.value:
    file_extension.set_value("png")
    file_extension.ui_enabled = False
  else:
    file_extension.set_value("jpg")
    file_extension.ui_enabled = True


#===============================================================================


class TestSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.Setting('file_extension', "png")
  
  def test_invalid_default_value_raises_error(self):
    with self.assertRaises(pgsetting.SettingDefaultValueError):
      MockSetting('setting', None)
  
  def test_default_value_without_validation(self):
    try:
      MockSetting('setting', None, validate_default_value=False)
    except pgsetting.SettingDefaultValueError:
      self.fail("SettingDefaultValueError should not be raised, default value validation is turned off")
  
  def test_value_invalid_assignment_operation(self):
    with self.assertRaises(AttributeError):
      self.setting.value = "jpg"
  
  def test_changed_attributes(self):
    self.setting.set_value("jpg")
    self.setting.ui_enabled = False
    self.setting.ui_visible = True
    
    for attr in ['value', 'ui_enabled', 'ui_visible']:
      self.assertTrue(attr in self.setting.changed_attributes,
                      msg=("'" + attr + "' not in " + str(self.setting.changed_attributes)))
  
  def test_pdb_registration_mode_automatic_is_registrable(self):
    setting = pgsetting.Setting('file_extension', "png", pdb_type=gimpenums.PDB_STRING)
    self.assertEqual(setting.pdb_registration_mode, pgsetting.PdbRegistrationModes.registrable)
  
  def test_pdb_registration_mode_automatic_is_not_registrable(self):
    setting = pgsetting.Setting('file_extension', "png", pdb_type=None)
    self.assertEqual(setting.pdb_registration_mode, pgsetting.PdbRegistrationModes.not_registrable)
  
  def test_invalid_pdb_type_and_registration_mode_raises_error(self):
    with self.assertRaises(ValueError):
      pgsetting.Setting('file_extension', "png", pdb_type=None,
                        pdb_registration_mode=pgsetting.PdbRegistrationModes.registrable)
  
  def test_reset(self):
    setting = pgsetting.Setting('file_extension', "png")
    setting.set_value("jpg")
    setting.reset()
    self.assertEqual(setting.value, "png")
  
  def test_set_remove_streamline_func(self):
    with self.assertRaises(TypeError):
      self.setting.remove_streamline_func()
    
    with self.assertRaises(TypeError):
      self.setting.set_streamline_func(None)
    
    with self.assertRaises(TypeError):
      self.setting.set_streamline_func("this is not a function")
  
  def test_invalid_streamline(self):
    with self.assertRaises(TypeError):
      self.setting.streamline()
  
  def test_can_streamline(self):
    self.setting.set_streamline_func(streamline_file_extension)
    self.assertTrue(self.setting.can_streamline())
    self.setting.remove_streamline_func()
    self.assertFalse(self.setting.can_streamline())
  
  def test_streamline(self):
    ignore_invisible = pgsetting.BoolSetting('ignore_invisible', False)
    self.setting.set_value("gif")
    self.setting.set_streamline_func(streamline_file_extension, ignore_invisible)
    
    changed_settings = self.setting.streamline()
    self.assertTrue(self.setting in changed_settings)
    self.assertTrue('ui_enabled' in changed_settings[self.setting])
    self.assertTrue('value' in changed_settings[self.setting])
    self.assertEqual(self.setting.ui_enabled, True)
    self.assertEqual(self.setting.value, "jpg")
  
  def test_streamline_force(self):
    ignore_invisible = pgsetting.BoolSetting('ignore_invisible', False)
    self.setting.set_streamline_func(streamline_file_extension, ignore_invisible)
    
    changed_settings = self.setting.streamline()
    self.assertEqual({}, changed_settings)
    
    changed_settings = self.setting.streamline(force=True)
    self.assertTrue(self.setting in changed_settings)


class TestIntSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.IntSetting('count', 0, min_value=0, max_value=100)
  
  def test_value_is_below_min(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(-5)
  
  def test_minimum_value_does_not_raise_error(self):
    try:
      self.setting.set_value(0)
    except pgsetting.SettingValueError:
      self.fail("SettingValueError should not be raised")
  
  def test_value_is_above_max(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(200)
  
  def test_maximum_value_does_not_raise_error(self):
    try:
      self.setting.set_value(100)
    except pgsetting.SettingValueError:
      self.fail("SettingValueError should not be raised")


class TestFloatSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.FloatSetting('clip_percent', 0.0, min_value=0.0, max_value=100.0)
  
  def test_value_below_min(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(-5.0)
  
  def test_minimum_value_does_not_raise_error(self):
    try:
      self.setting.set_value(0.0)
    except pgsetting.SettingValueError:
      self.fail("SettingValueError should not be raised")
  
  def test_value_above_max(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(200.0)
  
  def test_maximum_value_does_not_raise_error(self):
    try:
      self.setting.set_value(100.0)
    except pgsetting.SettingValueError:
      self.fail("SettingValueError should not be raised")


class TestEnumSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.EnumSetting(
      'overwrite_mode', 'replace',
      [('skip', "Skip"), ('replace', "Replace")],
      display_name="Overwrite mode (non-interactive only)")
  
  def test_explicit_values(self):
    setting = pgsetting.EnumSetting(
      'overwrite_mode', 'replace',
      [('skip', "Skip", 5),
       ('replace', "Replace", 6)])
    self.assertEqual(setting.options['skip'], 5)
    self.assertEqual(setting.options['replace'], 6)
    
    with self.assertRaises(ValueError):
      pgsetting.EnumSetting(
        'overwrite_mode', 'replace',
        [('skip', "Skip", 4),
         ('replace', "Replace")])
    
    with self.assertRaises(ValueError):
      pgsetting.EnumSetting(
        'overwrite_mode', 'replace',
        [('skip', "Skip", 4),
         ('replace', "Replace", 4)])
  
  def test_invalid_default_value(self):
    with self.assertRaises(pgsetting.SettingDefaultValueError):
      pgsetting.EnumSetting(
        'overwrite_mode', 'invalid_default_value',
        [('skip', "Skip"),
         ('replace', "Replace")])
  
  def test_default_value_no_validation(self):
    try:
      pgsetting.EnumSetting(
        'overwrite_mode', None,
        [('skip', "Skip"),
         ('replace', "Replace")],
        validate_default_value=False)
    except pgsetting.SettingDefaultValueError:
      self.fail("SettingDefaultValueError should not be raised, default value validation is turned off")
  
  def test_invalid_options_length_varying(self):
    with self.assertRaises(ValueError):
      pgsetting.EnumSetting(
          'overwrite_mode', None,
          [('skip', "Skip", 1),
           ('replace', "Replace")])
  
  def test_invalid_options_length_too_many_elements(self):
    with self.assertRaises(ValueError):
      pgsetting.EnumSetting(
          'overwrite_mode', None,
          [('skip', "Skip", 1, 1),
           ('replace', "Replace", 1, 1)])
  
  def test_invalid_options_length_too_few_elements(self):
    with self.assertRaises(ValueError):
      pgsetting.EnumSetting(
          'overwrite_mode', None,
          [('skip'),
           ('replace')])
  
  def test_set_invalid_option(self):
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(4)
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(-1)
  
  def test_get_invalid_option(self):
    with self.assertRaises(KeyError):
      self.setting.options['invalid_option']
  
  def test_short_description(self):
    self.assertEqual(self.setting.short_description,
                     self.setting.display_name + " { Skip (0), Replace (1) }")
  
  def test_get_option_display_names_and_values(self):
    self.assertEqual(self.setting.get_option_display_names_and_values(), ["Skip", 0, "Replace", 1])


class TestImageSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.ImageSetting('image', None, validate_default_value=False)
  
  @mock.patch(LIB_NAME + '.pgsetting.pdb', new=gimpmocks.MockPDB())
  def test_invalid_image(self):
    pdb = gimpmocks.MockPDB()
    image = pdb.gimp_image_new(2, 2, gimpenums.RGB)
    pdb.gimp_image_delete(image)
    with self.assertRaises(pgsetting.SettingValueError):
      self.setting.set_value(image)


class TestFileExtensionSetting(unittest.TestCase):
  
  def setUp(self):
    self.setting = pgsetting.FileExtensionSetting('file_ext', "png")
  
  def test_custom_error_message(self):
    self.setting.error_messages[pgpath.FileExtensionValidator.IS_EMPTY] = "My Custom Message"
    
    try:
      self.setting.set_value("")
    except pgsetting.SettingValueError as e:
      self.assertEqual(e.message, "My Custom Message")

