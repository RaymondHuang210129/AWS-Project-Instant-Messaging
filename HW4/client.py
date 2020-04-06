#!/usr/bin/python3
import sys, socket, json
import stomp, time

class SampleListener(object):
    def on_message(self, header, message):
        print(message)

host = sys.argv[1]#'140.113.207.51'
port = int(sys.argv[2])#8008
user = dict()
conn = dict()
for line in sys.stdin :
	if line == "exit\n":
		sys.exit()
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	command = line.split();
	if len(command) >= 2:
		username = command[1]
	if command[0] != 'register' and command[0] != 'login' and len(command) != 1:
		if command[1] in user.keys():
			command[1] = user[command[1]]
		else:
			command.pop(1)
		line = ' '.join(command)
	if s.connect_ex((host, port)) == 0 :
		s.send(line.encode())
		a = s.recv(1024).decode("utf-8")
		response = json.loads(a)
		if response['status'] == 0:
			if 'token' in response.keys():
				user[username] = response['token']
				if username not in conn.keys():
					conn[username] = stomp.Connection10([('127.0.0.1', 61613)])
					conn[username].set_listener('SampleListener', SampleListener())
					conn[username].start()
					conn[username].connect()
					conn[username].subscribe('/queue/' + username)
					for j in response['join']:
						conn[command[1]].subscribe('/topic/' + j)
			if 'invite' in response.keys():
				if response['invite'] == []:
					print('No invitations')
				else:
					print('\n'.join(response['invite']))
			if 'message' in response.keys():
				print(response['message'])
			if 'friend' in response.keys():
				if response['friend'] == []:
					print('No friends')
				else:
					print('\n'.join(response['friend']))
			if 'post' in response.keys():
				if response['post'] == []:
					print('No posts')
				else:
					for post in response['post']:
						print(post['id'], ':', post['message'])
			if 'groups' in response.keys():
				if response['groups'] == []:
					print('No groups')
				else:
					for group in response['groups']:
						print(group)
			if command[0] == 'delete' or command[0] == 'logout':
				conn[username].disconnect()
				del conn[username]
			if command[0] == 'join-group' or command[0] == 'create-group':
				conn[username].subscribe('/topic/' + command[2])

		else:
			print(response['message'])
	else:
		print('unable to connect server')
	s.close()



