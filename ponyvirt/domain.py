from xml.etree.ElementTree import XML, tostring
from ponyvirt.virtxmlbuilder import *
from libvirt import *

class PonyvirtError(Exception):
    pass


class NoDomainError(PonyvirtError):
    """vyhazovana, kdyz zmizne domena kterou proxynuje Domain"""


class InvalidOperationError(PonyvirtError):
    """prevedena z VIR_ERR_OPERATION_INVALID vyjimek"""


class TooManyDisksError(Exception):
    pass


def convert_exception_type(function):
    def convert(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except libvirtError, error:
            if error.get_error_code() == VIR_ERR_OPERATION_INVALID:
                raise InvalidOperationError()
            elif error.get_error_code() == VIR_ERR_NO_DOMAIN:
                raise NoDomainError()
            else:
                raise

    return convert


class Domain(object):
    NOSTATE = VIR_DOMAIN_NOSTATE
    RUNNING = VIR_DOMAIN_RUNNING
    BLOCKED = VIR_DOMAIN_BLOCKED
    PAUSED = VIR_DOMAIN_PAUSED
    SHUTDOWN = VIR_DOMAIN_SHUTDOWN
    SHUTOFF = VIR_DOMAIN_SHUTOFF
    CRASHED = VIR_DOMAIN_CRASHED
    PMSUSPENDED = VIR_DOMAIN_PMSUSPENDED

    def __init__(self, libvirt_domain):
        self.domain = libvirt_domain
        all_names = set(['vd' + chr(x) for x in xrange(ord('a'), ord('z') + 1)])
        self.drive_names = sorted(all_names - self.used_names)

    @convert_exception_type
    def info(self):
        return self.domain.info()

    @property
    def used_names(self):
        return set([x.attrib['dev'] for x in
                    XML(self.domain.XMLDesc(0)).findall(
                        'devices/disk[@device="disk"]/target')])

    def _allocate_disk_name(self):
        if len(self.drive_names) == 0:
            raise TooManyDisksError()
        return self.drive_names.pop(0)

    @property
    @convert_exception_type
    def name(self):
        return self.domain.name()

    @property
    def state(self):
        try:
            return self.info()[0]
        except libvirtError, e:
            if e.get_error_code() == VIR_ERR_NO_DOMAIN:
                return self.NOSTATE
            else:
                raise

    @property
    @convert_exception_type
    def active(self):
        return self.state in (self.RUNNING, self.SHUTDOWN,
                              self.PAUSED, self.BLOCKED)

    @convert_exception_type
    def shutdown(self):
        """sends shutdown request to the domain"""
        self.domain.shutdown()

    @convert_exception_type
    def destroy(self):
        """immediately destroy the domain (as in hard shutdown)"""
        self.domain.destroy()

    @convert_exception_type
    def start(self):
        """start the domain"""
        self.domain.create()

    @convert_exception_type
    def suspend(self):
        """suspend the domain"""
        self.domain.suspend()

    @convert_exception_type
    def resume(self):
        """resume the domain"""
        self.domain.resume()

    @convert_exception_type
    def get_console_device(self):
        """returns console device"""
        xml = XML(self.domain.XMLDesc(0))
        return xml.find('devices/console[@type="pty"]').attrib['tty']

    @convert_exception_type
    def get_vnc_port(self):
        """returns VNC port number"""
        xml = XML(self.domain.XMLDesc(0))
        return int(xml.find('devices/graphics[@type="vnc"]').attrib['port'])

    @convert_exception_type
    def delete(self):
        try:
            self.destroy()
        except libvirtError, error:
            if error.get_error_code() != VIR_ERR_OPERATION_INVALID:
                raise
        self.domain.undefine()

    @convert_exception_type
    def get_disks(self):
        xml = XML(self.domain.XMLDesc(0))
        disks = []

        for disk in xml.findall('devices/disk'):
            disk_definition = disk.attrib
            disk_definition['format'] = disk.find('driver').attrib['type']
            disk_definition['target'] = disk.find('target').attrib['dev']
            disk_definition['source'] = disk.find('source').attrib
            hosts = disk.findall('source/host')

            if len(hosts):
                disk_definition['source']['hosts'] = []
                for host in hosts:
                    disk_definition['source']['hosts'].append(
                        (host.attrib['name'], host.attrib['port'])
                    )
            disks.append(disk_definition)
        return disks


    @convert_exception_type
    def attach_disk(self, disk_definition):
        self.domain.attachDeviceFlags(
            tostring(generate_disk(disk_definition, self._allocate_disk_name())),VIR_DOMAIN_AFFECT_CURRENT)

    @convert_exception_type
    def detach_disk(self, disk_definition):
        self.domain.detachDeviceFlags(
            tostring(generate_disk(disk_definition, disk_definition['target'])), VIR_DOMAIN_AFFECT_CURRENT)
        self.drive_names.append(disk_definition['target'])
