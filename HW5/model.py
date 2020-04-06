from peewee import *

#pragmas={'foreign_keys': 1}
db = MySQLDatabase('testdb', host = 'testdb.cohtw5cyxow3.us-east-1.rds.amazonaws.com', port = 3306, user = 'raymond860909', passwd = 'ltes123456')


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    username = CharField(unique=True)
    password = CharField()


class Invitation(BaseModel):
    inviter = ForeignKeyField(User, on_delete='CASCADE', related_name = 'inviter')
    invitee = ForeignKeyField(User, on_delete='CASCADE', related_name = 'invitee')


class Friend(BaseModel):
    user = ForeignKeyField(User, on_delete='CASCADE', related_name = 'user')
    friend = ForeignKeyField(User, on_delete='CASCADE', related_name = 'friend')


class Post(BaseModel):
    user = ForeignKeyField(User, on_delete='CASCADE')
    message = CharField()


class Token(BaseModel):
    token = CharField(unique=True)
    owner = ForeignKeyField(User, on_delete='CASCADE')
    channel = CharField(unique=True)


class Group(BaseModel):
    name = CharField(unique=True)
    channel = CharField(unique=True)


class GroupMember(BaseModel):
    group = ForeignKeyField(Group, on_delete='CASCADE', related_name = 'group')
    member = ForeignKeyField(User, on_delete='CASCADE', related_name = 'member')


if __name__ == '__main__':
    db.connect()
    db.create_tables([User, Invitation, Friend, Post, Token, Group, GroupMember])
