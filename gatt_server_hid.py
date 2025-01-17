from __future__ import print_function
import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service

import array

import functools

try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject

from random import randint

import exceptions
import adapters

BLUEZ_SERVICE_NAME = 'org.bluez'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'

LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'

GATT_MANAGER_IFACE = 'org.bluez.GattManager1'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE =    'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE =    'org.bluez.GattDescriptor1'



class Application(dbus.service.Object):
    """
    org.bluez.GattApplication1 interface implementation
    """
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        # self.add_service(GenericAccessService(bus, 0))
        # self.add_service(GenericAttributeService(bus, 1))
        self.add_service(BatteryService(bus, 0))
        self.add_service(HidService(bus, 1))

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        print('GetManagedObjects')

        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response


class Service(dbus.service.Object):
    """
    org.bluez.GattService1 interface implementation
    """
    PATH_BASE = '/org/bluez/example/service'

    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_SERVICE_IFACE: {
                        'UUID': self.uuid,
                        'Primary': self.primary,
                        'Characteristics': dbus.Array(
                                self.get_characteristic_paths(),
                                signature='o')
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        return result

    def get_characteristics(self):
        return self.characteristics

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise exceptions.InvalidArgsException()

        return self.get_properties()[GATT_SERVICE_IFACE]

class Characteristic(dbus.service.Object):
    """
    org.bluez.GattCharacteristic1 interface implementation
    """
    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_CHRC_IFACE: {
                        'Service': self.service.get_path(),
                        'UUID': self.uuid,
                        'Flags': self.flags,
                        'Descriptors': dbus.Array(
                                self.get_descriptor_paths(),
                                signature='o')
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor):
        self.descriptors.append(descriptor)

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.get_path())
        return result

    def get_descriptors(self):
        return self.descriptors

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise exceptions.InvalidArgsException()

        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE,
                        in_signature='a{sv}',
                        out_signature='ay')
    def ReadValue(self, options):
        print(f'Default ReadValue called, returning error for {self.uuid}')
        raise exceptions.NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print('Default WriteValue called, returning error')
        raise exceptions.NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        print('Default StartNotify called, returning error')
        raise exceptions.NotSupportedException()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        print('Default StopNotify called, returning error')
        raise exceptions.NotSupportedException()

    @dbus.service.signal(DBUS_PROP_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass

class Descriptor(dbus.service.Object):
    """
    org.bluez.GattDescriptor1 interface implementation
    """
    def __init__(self, bus, index, uuid, flags, characteristic):
        self.path = characteristic.path + '/desc' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
                GATT_DESC_IFACE: {
                        'Characteristic': self.chrc.get_path(),
                        'UUID': self.uuid,
                        'Flags': self.flags,
                }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_DESC_IFACE:
            raise exceptions.InvalidArgsException()

        return self.get_properties()[GATT_DESC_IFACE]

    @dbus.service.method(GATT_DESC_IFACE,
                        in_signature='a{sv}',
                        out_signature='ay')
    def ReadValue(self, options):
        print('Default ReadValue called, returning error')
        raise exceptions.NotSupportedException()

    @dbus.service.method(GATT_DESC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print('Default WriteValue called, returning error')
        raise exceptions.NotSupportedException()

'''
class HeartRateService(Service):
    """
    Fake Heart Rate Service that simulates a fake heart beat and control point
    behavior.

    """
    HR_UUID = '0000180d-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.HR_UUID, True)
        self.add_characteristic(HeartRateMeasurementChrc(bus, 0, self))
        self.add_characteristic(BodySensorLocationChrc(bus, 1, self))
        self.add_characteristic(HeartRateControlPointChrc(bus, 2, self))
        self.energy_expended = 0

class HeartRateMeasurementChrc(Characteristic):
    HR_MSRMT_UUID = '00002a37-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.HR_MSRMT_UUID,
                ['notify'],
                service)
        self.notifying = False
        self.hr_ee_count = 0

    def hr_msrmt_cb(self):
        value = []
        value.append(dbus.Byte(0x06))

        value.append(dbus.Byte(randint(90, 130)))

        if self.hr_ee_count % 10 == 0:
            value[0] = dbus.Byte(value[0] | 0x08)
            value.append(dbus.Byte(self.service.energy_expended & 0xff))
            value.append(dbus.Byte((self.service.energy_expended >> 8) & 0xff))

        self.service.energy_expended = \
                min(0xffff, self.service.energy_expended + 1)
        self.hr_ee_count += 1

        print('Updating value: ' + repr(value))

        self.PropertiesChanged(GATT_CHRC_IFACE, { 'Value': value }, [])

        return self.notifying

    def _update_hr_msrmt_simulation(self):
        print('Update HR Measurement Simulation')

        if not self.notifying:
            return

        GObject.timeout_add(1000, self.hr_msrmt_cb)

    def StartNotify(self):
        if self.notifying:
            print('Already notifying, nothing to do')
            return

        self.notifying = True
        self._update_hr_msrmt_simulation()

    def StopNotify(self):
        if not self.notifying:
            print('Not notifying, nothing to do')
            return

        self.notifying = False
        self._update_hr_msrmt_simulation()

class BodySensorLocationChrc(Characteristic):
    BODY_SNSR_LOC_UUID = '00002a38-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.BODY_SNSR_LOC_UUID,
                ['read'],
                service)

    def ReadValue(self, options):
        # Return 'Chest' as the sensor location.
        return [ 0x01 ]

class HeartRateControlPointChrc(Characteristic):
    HR_CTRL_PT_UUID = '00002a39-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.HR_CTRL_PT_UUID,
                ['write'],
                service)

    def WriteValue(self, value, options):
        print('Heart Rate Control Point WriteValue called')

        if len(value) != 1:
            raise exceptions.InvalidValueLengthException()

        byte = value[0]
        print('Control Point value: ' + repr(byte))

        if byte != 1:
            raise exceptions.FailedException("0x80")

        print('Energy Expended field reset!')
        self.service.energy_expended = 0
'''

class GenericAccessService(Service):
    """
    Fake Generic Access Service.

    """
    GA_UUID = '00001800-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.GA_UUID, True)
        self.add_characteristic(DeviceNameChrc(bus, 0, self))
        self.add_characteristic(AppearanceChrc(bus, 1, self))
        self.add_characteristic(PeripheralPrivacyFlagChrc(bus, 2, self))
        self.add_characteristic(ReconnectionAddressChrc(bus, 3, self))
        self.add_characteristic(PeripheralPreferredConnectionParametersChrc(bus, 4, self))

class DeviceNameChrc(Characteristic):
    DEVICE_NAME_UUID = '00002a00-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.DEVICE_NAME_UUID,
                ['read'],
                service)

    def ReadValue(self, options):
        print('Device Name Read: ' + repr('PyGATTTS'))
        return ['P', 'y', 'G', 'A', 'T', 'T', 'T']

class AppearanceChrc(Characteristic):
    APPEARANCE_UUID = '00002a01-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.APPEARANCE_UUID,
                ['read'],
                service)

    def ReadValue(self, options):
        # Generic Computer
        print('Appearance Read: ' + repr([0x00, 0x80]))
        return [ dbus.Byte(0x00), dbus.Byte(0x80) ]

