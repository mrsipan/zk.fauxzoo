import mock
import time

class Faux:

    def __init__(self, server):
        pass

    def __enter__(self):
        self.patch = mock.patch('kazoo.client.KazooClient',
                                side_effect = KazooClient)
        self.patch.__enter__()

    start = __enter__

    def __exit__(self, *args):
        self.patch.__exit__(*args)

    def stop(self):
        self.__exit__(None, None, None)

class KazooClient:

    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.root = Node()

    def start(self):
        pass

    def stop(self):
        pass

    def get_children(self, path):
        return []


class Node:
    watchers = child_watchers = exists_watchers = ()
    flags = 0
    version = aversion = cversion = 0
    #acl = zc.zk.OPEN_ACL_UNSAFE

    def meta(self):
        return dict(
            version = self.version,
            aversion = self.aversion,
            cversion = self.cversion,
            ctime = self.ctime,
            mtime = self.mtime,
            numChildren = len(self.children),
            dataLength = len(self.data),
            ephemeralOwner=(1 if self.flags & zookeeper.EPHEMERAL else 0),
            )

    def __init__(self, data='', **children):
        self.data = data
        self.children = children
        self.ctime = self.mtime = time.time()

    def children_changed(self, handle, state, path):
        watchers = self.child_watchers
        self.child_watchers = ()
        for h, w in watchers:
            w(h, zookeeper.CHILD_EVENT, state, path)
        self.cversion += 1

    def changed(self, handle, state, path):
        watchers = self.watchers
        self.watchers = ()
        for h, w in watchers:
            w(h, zookeeper.CHANGED_EVENT, state, path)
        self.version += 1
        self.mtime = time.time()

    def deleted(self, handle, state, path):
        watchers = self.watchers
        self.watchers = ()
        for h, w in watchers:
            w(h, zookeeper.DELETED_EVENT, state, path)
        watchers = self.exists_watchers
        self.exists_watchers = ()
        for h, w in watchers:
            w(h, zookeeper.DELETED_EVENT, state, path)
        watchers = self.child_watchers
        self.watchers = ()
        for h, w in watchers:
            w(h, zookeeper.DELETED_EVENT, state, path)

    def session_event(self, handle, state):
        for (h, w) in self.watchers:
            if h == handle:
                w(h, zookeeper.SESSION_EVENT, state, '')
        for (h, w) in self.child_watchers:
            if h == handle:
                w(h, zookeeper.SESSION_EVENT, state, '')
        for (h, w) in self.exists_watchers:
            if h == handle:
                w(h, zookeeper.SESSION_EVENT, state, '')
        for child in self.children.values():
            child.session_event(handle, state)

    def clear_watchers(self, handle):
        self.watchers = tuple(
            (h, w) for (h, w) in self.watchers
            if h != handle
            )
        self.child_watchers = tuple(
            (h, w) for (h, w) in self.child_watchers
            if h != handle
            )
        self.exists_watchers = tuple(
            (h, w) for (h, w) in self.exists_watchers
            if h != handle
            )
        for name, child in self.children.items():
            child.clear_watchers(handle)
