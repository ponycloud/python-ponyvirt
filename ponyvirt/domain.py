from xml.etree.ElementTree import XML
from libvirt import *

class PonyvirtError(Exception):
    pass

class NoDomainError(PonyvirtError):
    """vyhazovana, kdyz zmizne domena kterou proxynuje Domain"""

class InvalidOperationError(PonyvirtError):
    """prevedena z VIR_ERR_OPERATION_INVALID vyjimek"""


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

    @convert_exception_type
    def info(self):
        return self.domain.info()

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
        pass

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