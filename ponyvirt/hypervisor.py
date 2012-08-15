import libvirt
import os
from ponyvirt.domain import Domain
from xml.etree.ElementTree import ElementTree, Element, XML, tostring


def disk_id_generator():
    for i in xrange(26):
        yield 'vd' + chr(ord('a') + i)

class Hypervisor(object):
    def __init__(self, connection_string="qemu:///system"):
        """
        Connection string example qemu:///system
        """
        self.conn = libvirt.open(connection_string)

    def __len__(self):
        return self.conn.numOfDomains() + self.conn.numOfDefinedDomains()

    def __contains__(self, index):
        try:
            self.__getitem__(index)
        except KeyError, e:
            return False
        return True

    def __getitem__(self, item):
        try:
            if isinstance(item, int):
                dom = self.conn.lookupByID(item)
            else:
                dom = self.conn.lookupByName(item)
        except libvirt.libvirtError, e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                raise KeyError()
            else:
                raise
        return Domain(dom)

    def __iter__(self):
        domainlist = []
        for id in self.conn.listDomainsID():
            try:
                domainlist.append(self[id].name)
            except KeyError:
                pass
        return iter(domainlist)

    def close(self):
        self.conn.close()

    def create(self, name, uuid, memory=256, vcpu=1, disks=[], vifs=[]):
        """
        Creates new domain.

        Disks are something like:
            [
                ('network', 'raw', 'sheepdog', 'vm:alice:root'),
                ('network', 'raw', 'sheepdog', 'vm:alice:eph'),
            ]

        Virtual interfaces:
            [
                ('br100', 'fa:16:3e:73:3b:f8'),
            ]
        """
        tmp_vm = ElementTree(
            file=os.path.dirname(__file__) + "/templates/vm.xml")

        tmp_vm.find("name").text = name
        tmp_vm.find("uuid").text = uuid
        tmp_vm.find("memory").text = str(memory)
        tmp_vm.find("vcpu").text = str(vcpu)

        diskseq = disk_id_generator()
        for disk in disks:
            tmp_disk = ElementTree(
                file = os.path.dirname(__file__) + "/templates/disk.xml")
            tmp_disk.getroot().attrib['type'] = disk[0]
            tmp_disk.find("driver").attrib['type'] = disk[1]
            tmp_disk.find("source").attrib['protocol'] = disk[2]
            tmp_disk.find("source").attrib['name'] = disk[3]
            tmp_disk.find("target").attrib['dev'] = next(diskseq)
            tmp_vm.find("devices").append(tmp_disk.getroot())
        for network in vifs:
            tmp_net = ElementTree(
                file=os.path.dirname(__file__) + "/templates/network.xml")
            tmp_net.find("source").attrib["bridge"] = network[0]
            tmp_net.find("mac").attrib["address"] = network[1]
            tmp_vm.find("devices").append(tmp_net.getroot())
        self.conn.createXML(tostring(tmp_vm.getroot()), 0)


def __del__(self, item):
    self[item].delete()


if __name__ == "__main__":
    h = Hypervisor()
    h.create("Testicek", "d56f7b2c-e531-405f-8fb1-e37764970231",
        disks=[('network', 'raw', 'sheepdog', 'vm:alice:root'),
            ('network', 'raw', 'sheepdog', 'vm:alice:eph')],
        vifs=[('virbr0', 'fa:16:3e:73:3b:f8')])