class PeripheralPrivacyFlagChrc(Characteristic):
    PERIPHERAL_PRIVACY_FLAG_UUID = '00002a02-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.PERIPHERAL_PRIVACY_FLAG_UUID,
                ['read'],
                service)

    def ReadValue(self, options):
        # Peripheral Privacy Flag is disabled
        print('Peripheral Privacy Flag Read: ' + repr([0x00]))
        return [ dbus.Byte(0x00) ]

class ReconnectionAddressChrc(Characteristic):
    RECONNECTION_ADDRESS_UUID = '00002a03-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.RECONNECTION_ADDRESS_UUID,
                ['read'],
                service)

    def ReadValue(self, options):
        # Reconnection Address is not set
        return [ dbus.Byte(0x00) ] * 6

class PeripheralPreferredConnectionParametersChrc(Characteristic):
    PERIPHERAL_PREFERRED_CONNECTION_PARAMETERS_UUID = '00002a04-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.PERIPHERAL_PREFERRED_CONNECTION_PARAMETERS_UUID,
                ['read'],
                service)

    def ReadValue(self, options):
        # Peripheral Preferred Connection Parameters are not set
        print(  'Peripheral Preferred Connection Parameters Read: ---not set---')
        return [ dbus.Byte(0x00) ] * 8


