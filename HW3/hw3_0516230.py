#!/usr/bin/python3

import socket, os, sys, json, random, string
from peewee import Model
from peewee import SqliteDatabase
from peewee import CharField
from peewee import FloatField
from peewee import BooleanField
from peewee import IntegerField
from peewee import TextField

dbpath = os.path.join(
	os.path.dirname(os.path.abspath(__file__)),
	'test.db'
)

db = SqliteDatabase(dbpath)

class BaseModel(Model):
	user_id = CharField()

	class Meta:
		database = db

class Registration(BaseModel):
	password = CharField()
	token = CharField()
	log_status = BooleanField()

class Friend(BaseModel):
	friend_id = CharField()

class Invite(BaseModel):
	sender_id = CharField()

class Post(BaseModel):
	message = CharField()

def create_table(table):
	if not table.table_exists():
		table.create_table()

def drop_table(table):
	if table.table_exists():
		table.drop_table()

def register(id, _password):
	result = Registration.select().where(Registration.user_id == id).count()
	if result == 0:
		Registration.create(user_id = id, password = _password, token = '', log_status = False)
		return json.dumps({'status': 0, 'message': 'Success!'})
	else:
		return json.dumps({'status': 1, 'message': id + ' is already used'})

def login(id, _password):
	result = Registration.select().where(Registration.user_id == id, Registration.password == _password)
	if result.count() == 0:
		return json.dumps({'status': 1, 'message': 'No such user or password error'})
	else:
		_token = ''.join(random.choice(string.ascii_uppercase + string.digits) for i in range(0, 10))
		Registration.update(log_status = True, token = _token).where(Registration.user_id == id).execute()
		return json.dumps({'status': 0, 'token': _token, 'message': 'Success!'})

def delete(token):
	result = Registration.select(Registration.user_id).where(Registration.token == token, Registration.log_status == True)
	if result.count() == 0:
		return json.dumps({'status': 1, 'message': 'Not login yet'})
	else:
		for i in result:
			Registration.delete().where(Registration.user_id == i.user_id).execute()
			Friend.delete().where((Friend.user_id == i.user_id) | (Friend.friend_id == i.user_id)).execute()
			Invite.delete().where((Invite.user_id == i.user_id) | (Invite.sender_id == i.user_id)).execute()
			Post.delete().where(Post.user_id == i.user_id).execute()
		return json.dumps({'status': 0, 'message': 'Success!'})

def logout(_token):
	result = Registration.select(Registration.user_id).where(Registration.token == _token, Registration.log_status == True).count()
	if result == 0:
		return json.dumps({'status': 1, 'message': 'Not login yet'})
	else:
		Registration.update(log_status = False).where(Registration.token == _token).execute()
		return json.dumps({'status': 0, 'message': 'Bye!'})

def invite(token, id):
	result = Registration.select(Registration.user_id).where(Registration.token == token, Registration.log_status == True).count()
	if result == 0:
		return json.dumps({'status': 1, 'message': 'Not login yet'})
	result = Registration.select().where(Registration.user_id == id).count()
	if result == 0:
		return json.dumps({'status': 1, 'message': id + ' does not exist'})
	result = Registration.select().where(Registration.token == token, Registration.user_id == id).count()
	if result == 1:
		return json.dumps({'status': 1, 'message': 'You cannot invite yourself'})
	identity = Registration.select().where(Registration.token == token, Registration.log_status == True)
	for i in identity:
		result = Friend.select().where(Friend.user_id == i.user_id, Friend.friend_id == id).count()
		if result == 1:
			return json.dumps({'status': 1, 'message': id + ' is already your friend'})
		result = Invite.select().where(Invite.user_id == i.user_id, Invite.sender_id == id).count()
		if result == 1:
			return json.dumps({'status': 1, 'message': id + ' has invited you'})
		result = Invite.select().where(Invite.user_id == id, Invite.sender_id == i.user_id).count()
		if result == 1:
			return json.dumps({'status': 1, 'message': 'Already invited'})
		else:
			Invite.create(user_id = id, sender_id = i.user_id)
			return json.dumps({'status': 0, 'message': 'Success!'})

def list_invite(token):
	result = Registration.select(Registration.user_id).where(Registration.token == token, Registration.log_status == True)
	if result.count() == 0:
		return json.dumps({'status': 1, 'message': 'Not login yet'})
	else:
		for j in result:
			friends = Invite.select(Invite.sender_id).where(Invite.user_id == j.user_id)
			return json.dumps({'status': 0, 'invite': [i.sender_id for i in friends]})

