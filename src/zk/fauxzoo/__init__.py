import kazoo.exceptions
import mock
import re
import threading
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

badpath = re.compile(r'(^([^/]|$))|(/\.\.?(/|$))|(./$)').search

class KazooClient:

    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.root = Node()
        self.lock = threading.RLock()

    def start(self):
        pass

    def stop(self):
        pass

    def create(self, path, data, acl=None,
               ephemeral=False, sequence=False, makepath=False):
        path = unicode(path)
        with self.lock:
            base, name = path.rsplit('/', 1)
            # if flags & zookeeper.SEQUENCE:
            #     self.sequence_number += 1
            #     name += "%.10d" % self.sequence_number
            #     path = base + '/' + name
            # if base.endswith('/'):
            #     raise zookeeper.BadArgumentsException('bad arguments')
            node = self._traverse(base or '/')
            # for p in node.acl:
            #     if not (p['perms'] & zookeeper.PERM_CREATE):
            #         raise zookeeper.NoAuthException('not authenticated')
            # if name in node.children:
            #     raise zookeeper.NodeExistsException()
            node.children[name] = newnode = Node(data)
            # newnode.acl = acl
            # newnode.flags = flags
            # node.children_changed(zookeeper.CONNECTED_STATE, base)

            # for h, w in self.exists_watchers.pop(path, ()):
            #     w(h, zookeeper.CREATED_EVENT, zookeeper.CONNECTED_STATE, path)

            # if flags & zookeeper.EPHEMERAL:
            #     self.sessions[handle].add(path)
            return path
 
    def get(self, path, watch=None):
        with self.lock:
            node = self._traverse(path)
            # for p in node.acl:
            #     if not (p['perms'] & zookeeper.PERM_READ):
            #         raise zookeeper.NoAuthException('not authenticated')
            if watch:
                node.watchers += ((handle, watch), )
            return node.data, node.meta()

    def get_children(self, path, watch=None):
        with self.lock:
            node = self._traverse(path)
            # for p in node.acl:
            #     if not (p['perms'] & zookeeper.PERM_READ):
            #         raise zookeeper.NoAuthException('not authenticated')
            if watch:
                node.child_watchers += ((handle, watch), )
            return list(node.children)

    def ensure_path(self, path):
        base = ''
        for p in path[1:].split('/'):
            base += '/' + p
            if not self.exists(base):
                self.create(base, '')


    def exists(self, path, watch=None):
        """Test whether a node exists:

        >>> zk = zc.zk.ZK('zookeeper.example.com:2181')
        >>> zk.exists('/test_exists')

        We can set watches:

        >>> def watch(*args):
        ...     print args

        >>> zk.exists('/test_exists', watch)
        >>> _ = zk.create('/test_exists', '', zc.zk.OPEN_ACL_UNSAFE)
        (0, 1, 3, '/test_exists')

        When a node exists, exists retirnes it's meta data, which is
        the same as the second result from get:

        >>> zk.exists('/test_exists') == zk.get('/test_exists')[1]
        True

        We can set watches on nodes that exist, too:

        >>> zk.exists('/test_exists', watch) == zk.get('/test_exists')[1]
        True

        >>> _ = zk.delete('/test_exists')
        (0, 2, 3, '/test_exists')

        Watches are one-time:

        >>> _ = zk.create('/test_exists', '', zc.zk.OPEN_ACL_UNSAFE)
        >>> _ = zk.delete('/test_exists')

        >>> zk.close()
        """
        with self.lock:
            try:
                node = self._traverse(path)
                if watch:
                    node.exists_watchers += ((handle, watch), )
                return node.meta()
            except kazoo.exceptions.NoNodeError:
                if watch:
                    self.exists_watchers[path] += ((handle, watch), )
                return None


    def _traverse(self, path):
        """This is used by a bunch of the methods.

        We'll test som edge cases here.

        We error on bad paths:

        >>> zk = zc.zk.ZK('zookeeper.example.com:2181')

        >>> zk.exists('')
        Traceback (most recent call last):
        ...
        BadArgumentsException: bad argument
        >>> zk.exists('xxx')
        Traceback (most recent call last):
        ...
        BadArgumentsException: bad argument
        >>> zk.exists('..')
        Traceback (most recent call last):
        ...
        BadArgumentsException: bad argument
        >>> zk.exists('.')
        Traceback (most recent call last):
        ...
        BadArgumentsException: bad argument

        >>> zk.get('')
        Traceback (most recent call last):
        ...
        BadArgumentsException: bad argument
        >>> zk.get('xxx')
        Traceback (most recent call last):
        ...
        BadArgumentsException: bad argument
        >>> zk.get('..')
        Traceback (most recent call last):
        ...
        BadArgumentsException: bad argument
        >>> zk.get('.')
        Traceback (most recent call last):
        ...
        BadArgumentsException: bad argument


        """
        if badpath(path):
            raise zookeeper.BadArgumentsException('bad argument')
        node = self.root
        for name in path.split('/')[1:]:
            if not name:
                continue
            try:
                node = node.children[name]
            except KeyError:
                raise kazoo.exceptions.NoNodeError('no node')

        return node
        

class Node:
    watchers = child_watchers = exists_watchers = ()
    ephemeral = sequence = False
    version = aversion = cversion = 0
    #acl = zc.zk.OPEN_ACL_UNSAFE

    def meta(self):
        return kazoo.protocol.states.ZnodeStat(
            czxid = 0,
            mzxid = 0,
            ctime = self.ctime,
            mtime = self.mtime,
            version = self.version,
            cversion = self.cversion,
            aversion = self.aversion,
            ephemeralOwner = (1 if self.ephemeral else 0),
            dataLength = len(self.data),
            numChildren = len(self.children),
            pzxid = 0, # XXX what's this?
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