class GenericAttributeService(Service):
    """
    Fake Generic Attribute Service.

    """
    GA_UUID = '00001801-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.GA_UUID, True)
        self.add_characteristic(ServiceChangedChrc(bus, 0, self))

class ServiceChangedChrc(Characteristic):
    SERVICE_CHANGED_UUID = '00002a05-0000-1000-8000-00805f9b34fb'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.SERVICE_CHANGED_UUID,
                ['indicate'],
                service)

    def StartNotify(self):
        print('Service Changed StartNotify called')

    def StopNotify(self):
        print('Service Changed StopNotify called')


class HidService(Service):
    """
    Fake HID service that emulates a keyboard.

    """
    HID_UUID = '1812'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.HID_UUID, True)
        self.add_characteristic(HidReportMapCharacteristic(bus, 0, self))
        self.add_characteristic(HidInfoCharacteristic(bus, 1, self))
        self.add_characteristic(HidControlPointCharacteristic(bus, 2, self))
        self.add_characteristic(HidReportCharacteristic(bus, 3, self))
        self.add_characteristic(HidProtocolModeCharacteristic(bus, 4, self))

class HidReportMapCharacteristic(Characteristic):
    """
    Fake HID Report Map characteristic.

    """
    HID_REPORT_MAP_UUID = '2a4b'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.HID_REPORT_MAP_UUID,
                ['read'],
                service)

    def ReadValue(self, options):
        print('HID Report Map read')
        # return [dbus.Byte(0x05), dbus.Byte(0x01), dbus.Byte(0x09),
        #         dbus.Byte(0x06), dbus.Byte(0xA1), dbus.Byte(0x01),
        #         dbus.Byte(0x85), dbus.Byte(0x01), dbus.Byte(0x05),
        #         dbus.Byte(0x07), dbus.Byte(0x19), dbus.Byte(0xE0),
        #         dbus.Byte(0x29), dbus.Byte(0xE7), dbus.Byte(0x15),
        #         dbus.Byte(0x00), dbus.Byte(0x25), dbus.Byte(0x01),
        #         dbus.Byte(0x75), dbus.Byte(0x01), dbus.Byte(0x95),
        #         dbus.Byte(0x08), dbus.Byte(0x81), dbus.Byte(0x02),
        #         dbus.Byte(0x95), dbus.Byte(0x01), dbus.Byte(0x75),
        #         dbus.Byte(0x08), dbus.Byte(0x81), dbus.Byte(0x01),
        #         dbus.Byte(0x95), dbus.Byte(0x05), dbus.Byte(0x75),
        #         dbus.Byte(0x01), dbus.Byte(0x05), dbus.Byte(0x08),
        #         dbus.Byte(0x19), dbus.Byte(0x01), dbus.Byte(0x29),
        #         dbus.Byte(0x05), dbus.Byte(0x91), dbus.Byte(0x02),
        #         dbus.Byte(0x95), dbus.Byte(0x01), dbus.Byte(0x75),
        #         dbus.Byte(0x03), dbus.Byte(0x91), dbus.Byte(0x01),
        #         dbus.Byte(0x95), dbus.Byte(0x06), dbus.Byte(0x75),
        #         dbus.Byte(0x08), dbus.Byte(0x15), dbus.Byte(0x00),
        #         dbus.Byte(0x25), dbus.Byte(0x65), dbus.Byte(0x05),
        #         dbus.Byte(0x07), dbus.Byte(0x19), dbus.Byte(0x00),
        #         dbus.Byte(0x29), dbus.Byte(0x65), dbus.Byte(0x81),
        #         dbus.Byte(0x00), dbus.Byte(0xC0)]








        return [dbus.Byte(0x05), dbus.Byte(0x01), dbus.Byte(0x09),
                dbus.Byte(0x06), dbus.Byte(0xA1), dbus.Byte(0x01),
                dbus.Byte(0x85), dbus.Byte(0x01), dbus.Byte(0x05),
                dbus.Byte(0x07), dbus.Byte(0x19), dbus.Byte(0xE0),
                dbus.Byte(0x29), dbus.Byte(0xE7), dbus.Byte(0x15),
                dbus.Byte(0x00), dbus.Byte(0x25), dbus.Byte(0x01),
                dbus.Byte(0x75), dbus.Byte(0x01), dbus.Byte(0x95),
                dbus.Byte(0x08), dbus.Byte(0xc0)]