def accept_invite(token, id):
	user = Registration.select(Registration.user_id).where(Registration.token == token, Registration.log_status == True)
	if user.count() == 0:
		return json.dumps({'status': 1, 'message': 'Not login yet'})
	else:
		for i in user:
			result = Invite.delete().where(Invite.user_id == i.user_id, Invite.sender_id == id).execute()
			if result == 0:
				return json.dumps({'status': 1, 'message': id + ' did not invite you'})
			else:
				Friend.create(user_id = i.user_id, friend_id = id)
				Friend.create(user_id = id, friend_id = i.user_id)
				return json.dumps({'status': 0, 'message': 'Success!'})

def list_friend(token):
	result = Registration.select(Registration.user_id).where(Registration.token == token, Registration.log_status == True)
	if result.count() == 0:
		return json.dumps({'status': 1, 'message': 'Not login yet'})
	else:
		for j in result:
			friends = Friend.select(Friend.friend_id).where(Friend.user_id == j.user_id)
			return json.dumps({'status': 0, 'friend': [i.friend_id for i in friends]})

def post(token, _message):
	user = Registration.select(Registration.user_id).where(Registration.token == token, Registration.log_status == True)
	if user.count() == 0:
		return json.dumps({'status': 1, 'message': 'Not login yet'})
	else:
		for i in user:
			Post.create(user_id = i.user_id, message = _message)
			return json.dumps({'status': 0, 'message': 'Success!'})

def receive_post(token):
	user = Registration.select(Registration.user_id).where(Registration.token == token, Registration.log_status == True)
	if user.count() == 0:
		return json.dumps({'status': 1, 'message': 'Not login yet'})
	else:
		for j in user:
			friends = Friend.select(Friend.friend_id).where(Friend.user_id == j.user_id)
			messages = []
			for friend in friends:
				messages.extend({'id': i.user_id, 'message': i.message} for i in (Post.select().where(Post.user_id == friend.friend_id)))
			return json.dumps({'status': 0, 'post' : [{'id': i['id'], 'message': i['message']} for i in messages]})

create_table(Registration)
create_table(Friend)
create_table(Invite)
create_table(Post)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = sys.argv[1]
port = int(sys.argv[2])
s.bind((host, port))
s.listen(5)
while True:
	clientSocket, address = s.accept()
	command = clientSocket.recv(1024).decode().split()
	if command[0] == 'register':
		if len(command) != 3:
			clientSocket.send(json.dumps({'status': 1, 'message': 'Usage: register <id> <password>'}).encode())
		else:
			clientSocket.send(register(command[1], command[2]).encode())
	elif command[0] == 'login':
		if len(command) != 3:
			clientSocket.send(json.dumps({'status': 1, 'message': 'Usage: login <id> <password>'}).encode())
		else:
			clientSocket.send(login(command[1], command[2]).encode())
	elif command[0] == 'invite':
		if len(command) != 3:
			clientSocket.send(json.dumps({'status': 1, 'message': 'Usage: invite <user> <id>'}).encode())
		else:
			clientSocket.send(invite(command[1], command[2]).encode())
	elif command[0] == 'accept-invite':
		if len(command) != 3:
			clientSocket.send(json.dumps({'status': 1, 'message': 'Usage: accept-invite <user> <id>'}).encode())
		else:
			clientSocket.send(accept_invite(command[1], command[2]).encode())
	elif command[0] == 'post':
		if len(command) != 3:
			clientSocket.send(json.dumps({'status': 1, 'message': 'Usage: post <user> <message>'}).encode())
		else:
			clientSocket.send(post(command[1], command[2]).encode())
	elif command[0] == 'delete':
		if len(command) != 2:
			clientSocket.send(json.dumps({'status': 1, 'message': 'Usage: delete <user>'}).encode())
		else:
			clientSocket.send(delete(command[1]).encode())
	elif command[0] == 'logout':
		if len(command) != 2:
			clientSocket.send(json.dumps({'status': 1, 'message': 'Usage: logout <user>'}))
		else:
			clientSocket.send(logout(command[1]).encode())
	elif command[0] == 'list-invite':
		if len(command) != 2:
			clientSocket.send(json.dumps({'status': 1, 'message': 'Usage: list-invite <user>'}).encode())
		else:
			clientSocket.send(list_invite(command[1]).encode())
	elif command[0] == 'list-friend':
		if len(command) != 2:
			clientSocket.send(json.dumps({'status': 1, 'message': 'Usage: list-friend <user>'}).encode())
		else:
			clientSocket.send(list_friend(command[1]).encode())
	elif command[0] == 'receive-post':
		if len(command) != 2:
			clientSocket.send(json.dumps({'status': 1, 'message': 'Usage: receive-post <user>'}).encode())
		else:
			clientSocket.send(receive_post(command[1]).encode())
	else:
		clientSocket.send(json.dumps({'status': 1, 'message': 'unknown command'}).encode())


