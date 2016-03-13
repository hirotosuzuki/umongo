from marshmallow import ValidationError, missing
import pytest

from umongo.data_proxy import DataProxy
from umongo import NestedSchema, fields


class TestDataProxy:

    def test_repr(self):

        class MySchema(NestedSchema):
            field_a = fields.IntField()
            field_b = fields.StrField()

        d = DataProxy(MySchema(), {'field_a': 1, 'field_b': 'value'})
        repr_d = repr(d)
        assert repr_d.startswith("<DataProxy(")
        assert "'field_a': 1" in repr_d
        assert "'field_b': 'value'" in repr_d

    def test_simple(self):

        class MySchema(NestedSchema):
            a = fields.IntField()
            b = fields.IntField()

        d = DataProxy(MySchema())
        d.load({'a': 1, 'b': 2})
        assert d.get('a') == 1
        d.set('b', 3)
        assert d.get('b') == 3
        assert d._data == {'a': 1, 'b': 3}
        assert d.dump() == {'a': 1, 'b': 3}
        d.delete('b') 
        assert d._data == {'a': 1, 'b': missing}
        assert d.dump() == {'a': 1}

    def test_load(self):

        class MySchema(NestedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        d = DataProxy(MySchema())
        d.load({'a': 1, 'b': 2})
        assert d.to_mongo() == {'a': 1, 'in_mongo_b': 2}

        d.set('a', 3)
        assert d.to_mongo(update=True) == {'$set': {'a': 3}}

        d.load({'a': 4, 'b': 5})
        assert d.to_mongo(update=True) is None
        assert d.to_mongo() == {'a': 4, 'in_mongo_b': 5}

        d2 = DataProxy(MySchema(), data={'a': 4, 'b': 5})
        assert d == d2

    def test_modify(self):

        class MySchema(NestedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        d = DataProxy(MySchema())
        d.load({'a': 1, 'b': 2})
        assert d.to_mongo() == {'a': 1, 'in_mongo_b': 2}
        assert d.to_mongo(update=True) is None
        d.set('a', 3)
        d.delete('b')
        assert d.to_mongo(update=True) == {'$set': {'a': 3}, '$unset': ['in_mongo_b']}
        d.clear_modified()
        assert d.to_mongo(update=True) is None
        assert d.to_mongo() == {'a': 3}

    def test_set(self):

        class MySchema(NestedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        d = DataProxy(MySchema())
        d.load({'a': 1, 'b': 2})
        d.set('a', 3)
        assert d.to_mongo() == {'a': 3, 'in_mongo_b': 2}
        assert d.to_mongo(update=True) == {'$set': {'a': 3}}

        d.load({'a': 1, 'b': 2})
        d.set('b', 3)
        assert d.to_mongo() == {'a': 1, 'in_mongo_b': 3}
        assert d.to_mongo(update=True) == {'$set': {'in_mongo_b': 3}}

        with pytest.raises(KeyError):
            d.set('in_mongo_b', 2)

    def test_del(self):

        class MySchema(NestedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        d = DataProxy(MySchema())
        d.load({'a': 1, 'b': 2})
        d.delete('b')
        assert d.to_mongo() == {'a': 1}
        assert d.to_mongo(update=True) == {'$unset': ['in_mongo_b']}
        d.delete('a')
        assert d.to_mongo(update=True) == {'$unset': ['a', 'in_mongo_b']}

        with pytest.raises(KeyError):
            d.delete('in_mongo_b')

    def test_route_naming(self):

        class MySchema(NestedSchema):
            in_front = fields.IntField(attribute='in_mongo')

        d = DataProxy(MySchema())
        with pytest.raises(ValidationError):
            d.load({'in_mongo': 42})
        d.load({'in_front': 42})
        with pytest.raises(KeyError):
            d.get('in_mongo')
        assert d.get('in_front') == 42
        d.set('in_front', 24)
        assert d._data == {'in_mongo': 24}
        assert d.get('in_front') == 24
        assert d.dump() == {'in_front': 24}
        assert d.to_mongo() == {'in_mongo': 24}

    def test_from_mongo(self):

        class MySchema(NestedSchema):
            in_front = fields.IntField(attribute='in_mongo')

        d = DataProxy(MySchema())
        with pytest.raises(KeyError):
            d.from_mongo({'in_front': 42})
        d.from_mongo({'in_mongo': 42})
        assert d.get('in_front') == 42

    def test_equality(self):

        class MySchema(NestedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        d1 = DataProxy(MySchema())
        d1.load({'a': 1, 'b': 2})
        assert d1 == {'a': 1, 'in_mongo_b': 2}

        d2 = DataProxy(MySchema())
        d2.load({'a': 1, 'b': 2})
        assert d1 == d2

    def test_access_by_mongo_name(self):

        class MySchema(NestedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        d = DataProxy(MySchema(), data={'a': 1, 'b': 2})
        assert d.get_by_mongo_name('in_mongo_b') == 2
        assert d.get_by_mongo_name('a') == 1
        with pytest.raises(KeyError):
            d.get_by_mongo_name('b')
        d.set_by_mongo_name('in_mongo_b', 3)
        assert d.to_mongo(update=True) == {'$set': {'in_mongo_b': 3}}
        assert d.get_by_mongo_name('in_mongo_b') == 3
        d.delete_by_mongo_name('in_mongo_b')
        assert d.to_mongo(update=True) == {'$unset': ['in_mongo_b']}

    def test_set_to_missing_fields(self):

        class MySchema(NestedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        d = DataProxy(MySchema(), data={'a': 1})
        assert d.get('b') is None
        assert d.get_by_mongo_name('in_mongo_b') is None
        assert d._data['in_mongo_b'] is missing
        with pytest.raises(KeyError):
            d.delete('b')
        d.set('b', 2)
        assert d.get('b') == 2
        d.delete('b')
        assert d._data['in_mongo_b'] is missing
