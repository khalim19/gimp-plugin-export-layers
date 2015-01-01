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

import errno
from StringIO import StringIO

import unittest

import gimpenums

from ..lib import mock
from . import gimpmocks

from .. import pgsetting
from .. import pgsettinggroup

#===============================================================================

LIB_NAME = '.'.join(__name__.split('.')[:-2])

#===============================================================================


class MockStringIO(StringIO):
  def read(self):
    return self.getvalue()


class MockGuiWidget(object):
  def __init__(self, value):
    self.value = value
    self.enabled = True
    self.visible = True


class MockSettingPresenter(pgsettinggroup.SettingPresenter):
  
  def get_value(self):
    return self._element.value
  
  def set_value(self, value):
    self._element.value = value

  def get_enabled(self):
    return self._element.enabled
  
  def set_enabled(self, value):
    self._element.enabled = value

  def get_visible(self):
    return self._element.visible
  
  def set_visible(self, value):
    self._element.visible = value
  
  def connect_event(self, event_func, *event_args):
    pass
  
  def set_tooltip(self):
    pass


class MockSettingPresenterGroup(pgsettinggroup.SettingPresenterGroup):
  
  def _gui_on_element_value_change(self, presenter):
    self._on_element_value_change(presenter)
  
  def _gui_on_element_value_change_streamline(self, presenter):
    self._on_element_value_change(presenter)


class SettingGroupTest(pgsettinggroup.SettingGroup):
  
  def _create_settings(self):
    
    self._add(pgsetting.FileExtensionSetting('file_extension', "bmp", resettable_by_group=False))
    
    self._add(pgsetting.BoolSetting('ignore_invisible', False))
    
    self._add(
      pgsetting.EnumSetting(
       'overwrite_mode', 'rename_new',
       [('replace', "Replace"),
        ('skip', "Skip"),
        ('rename_new', "Rename new file"),
        ('rename_existing', "Rename existing file")])
    )
    
    self['file_extension'].set_streamline_func(streamline_file_extension, self['ignore_invisible'])
    self['overwrite_mode'].set_streamline_func(streamline_overwrite_mode, self['ignore_invisible'], self['file_extension'])


class NewSettingGroupTest(pgsettinggroup.SettingGroup):
   
  def _create_settings(self):
     
    self._add(
      pgsetting.FileExtensionSetting,
      name='file_extension',
      default_value='bmp',
      resettable_by_group=False
    )
    
    self._add(
      pgsetting.BoolSetting,
      name='ignore_invisible',
      default_value=False,
      display_name="Ignore invisible"
    )
    
    self._add(
      pgsetting.EnumSetting,
      name='overwrite_mode',
      default_value='rename_new',
      options=[('replace', "Replace"),
               ('skip', "Skip"),
               ('rename_new', "Rename new file"),
               ('rename_existing', "Rename existing file")],
    )
    
    self['file_extension'].set_streamline_func(streamline_file_extension, self['ignore_invisible'])
    self['overwrite_mode'].set_streamline_func(streamline_overwrite_mode, self['ignore_invisible'], self['file_extension'])


def streamline_file_extension(file_extension, ignore_invisible):
  if ignore_invisible.value:
    file_extension.set_value("png")
    file_extension.ui_enabled = False
  else:
    file_extension.set_value("jpg")
    file_extension.ui_enabled = True


def streamline_overwrite_mode(overwrite_mode, ignore_invisible, file_extension):
  if ignore_invisible.value:
    overwrite_mode.set_value(overwrite_mode.options['skip'])
    file_extension.error_messages['custom'] = "custom error message"
  else:
    overwrite_mode.set_value(overwrite_mode.options['replace'])
    file_extension.error_messages['custom'] = "different custom error message"


#===============================================================================


