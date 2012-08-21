#!/usr/bin/python -tt

import sys

__all__ = ['Hypervisor']

import libvirt
import os
from domain import Domain, NoDomainError
from virtxmlbuilder import *
from xml.etree.ElementTree import ElementTree, tostring, XML

def disk_id_generator(offset=0):
    for i in xrange(26):
        yield 'vd' + chr(ord('a') + i + offset)

class Hypervisor(object):
    def __init__(self, connection_string='qemu:///system'):
        '''
        Connection string example qemu:///system
        '''
        self.conn = libvirt.open(connection_string)
        e = ElementTree()
        self._features = e.parse('/usr/share/libvirt/cpu_map.xml')

        self.capabilities = self._get_capabilities()
        self.sysinfo = self._get_sys_info()

    def __len__(self):
        return self.conn.numOfDomains() + self.conn.numOfDefinedDomains()

    def __contains__(self, index):
        try:
            self[index]
        except NoDomainError, e:
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
                raise NoDomainError()
            else:
                raise
        return Domain(dom)

    def __iter__(self):
        domainlist = []
        for id in self.conn.listDomainsID():
            try:
                domainlist.append(self[id].name)
            except NoDomainError:
                pass
        return iter(domainlist)

    def __delitem__(self, item):
        self[item].delete()





    def _list_features(self, model):
        features = [element.attrib['name'] for element in self._features.findall('arch/model[@name="' + model + '"]/feature')]
        parent = self._features.find('arch/model[@name="' + model + '"]/model')
        if parent is not None:
            features.extend(self._list_features(parent.attrib['name']))
        return features




    def _get_capabilities(self):
        xml = XML(self.conn.getCapabilities())
        capabilities = {
            'canonical': xml.find('guest/arch[@name="x86_64"]/machine[@canonical]').attrib['canonical'],
            'topology': {k: int(v) for k, v in xml.find('host/cpu/topology').attrib.items()},
            'model': xml.find('host/cpu/model').text,
            'toggleable': [e.tag for e in xml.findall('guest/arch[@name="x86_64"]/../features/*[@toggle]')],
        }

        features = [element.attrib['name'] for element in self._features.findall('host/cpu/feature')]
        features.extend(self._list_features(capabilities['model']))

        capabilities['features'] = features

        return capabilities

    def _get_sys_info(self):
        """
        Returns sysinfo of host system in the following format::
            {'memory': [{'bank_locator': 'BANK 0',
                         'form_factor': 'SODIMM',
                         'locator': 'ChannelA-DIMM0',
                         'manufacturer': 'Samsung',
                         'part_number': 'M471B5273DH0-CK0',
                         'serial_number': '9760E90B',
                         'size': '4096 MB',
                         'speed': '1600 MHz',
                         'type': 'DDR3',
                         'type_detail': 'Synchronous'},
                        {'bank_locator': 'BANK 2',
                         'form_factor': 'SODIMM',
                         'locator': 'ChannelB-DIMM0',
                         'manufacturer': 'Micron',
                         'part_number': '16KTF51264HZ-1G6M1',
                         'serial_number': '3255C613',
                         'size': '4096 MB',
                         'speed': '1600 MHz',
                         'type': 'DDR3',
                         'type_detail': 'Synchronous'}],
             'processor': {'external_clock': '100 MHz',
                           'family': 'Core i5',
                           'manufacturer': 'Intel(R) Corporation',
                           'max_speed': '2600 MHz',
                           'part_number': 'None',
                           'serial_number': 'None',
                           'signature': 'Type 0, Family 6, Model 58, Stepping 9',
                           'socket_destination': 'CPU Socket - U3E1',
                           'status': 'Populated, Enabled',
                           'type': 'Central Processor',
                           'version': 'Intel(R) Core(TM) i5-3320M CPU @ 2.60GHz'},
             'system': {'family': 'ThinkPad T430',
                        'manufacturer': 'LENOVO',
                        'product': '234455G',
                        'serial': 'PBKVYA6',
                        'sku': 'LENOVO_MT_2344',
                        'uuid': 'D6A27701-51F5-11CB-963F-F8A34AA11505',
                        'version': 'ThinkPad T430'}}

        """
        xml = XML(self.conn.getSysinfo(0))
        sysinfo = {}
        keys = ['system', 'processor']
        for key in keys:
            sysinfo[key] = {}
            for element in xml.findall(key+'/entry'):
                sysinfo[key][element.attrib['name']] = element.text

        sysinfo['memory'] = []
        for memorydevs in xml.findall('memory_device'):
            x = {}
            for entry in memorydevs.findall('entry'):
                x[entry.attrib['name']] = entry.text
            sysinfo['memory'].append(x)
        return sysinfo


    def close(self):
        self.conn.close()

    def create(self, name, uuid, memory=256, vcpu=1, disks=[], vifs=[]):
        '''
        Creates new domain.

        Disks are something like::
            [
                {
                    'type':   'network',
                    'device': 'disk',
                    'format': 'raw',
                    'source': {
                        'protocol': 'sheepdog',
                        'name': 'Alice',
                        'hosts': [('127.0.0.1', '7000'),],
                    },
                },
                {
                    'type':   'file',
                    'device': 'disk',
                    'format': 'qcow2',
                    'source': {
                        'file': '/var/lib/libvirt/images/Alice.img',
                    },
                },
            ]

        Virtual interfaces::
            [
                {
                    'type': 'bridge',
                    'mac': 'fa:16:3e:73:3b:f8',
                    'source': {'bridge': 'br100'},
                }
            ]
        '''
        tmp_vm = ElementTree(
            file=os.path.dirname(__file__) + '/templates/vm.xml')

        tmp_vm.find('name').text = name
        tmp_vm.find('uuid').text = uuid
        tmp_vm.find('memory').text = str(memory)
        tmp_vm.find('vcpu').text = str(vcpu)

        diskseq = disk_id_generator()

        for disk in disks:
            tmp_vm.find('devices').append(generate_disk(disk, next(diskseq)))

        for network in vifs:
            tmp_vm.find('devices').append(generate_nic(network))
        self.conn.defineXML(tostring(tmp_vm.getroot()))


if __name__ == '__main__':
    h = Hypervisor()
    h.create('Testicek', 'd56f7b2c-e531-405f-8fb1-e37764970231',
        disks=[{
            'type': 'file',
            'device': 'disk',
            'format': 'raw',
            'source': {
                'file': '/var/lib/libvirt/images/Test.img',
                },
            }, ],
        vifs=[{
            'type': 'bridge',
            'mac': 'fa:16:3e:73:3b:f8',
            'source': {'bridge': 'virbr0'},
            }])
    d = h['Testicek'].attach_disk({
        'type': 'file',
        'device': 'disk',
        'format': 'raw',
        'source': {
            'file': '/var/lib/libvirt/images/FFF.img',
            },
        })
    print >>sys.stdout, "Press any key to detach volume..."
    sys.stdin.readline()
    h['Testicek'].detach_disk(h['Testicek'].get_disks()[-1])



# vim:set sw=4 ts=4 et:
# -*- coding: utf-8 -*-