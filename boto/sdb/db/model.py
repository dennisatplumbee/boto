# Copyright (c) 2006,2007,2008 Mitch Garnaat http://garnaat.org/
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from boto.sdb.db.manager import get_manager
from boto.sdb.db.property import *
from boto.sdb.db.key import Key
from boto.sdb.db.query import Query
import boto
import uuid

class ModelMeta(type):
    "Metaclass for all Models"
    def __init__(cls, name, bases, dict):
        super(ModelMeta, cls).__init__(name, bases, dict)
        # Make sure this is a subclass of Model - mainly copied from django ModelBase (thanks!)
        try:
            if filter(lambda b: issubclass(b, Model), bases):
                cls._manager = get_manager(cls)
                # look for all of the Properties and set their names
                for key in dict.keys():
                    if isinstance(dict[key], Property):
                        property = dict[key]
                        property.__property_config__(cls, key)
                prop_names = []
                props = cls.properties()
                for prop in props:
                    if not prop.__class__.__name__.startswith('_'):
                        prop_names.append(prop.name)
                setattr(cls, '_prop_names', prop_names)
        except NameError:
            # 'Model' isn't defined yet, meaning we're looking at our own
            # Model class, defined below.
            pass
        
class Model(object):
    __metaclass__ = ModelMeta

    @classmethod
    def get_lineage(cls):
        l = [c.__name__ for c in cls.mro()]
        l.reverse()
        return '.'.join(l)

    @classmethod
    def kind(cls):
        return cls.__name__
    
    @classmethod
    def _get_by_id(cls, id, manager=None):
        if not manager:
            manager = cls._manager
        return manager.get_object(cls, id)
            
    @classmethod
    def get_by_ids(cls, ids=None, parent=None):
        if isinstance(ids, list):
            objs = [cls._get_by_id(id) for id in ids]
            return objs
        else:
            return cls._get_by_id(ids)

    @classmethod
    def get_by_key_name(cls, key_names, parent=None):
        raise NotImplementedError, "Key Names are not currently supported"

    @classmethod
    def find(cls, **params):
        q = Query(cls)
        for key, value in params.items():
            q.filter('%s =' % key, value)
        return q

    @classmethod
    def all(cls, max_items=None):
        return cls.find()

    @classmethod
    def get_or_insert(key_name, **kw):
        raise NotImplementedError, "get_or_insert not currently supported"
            
    @classmethod
    def properties(cls, hidden=True):
        properties = []
        while cls:
            for key in cls.__dict__.keys():
                prop = cls.__dict__[key]
                if isinstance(prop, Property):
                    if hidden or not prop.__class__.__name__.startswith('_'):
                        properties.append(cls.__dict__[key])
            if len(cls.__bases__) > 0:
                cls = cls.__bases__[0]
            else:
                cls = None
        return properties

    def __init__(self, id=None, **kw):
        if kw.has_key('manager'):
            self._manager = kw['manager']
        self.id = id
        if self.id:
            self._auto_update = True
        else:
            self._auto_update = False
            self.id = str(uuid.uuid4())

    def __repr__(self):
        return '%s<%s>' % (self.__class__.__name__, self.id)

    def _get_raw_item(self):
        return self._manager.get_raw_item(self)

    def put(self):
        self._manager.save_object(self)
        self._auto_update = True

    save = put
        
    def delete(self):
        self._manager.delete_obj(self)

    def key(self):
        return Key(obj=self)

    def set_manager(self, manager):
        self._manager = manager

class Expando(Model):

    def __setattr__(self, name, value):
        if name in self._prop_names:
            object.__setattr__(self, name, value)
        elif name.startswith('_'):
            object.__setattr__(self, name, value)
        elif name == 'id':
            object.__setattr__(self, name, value)
        else:
            self._manager.store_key_value(self, name, value)
            object.__setattr__(self, name, value)

    def __getattr__(self, name):
        if not name.startswith('_'):
            value = self._manager.get_key_value(self, name)
            if value:
                object.__setattr__(self, name, a[name])
                return a[name]
        raise AttributeError

    