class TestSettingGroup(unittest.TestCase):
  
  def setUp(self):
    self.settings = SettingGroupTest()
      
  def test_get_setting_invalid_key(self):
    with self.assertRaises(KeyError):
      self.settings['invalid_key']
  
  def test_streamline(self):
    self.settings.streamline(force=True)
    self.assertEqual(self.settings['file_extension'].value, "jpg")
    self.assertEqual(self.settings['file_extension'].ui_enabled, True)
    self.assertEqual(self.settings['overwrite_mode'].value, self.settings['overwrite_mode'].options['replace'])
  
  def test_reset(self):
    self.settings['overwrite_mode'].set_value(self.settings['overwrite_mode'].options['rename_new'])
    self.settings['file_extension'].set_value("jpg")
    self.settings.reset()
    self.assertEqual(self.settings['overwrite_mode'].value, self.settings['overwrite_mode'].default_value)
    self.assertNotEqual(self.settings['file_extension'].value, self.settings['file_extension'].default_value)
    self.assertEqual(self.settings['file_extension'].value, "jpg")


#===============================================================================


# class TestSettingAttributeSubstitutor(unittest.TestCase):
#   
#   def test_substitute_attributes(self):
#     description=("If this setting is enabled, \"{0}\" will be, for some reason, "
#                    "set to \"{1}\".").format(self._get_setting_property('file_extension', 'display_name'),
#                                              self._get_setting_property('file_extension', 'default_value'))
#     
#     description=("If this setting is enabled, {0} will be, for some reason, "
#                  "set to {1} " + self._get_setting_property('file_extension', 'display_name'))
#     description=("If this setting is enabled, {} will be, for some reason, "
#                  "set to {} " + self._get_setting_property('file_extension', 'display_name'))
#     description=("If this setting is enabled, {{}} {0} will be, for some reason, "
#                  "set to {{}} ".format(self._get_setting_property('file_extension', 'display_name')))
#     temp_str = "If this setting is enabled, {} {} will be, for some reason, set to {} "
#     final_str = "If this setting is enabled, File extension {} will be, for some reason, set to {} "


#===============================================================================


class TestSettingPresenterGroup(unittest.TestCase):
  
  def setUp(self):
    self.settings = SettingGroupTest()
    self.element = MockGuiWidget("")
    self.setting_presenter = MockSettingPresenter(self.settings['file_extension'], self.element)
    
    self.presenters = MockSettingPresenterGroup()
    self.presenters.add(self.setting_presenter)
    self.presenters.add(MockSettingPresenter(self.settings['overwrite_mode'],
                                             MockGuiWidget(self.settings['overwrite_mode'].options['skip'])))
    self.presenters.add(MockSettingPresenter(self.settings['ignore_invisible'], MockGuiWidget(False)))
  
  def test_assign_setting_values_to_elements(self):
    self.settings['file_extension'].set_value("png")
    self.settings['ignore_invisible'].set_value(True)
    
    self.presenters.assign_setting_values_to_elements()
    
    self.assertEqual(self.presenters[self.settings['file_extension']].get_value(), "png")
    self.assertEqual(self.presenters[self.settings['file_extension']].get_enabled(), False)
    self.assertEqual(self.presenters[self.settings['ignore_invisible']].get_value(), True)
  
  def test_assign_element_values_to_settings_with_streamline(self):
    self.presenters[self.settings['file_extension']].set_value("jpg")
    self.presenters[self.settings['ignore_invisible']].set_value(True)
    
    self.presenters.assign_element_values_to_settings()
    
    self.assertEqual(self.settings['file_extension'].value, "png")
    self.assertEqual(self.settings['file_extension'].ui_enabled, False)
  
  def test_assign_element_values_to_settings_no_streamline(self):
    # `value_changed_signal` is None, so no event handlers are invoked.
    self.presenters.connect_value_changed_events()
    
    self.presenters[self.settings['file_extension']].set_value("jpg")
    self.presenters[self.settings['ignore_invisible']].set_value(True)
    
    self.presenters.assign_element_values_to_settings()
    
    self.assertEqual(self.settings['file_extension'].value, "jpg")
    self.assertEqual(self.settings['file_extension'].ui_enabled, True)


#===============================================================================


