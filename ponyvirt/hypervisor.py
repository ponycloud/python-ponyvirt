#!/usr/bin/python -tt

import sys

__all__ = ['Hypervisor']

import libvirt
import os
from ponyvirt.domain import Domain
from ponyvirt.virtxmlbuilder import *
from xml.etree.ElementTree import ElementTree, tostring

def disk_id_generator(offset=0):
    for i in xrange(26):
        yield 'vd' + chr(ord('a') + i + offset)

class Hypervisor(object):
    def __init__(self, connection_string='qemu:///system'):
        '''
        Connection string example qemu:///system
        '''
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

    def __delitem__(self, item):
        self[item].delete()

    def close(self):
        self.conn.close()

    def create(self, name, uuid, memory=256, vcpu=1, disks=[], vifs=[]):
        '''
        Creates new domain.

        Disks are something like:

            [
                {
                    'type': 'network',
                    'device': 'disk',
                    'format': 'raw',
                    'source': {
                        'protocol': 'sheepdog',
                        'name': 'Alice',
                        'hosts': [('127.0.0.1', '7000'),],
                    },
                },
                {
                    'type': 'file',
                    'device': 'disk',
                    'format': 'qcow2',
                    'source': {
                        'file': '/var/lib/libvirt/images/Alice.img',
                    },
                },
            ]

        Virtual interfaces:
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