class HidInfoCharacteristic(Characteristic):
    """
    HID Info characteristic.

    """
    HID_INFO_UUID = '2a4a'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.HID_INFO_UUID,
                ['read'],
                service)

    def ReadValue(self, options):
        print('HID Info read')
        return [dbus.Byte(0x01), dbus.Byte(0x01), dbus.Byte(0x00),
                dbus.Byte(0x03)]

class HidControlPointCharacteristic(Characteristic):
    """
    HID Control Point characteristic.

    """
    HID_CONTROL_POINT_UUID = '2a4c'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.HID_CONTROL_POINT_UUID,
                ['write'],
                service)

    def WriteValue(self, value, options):
        print('HID Control Point write: ' + repr(value))
        byte = value[0]
        print('Control Point value: ' + repr(byte))

        if byte != 1:
            raise exceptions.FailedException("0x80")

        print('Suspend command received!')

class HidReportCharacteristic(Characteristic):
    """
    HID Report characteristic.

    """
    HID_REPORT_UUID = '2a4d'

    A_VALUE = [ dbus.Byte(0x02), dbus.Byte(0x00), dbus.Byte(0x08),
                dbus.Byte(0x00), dbus.Byte(0x00), dbus.Byte(0x00),
                dbus.Byte(0x00), dbus.Byte(0x00)]

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.HID_REPORT_UUID,
                ['read', 'notify'],
                service)
        self.notifying = False
        self.key_pressed = 'a'
        print("HidReportCharacteristic init")
        GObject.timeout_add(5000, self.change_letter)

    def change_letter(self):
        print("change_letter")

        self.key_pressed = chr(ord(self.key_pressed) + 1)
        if self.key_pressed > 'z':
            self.key_pressed = 'a'

        self.notify_key_pressed()
        return True

    def notify_key_pressed(self):
        if not self.notifying:
            return
        print('notify_key_pressed: ' + self.key_pressed)

        # value = [dbus.Byte(0x02), dbus.Byte(0x00), dbus.Byte(0x00),
        #          dbus.Byte(0x00), dbus.Byte(0x00), dbus.Byte(0x00),
        #          dbus.Byte(0x00), dbus.Byte(0x00)]
        # value[2] = dbus.Byte(ord(self.key_pressed))

        self.PropertiesChanged(
            GATT_CHRC_IFACE,
            {'Value': A_VALUE }, [])

    def ReadValue(self, options):
        print('Letter read: ' + (self.key_pressed))
        return A_VALUE

    def StartNotify(self):
        if self.notifying:
            print('Already notifying, nothing to do')
            return

        self.notifying = True

    def StopNotify(self):
        if not self.notifying:
            print('Not notifying, nothing to do')
            return

        self.notifying = False