class TestShelfSettingStream(unittest.TestCase):
  
  @mock.patch(LIB_NAME + '.pgsettinggroup.gimpshelf.shelf', new=gimpmocks.MockGimpShelf())
  def setUp(self):
    self.prefix = 'prefix'
    self.stream = pgsettinggroup.GimpShelfSettingStream(self.prefix)
    self.settings = SettingGroupTest()
  
  @mock.patch(LIB_NAME + '.pgsettinggroup.gimpshelf.shelf', new=gimpmocks.MockGimpShelf())
  def test_write(self):
    self.settings['file_extension'].set_value("png")
    self.settings['ignore_invisible'].set_value(True)
    self.stream.write(self.settings)
    
    self.assertEqual(pgsettinggroup.gimpshelf.shelf[self.prefix + 'file_extension'], "png")
    self.assertEqual(pgsettinggroup.gimpshelf.shelf[self.prefix + 'ignore_invisible'], True)
  
  @mock.patch(LIB_NAME + '.pgsettinggroup.gimpshelf.shelf', new=gimpmocks.MockGimpShelf())
  def test_read(self):
    pgsettinggroup.gimpshelf.shelf[self.prefix + 'file_extension'] = "png"
    pgsettinggroup.gimpshelf.shelf[self.prefix + 'ignore_invisible'] = True
    self.stream.read([self.settings['file_extension'], self.settings['ignore_invisible']])
    self.assertEqual(self.settings['file_extension'].value, "png")
    self.assertEqual(self.settings['ignore_invisible'].value, True)
  
  @mock.patch(LIB_NAME + '.pgsettinggroup.gimpshelf.shelf', new=gimpmocks.MockGimpShelf())
  def test_read_settings_not_found(self):
    with self.assertRaises(pgsettinggroup.SettingsNotFoundInStreamError):
      self.stream.read(self.settings)
  
  @mock.patch(LIB_NAME + '.pgsettinggroup.gimpshelf.shelf', new=gimpmocks.MockGimpShelf())
  def test_read_invalid_setting_value(self):
    setting_with_invalid_value = pgsetting.IntSetting('int', -1, min_value=0, validate_default_value=False)
    self.stream.write([setting_with_invalid_value])
    self.stream.read([setting_with_invalid_value])
    self.assertEqual(setting_with_invalid_value.value, setting_with_invalid_value.default_value)


@mock.patch('__builtin__.open')
class TestJSONFileSettingStream(unittest.TestCase):
  
  def setUp(self):
    self.stream = pgsettinggroup.JSONFileSettingStream("/test/file")
    self.settings = SettingGroupTest()
  
  def test_write_read(self, mock_file):
    self.settings['file_extension'].set_value("jpg")
    self.settings['ignore_invisible'].set_value(True)
    
    mock_file.return_value.__enter__.return_value = MockStringIO()
    
    self.stream.write(self.settings)
    self.stream.read(self.settings)
    self.assertEqual(self.settings['file_extension'].value, "jpg")
    self.assertEqual(self.settings['ignore_invisible'].value, True)
  
  def test_write_ioerror_oserror(self, mock_file):
    mock_file.side_effect = IOError("Whatever other I/O error it could be")
    with self.assertRaises(pgsettinggroup.SettingStreamWriteError):
      self.stream.write(self.settings)
    
    mock_file.side_effect = OSError("Permission denied or whatever other OS error it could be")
    with self.assertRaises(pgsettinggroup.SettingStreamWriteError):
      self.stream.write(self.settings)
  
  def test_read_ioerror_oserror(self, mock_file):
    mock_file.side_effect = IOError("File not found or whatever other I/O error it could be")
    with self.assertRaises(pgsettinggroup.SettingStreamReadError):
      self.stream.read(self.settings)
    
    mock_file.side_effect = OSError("Permission denied or whatever other OS error it could be")
    with self.assertRaises(pgsettinggroup.SettingStreamReadError):
      self.stream.read(self.settings)

  def test_read_invalid_file_extension(self, mock_file):
    mock_file.side_effect = ValueError("Invalid file format; must be JSON")
    with self.assertRaises(pgsettinggroup.SettingStreamInvalidFormatError):
      self.stream.read(self.settings)

  def test_read_invalid_setting_value(self, mock_file):
    mock_file.return_value.__enter__.return_value = MockStringIO()
    
    setting_with_invalid_value = pgsetting.IntSetting('int', -1, min_value=0, validate_default_value=False)
    self.stream.write([setting_with_invalid_value])
    self.stream.read([setting_with_invalid_value])
    self.assertEqual(setting_with_invalid_value.value, setting_with_invalid_value.default_value)
  
  def test_read_settings_not_found(self, mock_file):
    mock_file.return_value.__enter__.return_value = MockStringIO()
    
    self.stream.write([pgsetting.IntSetting('int', -1)])
    with self.assertRaises(pgsettinggroup.SettingsNotFoundInStreamError):
      self.stream.read(self.settings)


