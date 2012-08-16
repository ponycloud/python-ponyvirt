#!/usr/bin/python -tt

from xml.etree.ElementTree import TreeBuilder

__all__ = ['generate_disk', 'generate_nic']

def sans(d, *items):
    d = d.copy()
    for i in items:
        if i in d:
            del d[i]
    return d

def generate_disk(disk, devicename):
    """
    Creates XML representation of disk for libvirt based on disk_definition

    disk_definition is something like
            {
                'type': 'network',
                'device': 'disk',
                'format': 'raw',
                'source': {
                    'protocol': 'sheepdog',
                    'name': 'Alice',
                    'hosts': [('127.0.0.1', '7000'),],
                },
            }
     or
             {
                'type': 'file',
                'device': 'disk',
                'format': 'qcow2',
                'source': {
                    'file': '/var/lib/libvirt/images/Alice.img',
                },
            },

    devicename is string representing devicename (eg. vda, vdb, ...)
    """

    builder = TreeBuilder()
    builder.start('disk',
                {'type': disk['type'], 'device': disk['device']})
    builder.start('source', sans(disk['source'], 'hosts'))
    for host in disk['source'].get('hosts', []):
        builder.start('host', {'name': host[0], 'port': host[1]})
        builder.end('host')
    builder.end('source')
    builder.start('target', {'dev': devicename, 'bus': 'virtio'})
    builder.end('target')
    builder.start('driver', {'name': 'qemu', 'cache': 'none', 'type': disk['format']})
    builder.end('driver')
    builder.end('disk')
    return builder.close()


def generate_nic(network):
    builder = TreeBuilder()
    builder.start('interface', {'type': network['type']})
    builder.start('mac', {'address': network['mac']})
    builder.end('mac')
    builder.start('source', network['source'])
    builder.end('source')
    builder.start('model', {'type':'virtio'})
    builder.end('model')
    builder.end('interface')
    return builder.close()

# vim:set sw=4 ts=4 et:
# -*- coding: utf-8 -*-