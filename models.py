__author__ = 'tarzan'

import importlib
import re
import sys
from datetime import datetime
from sqlalchemy import Table, Column, types
from pyramid.security import Everyone, Authenticated

__all__ = ['import_settings', 'User', 'get_user_groups', 'get_user']

DBSession = None
Base = None
User = None

class _Base_User(object):
    def __unicode__(self):
        return self.email

    def __str__(self):
        return self.__unicode__().encode('utf-8')

    def merge_from_dict(self, dict):
        self.email = dict["email"] or self.email
        self.name = dict["name"] or self.name

    @classmethod
    def import_from_dict(cls, dict):
        obj = DBSession.query(cls).filter(cls.email == dict['email']).first()
        if obj is None:
            obj = cls()
            obj.merge_from_dict(dict)
            DBSession.add(obj)
            DBSession.flush()
        else:
            obj.merge_from_dict(dict)
        obj.id = int(obj.id)

        return obj

def _declare_user_class(groups):
    global Base
    user_model_cls = type('User', (Base, _Base_User), dict(
        __tablename__ = 'user',
        GROUPS = groups,
        id = Column(types.Integer, primary_key=True, autoincrement=True),
        name = Column(types.VARCHAR(length=255), nullable=False),
        email = Column(types.VARCHAR(length=255)),
        created_time = Column(types.DateTime, nullable=False,
                              default=datetime.now),
        last_modified_time = Column(types.DateTime, nullable=False,
                                    default=datetime.now, onupdate=datetime.now),
        groups = Column(types.Text()),
    ))
    setattr(sys.modules[__name__], 'User', user_model_cls)


def get_user_groups(userid, request):
    user = get_user(request)
    if user is None:
        return []
    groups = user.groups or ""
    return [Everyone, Authenticated] + groups.split(',')

def get_user(request):
    user_id = request.unauthenticated_userid
    if user_id:
        return DBSession.query(User).get(user_id)
    return None

def import_settings(settings):
    global DBSession
    global Base

    def _import_object(path):
        _module, _var = path.rsplit('.', 1)
        _module = importlib.import_module(_module, package=None)
        return getattr(_module, _var)

    DBSession = _import_object(settings['dbsession'])
    Base = _import_object(settings['base'])

    groups = re.split(r"[^a-zA-Z0-9-_.:]+", settings.get('user_groups', ''))
    _declare_user_class(groups)