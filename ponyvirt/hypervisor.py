import libvirt
from ponyvirt.domain import Domain

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

    def create(self):
        pass

    def __del__(self, item):
        self[item].delete()


if __name__ == "__main__":
    h = Hypervisor()
    print h