class HidProtocolModeCharacteristic(Characteristic):
    """
    Fake HID Protocol Mode characteristic.

    """
    HID_PROTOCOL_MODE_UUID = '2a4e'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.HID_PROTOCOL_MODE_UUID,
                ['read', 'write'],
                service)

    def ReadValue(self, options):
        print('HID Protocol Mode read')
        return [dbus.Byte(0x01)]

    def WriteValue(self, value, options):
        print('HID Protocol Mode write: ' + repr(value))
        byte = value[0]
        print('Protocol Mode value: ' + repr(byte))

        if byte != 0 and byte != 1:
            raise exceptions.FailedException("0x80")

        print('Protocol Mode changed to ' + repr(byte))


class BatteryService(Service):
    """
    Fake Battery service that emulates a draining battery.

    """
    BATTERY_UUID = '180f'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.BATTERY_UUID, True)
        self.add_characteristic(BatteryLevelCharacteristic(bus, 0, self))


class BatteryLevelCharacteristic(Characteristic):
    """
    Fake Battery Level characteristic. The battery level is drained by 2 points
    every 5 seconds.

    """
    BATTERY_LVL_UUID = '2a19'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.BATTERY_LVL_UUID,
                ['read', 'notify'],
                service)
        self.notifying = False
        self.battery_lvl = 100
        GObject.timeout_add(5000, self.drain_battery)

    def notify_battery_level(self):
        if not self.notifying:
            return
        self.PropertiesChanged(
                GATT_CHRC_IFACE,
                {'Value': [dbus.Byte(self.battery_lvl)] }, [])

    def drain_battery(self):
        if self.battery_lvl >= 0:
            self.battery_lvl -= 2
            if self.battery_lvl < 0:
                self.battery_lvl = 100
        print('Battery level: ' + repr(self.battery_lvl))
        self.notify_battery_level()
        return True

    def ReadValue(self, options):
        print('Battery level read: ' + repr(self.battery_lvl))
        return [dbus.Byte(self.battery_lvl)]

    def StartNotify(self):
        if self.notifying:
            print('Already notifying, nothing to do')
            return

        self.notifying = True
        self.notify_battery_level()

    def StopNotify(self):
        if not self.notifying:
            print('Not notifying, nothing to do')
            return

        self.notifying = False


class TestService(Service):
    """
    Dummy test service that provides characteristics and descriptors that
    exercise various API functionality.

    """
    TEST_SVC_UUID = '12345678-1234-5678-1234-56789abcdef0'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.TEST_SVC_UUID, True)
        self.add_characteristic(TestCharacteristic(bus, 0, self))
        self.add_characteristic(TestEncryptCharacteristic(bus, 1, self))
        self.add_characteristic(TestSecureCharacteristic(bus, 2, self))

class TestCharacteristic(Characteristic):
    """
    Dummy test characteristic. Allows writing arbitrary bytes to its value, and
    contains "extended properties", as well as a test descriptor.

    """
    TEST_CHRC_UUID = '12345678-1234-5678-1234-56789abcdef1'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.TEST_CHRC_UUID,
                ['read', 'write', 'writable-auxiliaries'],
                service)
        self.value = []
        self.add_descriptor(TestDescriptor(bus, 0, self))
        self.add_descriptor(
                CharacteristicUserDescriptionDescriptor(bus, 1, self))

    def ReadValue(self, options):
        print('TestCharacteristic Read: ' + repr(self.value))
        return self.value

    def WriteValue(self, value, options):
        print('TestCharacteristic Write: ' + repr(value))
        self.value = value

class TestDescriptor(Descriptor):
    """
    Dummy test descriptor. Returns a static value.

    """
    TEST_DESC_UUID = '12345678-1234-5678-1234-56789abcdef2'

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
                self, bus, index,
                self.TEST_DESC_UUID,
                ['read', 'write'],
                characteristic)

    def ReadValue(self, options):
        return [
                dbus.Byte('T'), dbus.Byte('e'), dbus.Byte('s'), dbus.Byte('t')
        ]