#===============================================================================


@mock.patch('__builtin__.open')
class TestSettingPersistor(unittest.TestCase):
  
  @mock.patch(LIB_NAME + '.pgsettinggroup.gimpshelf.shelf', new=gimpmocks.MockGimpShelf())
  def setUp(self):
    self.settings = SettingGroupTest()
    self.shelf_stream = pgsettinggroup.GimpShelfSettingStream('')
    self.json_stream = pgsettinggroup.JSONFileSettingStream('filename')
  
  @mock.patch(LIB_NAME + '.pgsettinggroup.gimpshelf.shelf', new=gimpmocks.MockGimpShelf())
  def test_load_save(self, mock_file):
    mock_file.return_value.__enter__.return_value = MockStringIO()
    
    self.settings['file_extension'].set_value("png")
    self.settings['ignore_invisible'].set_value(True)
    
    status, unused_ = pgsettinggroup.SettingPersistor.save([self.settings], [self.shelf_stream, self.json_stream])
    self.assertEqual(status, pgsettinggroup.SettingPersistor.SUCCESS)
    
    self.settings['file_extension'].set_value("jpg")
    self.settings['ignore_invisible'].set_value(False)
    
    status, unused_ = pgsettinggroup.SettingPersistor.load([self.settings], [self.shelf_stream, self.json_stream])
    self.assertEqual(status, pgsettinggroup.SettingPersistor.SUCCESS)
    self.assertEqual(self.settings['file_extension'].value, "png")
    self.assertEqual(self.settings['ignore_invisible'].value, True)
  
  @mock.patch(LIB_NAME + '.pgsettinggroup.gimpshelf.shelf', new=gimpmocks.MockGimpShelf())
  def test_load_combine_settings_from_multiple_streams(self, mock_file):
    mock_file.return_value.__enter__.return_value = MockStringIO()
    
    self.settings['file_extension'].set_value("png")
    self.settings['ignore_invisible'].set_value(True)
    self.shelf_stream.write([self.settings['file_extension']])
    self.settings['file_extension'].set_value("jpg")
    self.json_stream.write([self.settings['ignore_invisible'], self.settings['file_extension']])
    self.settings['file_extension'].set_value("gif")
    self.settings['ignore_invisible'].set_value(False)
    
    pgsettinggroup.SettingPersistor.load([self.settings], [self.shelf_stream, self.json_stream])
    
    self.assertEqual(self.settings['file_extension'].value, "png")
    self.assertEqual(self.settings['ignore_invisible'].value, True)
    
    for setting in self.settings:
      if setting not in [self.settings['file_extension'], self.settings['ignore_invisible']]:
        self.assertEqual(setting.value, setting.default_value)
  
  @mock.patch(LIB_NAME + '.pgsettinggroup.gimpshelf.shelf', new=gimpmocks.MockGimpShelf())
  def test_load_settings_file_not_found(self, mock_file):
    mock_file.return_value.__enter__.return_value = MockStringIO()
    mock_file.side_effect = IOError("File not found")
    mock_file.side_effect.errno = errno.ENOENT
    
    status, unused_ = pgsettinggroup.SettingPersistor.load([self.settings], [self.shelf_stream, self.json_stream])
    self.assertEqual(status, pgsettinggroup.SettingPersistor.NOT_ALL_SETTINGS_FOUND)
    
  @mock.patch(LIB_NAME + '.pgsettinggroup.gimpshelf.shelf', new=gimpmocks.MockGimpShelf())
  def test_load_settings_not_found(self, mock_file):
    mock_file.return_value.__enter__.return_value = MockStringIO()
    self.shelf_stream.write([self.settings['ignore_invisible']])
    self.json_stream.write([self.settings['file_extension'], self.settings['ignore_invisible']])
    
    status, unused_ = pgsettinggroup.SettingPersistor.load([self.settings['overwrite_mode']],
                                                           [self.shelf_stream, self.json_stream])
    self.assertEqual(status, pgsettinggroup.SettingPersistor.NOT_ALL_SETTINGS_FOUND)
  
  @mock.patch(LIB_NAME + '.pgsettinggroup.gimpshelf.shelf', new=gimpmocks.MockGimpShelf())
  def test_load_read_fail(self, mock_file):
    mock_file.return_value.__enter__.return_value = MockStringIO()
    
    status, unused_ = pgsettinggroup.SettingPersistor.load([self.settings], [self.shelf_stream, self.json_stream])
    self.assertEqual(status, pgsettinggroup.SettingPersistor.READ_FAIL)
    
    mock_file.side_effect = IOError()
    status, unused_ = pgsettinggroup.SettingPersistor.load([self.settings], [self.shelf_stream, self.json_stream])
    self.assertEqual(status, pgsettinggroup.SettingPersistor.READ_FAIL)
    
    mock_file.side_effect = OSError()
    status, unused_ = pgsettinggroup.SettingPersistor.load([self.settings], [self.shelf_stream, self.json_stream])
    self.assertEqual(status, pgsettinggroup.SettingPersistor.READ_FAIL)
  
  @mock.patch(LIB_NAME + '.pgsettinggroup.gimpshelf.shelf', new=gimpmocks.MockGimpShelf())
  def test_save_write_fail(self, mock_file):
    mock_file.return_value.__enter__.return_value = MockStringIO()
    
    mock_file.side_effect = IOError()
    status, unused_ = pgsettinggroup.SettingPersistor.save([self.settings], [self.shelf_stream, self.json_stream])
    self.assertEqual(status, pgsettinggroup.SettingPersistor.WRITE_FAIL)
    
    mock_file.side_effect = OSError()
    status, unused_ = pgsettinggroup.SettingPersistor.save([self.settings], [self.shelf_stream, self.json_stream])
    self.assertEqual(status, pgsettinggroup.SettingPersistor.WRITE_FAIL)


