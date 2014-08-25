from datetime import datetime, date


def is_json_key_in_paths(key, seq):
    for p in seq:
        if p == key or p.startswith(key+'.'):
            return True
    return False


def json_subkeys(key, seq):
    subkeys = []
    for p in seq:
        root, _, subkey = p.partition('.')
        if root == key and len(subkey) > 0:
            subkeys.append(subkey)
    return tuple(subkeys)


class JSONSerialize(object):
    'Mixin for retrieving public fields of model in json-compatible format'
    __public__ = None

    def get_public(self, **kwargs):
        "Returns model's PUBLIC data for jsonify"
        data = {}
        exclude = kwargs.get("exclude", ())
        extra = kwargs.get("extra", ())
        override = kwargs.get("override", ())
        keys = self._sa_instance_state.attrs.items()
        public = override if override else self.__public__
        if extra:
            public += extra

        if not public:
            return {}

        for k, field in keys:
            if k in public:
                add_subkey = False
            elif is_json_key_in_paths(k, public):
                add_subkey = True
            else:
                continue
            if k in exclude:
                continue

            if add_subkey:
                public_subkeys = json_subkeys(k, public)
                exclude_subkeys = json_subkeys(k, exclude)
                value = self._serialize(field.value,
                                        override=public_subkeys,
                                        exclude=exclude_subkeys)
            else:
                value = self._serialize(field.value,
                                        extra=extra,
                                        exclude=exclude)
            if value:
                data[k] = value
        return data

    @classmethod
    def _serialize(cls, value, follow_fk=False, **get_public_kwargs):
        if type(value) in (datetime, date):
            ret = value.isoformat()
        elif hasattr(value, '__iter__'):
            ret = []
            for v in value:
                ret.append(cls._serialize(v, **get_public_kwargs))
        elif JSONSerialize in value.__class__.__bases__:
            ret = value.get_public(**get_public_kwargs)
        else:
            ret = value

        return ret