class CharacteristicUserDescriptionDescriptor(Descriptor):
    """
    Writable CUD descriptor.

    """
    CUD_UUID = '2901'

    def __init__(self, bus, index, characteristic):
        self.writable = 'writable-auxiliaries' in characteristic.flags
        self.value = array.array('B', b'This is a characteristic for testing')
        self.value = self.value.tolist()
        Descriptor.__init__(
                self, bus, index,
                self.CUD_UUID,
                ['read', 'write'],
                characteristic)

    def ReadValue(self, options):
        return self.value

    def WriteValue(self, value, options):
        if not self.writable:
            raise exceptions.NotPermittedException()
        self.value = value

class TestEncryptCharacteristic(Characteristic):
    """
    Dummy test characteristic requiring encryption.

    """
    TEST_CHRC_UUID = '12345678-1234-5678-1234-56789abcdef3'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.TEST_CHRC_UUID,
                ['encrypt-read', 'encrypt-write'],
                service)
        self.value = []
        self.add_descriptor(TestEncryptDescriptor(bus, 2, self))
        self.add_descriptor(
                CharacteristicUserDescriptionDescriptor(bus, 3, self))

    def ReadValue(self, options):
        print('TestEncryptCharacteristic Read: ' + repr(self.value))
        return self.value

    def WriteValue(self, value, options):
        print('TestEncryptCharacteristic Write: ' + repr(value))
        self.value = value

class TestEncryptDescriptor(Descriptor):
    """
    Dummy test descriptor requiring encryption. Returns a static value.

    """
    TEST_DESC_UUID = '12345678-1234-5678-1234-56789abcdef4'

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
                self, bus, index,
                self.TEST_DESC_UUID,
                ['encrypt-read', 'encrypt-write'],
                characteristic)

    def ReadValue(self, options):
        return [
                dbus.Byte('T'), dbus.Byte('e'), dbus.Byte('s'), dbus.Byte('t')
        ]

class TestSecureCharacteristic(Characteristic):
    """
    Dummy test characteristic requiring secure connection.

    """
    TEST_CHRC_UUID = '12345678-1234-5678-1234-56789abcdef5'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.TEST_CHRC_UUID,
                ['secure-read', 'secure-write'],
                service)
        self.value = []
        self.add_descriptor(TestSecureDescriptor(bus, 2, self))
        self.add_descriptor(
                CharacteristicUserDescriptionDescriptor(bus, 3, self))

    def ReadValue(self, options):
        print('TestSecureCharacteristic Read: ' + repr(self.value))
        return self.value

    def WriteValue(self, value, options):
        print('TestSecureCharacteristic Write: ' + repr(value))
        self.value = value

class TestSecureDescriptor(Descriptor):
    """
    Dummy test descriptor requiring secure connection. Returns a static value.

    """
    TEST_DESC_UUID = '12345678-1234-5678-1234-56789abcdef6'

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
                self, bus, index,
                self.TEST_DESC_UUID,
                ['secure-read', 'secure-write'],
                characteristic)

    def ReadValue(self, options):
        return [
                dbus.Byte('T'), dbus.Byte('e'), dbus.Byte('s'), dbus.Byte('t')
        ]

def register_app_cb():
    print('GATT application registered')

def register_app_error_cb(mainloop, error):
    print('Failed to register application: ' + str(error))
    mainloop.quit()

def gatt_server_main(mainloop, bus, adapter_name):
    adapter = adapters.find_adapter(bus, GATT_MANAGER_IFACE, adapter_name)
    if not adapter:
        raise Exception('GattManager1 interface not found')

    service_manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, adapter),
            GATT_MANAGER_IFACE)

    app = Application(bus)

    print('Registering GATT application...')

    service_manager.RegisterApplication(app.get_path(), {},
                                    reply_handler=register_app_cb,
                                    error_handler=functools.partial(register_app_error_cb, mainloop))