#===============================================================================


class TestPdbParamCreator(unittest.TestCase):
  
  def setUp(self):
    self.file_ext_setting = pgsetting.FileExtensionSetting("file_extension", "png",
                                                           display_name="File extension")
    self.unregistrable_setting = pgsetting.IntSetting("num_exported_layers", 0,
                                                      pdb_registration_mode=pgsetting.PdbRegistrationModes.not_registrable)
    self.settings = SettingGroupTest()
  
  def test_create_one_param_successfully(self):
    params = pgsettinggroup.PdbParamCreator.create_params(self.file_ext_setting)
    # There's only one PDB parameter returned.
    param = params[0]
    
    self.assertTrue(len(param), 3)
    self.assertEqual(param[0], gimpenums.PDB_STRING)
    self.assertEqual(param[1], "file_extension".encode())
    self.assertEqual(param[2], "File extension".encode())
  
  def test_create_params_invalid_argument(self):
    with self.assertRaises(TypeError):
      pgsettinggroup.PdbParamCreator.create_params([self.file_ext_setting])
  
  def test_create_multiple_params(self):
    params = pgsettinggroup.PdbParamCreator.create_params(self.file_ext_setting, self.settings)
    
    self.assertTrue(len(params), 1 + len(self.settings))
    
    self.assertEqual(params[0], (self.file_ext_setting.pdb_type, self.file_ext_setting.name.encode(),
                                 self.file_ext_setting.short_description.encode()))
    for param, setting in zip(params[1:], self.settings):
      self.assertEqual(param, (setting.pdb_type, setting.name.encode(),
                               setting.short_description.encode()))
  
  def test_create_params_with_unregistrable_setting(self):
    params = pgsettinggroup.PdbParamCreator.create_params(self.unregistrable_setting)
    self.assertEqual(params, [])
