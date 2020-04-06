#!/usr/bin/python3

import sys
import socket
from model import *
import json
import uuid
import stomp
import time


class DBControl(object):
    def __auth(func):
        def validate_token(self, token=None, *args):
            if token:
                t = Token.get_or_none(Token.token == token)
                if t:
                    return func(self, t, *args)
            return {
                'status': 1,
                'message': 'Not login yet'
            }
        return validate_token

    def register(self, username=None, password=None, *args):
        if not username or not password or args:
            return {
                'status': 1,
                'message': 'Usage: register <username> <password>'
            }
        if User.get_or_none(User.username == username):
            return {
                'status': 1,
                'message': '{} is already used'.format(username)
            }
        res = User.create(username=username, password=password)
        if res:
            return {
                'status': 0,
                'message': 'Success!'
            }
        else:
            return {
                'status': 1,
                'message': 'Register failed due to unknown reason'
            }

    @__auth
    def delete(self, token, *args):
        if args:
            return {
                'status': 1,
                'message': 'Usage: delete <user>'
            }
        token.owner.delete_instance()
        return {
            'status': 0,
            'message': 'Success!'
        }

    def login(self, username=None, password=None, *args):
        if not username or not password or args:
            return {
                'status': 1,
                'message': 'Usage: login <id> <password>'
            }
        res = User.get_or_none((User.username == username) & (User.password == password))
        if res:
            t = Token.get_or_none(Token.owner == res)
            if not t:
                t = Token.create(token=str(uuid.uuid4()), owner=res)
            join = []
            print(username)
            groups = Membership.select().where(Membership.user == res)
            for g in groups:
                print(g.join.groupname)
                join.append(g.join.groupname)
            return {
                'status': 0,
                'token': t.token,
                'message': 'Success!',
                'join' : join
            }
        else:
            return {
                'status': 1,
                'message': 'No such user or password error'
            }

    @__auth
    def logout(self, token, *args):
        if args:
            return {
                'status': 1,
                'message': 'Usage: logout <user>'
            }
        token.delete_instance()
        return {
            'status': 0,
            'message': 'Bye!'
        }

    @__auth
    def invite(self, token, username=None, *args):
        if not username or args:
            return {
                'status': 1,
                'message': 'Usage: invite <user> <id>'
            }
        if username == token.owner.username:
            return {
                'status': 1,
                'message': 'You cannot invite yourself'
            }
        friend = User.get_or_none(User.username == username)
        if friend:
            res1 = Friend.get_or_none((Friend.user == token.owner) & (Friend.friend == friend))
            res2 = Friend.get_or_none((Friend.friend == token.owner) & (Friend.user == friend))
            if res1 or res2:
                return {
                    'status': 1,
                    'message': '{} is already your friend'.format(username)
                }
            else:
                invite1 = Invitation.get_or_none((Invitation.inviter == token.owner) & (Invitation.invitee == friend))
                invite2 = Invitation.get_or_none((Invitation.inviter == friend) & (Invitation.invitee == token.owner))
                if invite1:
                    return {
                        'status': 1,
                        'message': 'Already invited'
                    }
                elif invite2:
                    return {
                        'status': 1,
                        'message': '{} has invited you'.format(username)
                    }
                else:
                    Invitation.create(inviter=token.owner, invitee=friend)
                    return {
                        'status': 0,
                        'message': 'Success!'
                    }
        else:
            return {
                'status': 1,
                'message': '{} does not exist'.format(username)
            }
        pass

    @__auth
    def list_invite(self, token, *args):
        if args:
            return {
                'status': 1,
                'message': 'Usage: list-invite <user>'
            }
        res = Invitation.select().where(Invitation.invitee == token.owner)
        invite = []
        for r in res:
            invite.append(r.inviter.username)
        return {
            'status': 0,
            'invite': invite
        }

    @__auth
    def accept_invite(self, token, username=None, *args):
        if not username or args:
            return {
                'status': 1,
                'message': 'Usage: accept-invite <user> <id>'
            }
        inviter = User.get_or_none(User.username == username)
        invite = Invitation.get_or_none((Invitation.inviter == inviter) & (Invitation.invitee == token.owner))
        if invite:
            Friend.create(user=token.owner, friend=inviter)
            invite.delete_instance()
            return {
                'status': 0,
                'message': 'Success!'
            }
        else:
            return {
                'status': 1,
                'message': '{} did not invite you'.format(username)
            }
        pass

    @__auth
    def list_friend(self, token, *args):
        if args:
            return {
                'status': 1,
                'message': 'Usage: list-friend <user>'
            }
        friends = Friend.select().where((Friend.user == token.owner) | (Friend.friend == token.owner))
        res = []
        for f in friends:
            if f.user == token.owner:
                res.append(f.friend.username)
            else:
                res.append(f.user.username)
        return {
            'status': 0,
            'friend': res
        }

    @__auth
    def send(self, token, friend=None, *args):
        if not args or not friend:
            return {
                'status': 1,
                'message': 'Usage: send <user> <friend> <message>'
            }
        receiver = User.get_or_none(User.username == friend)
        if not receiver:
            return {
                'status': 1,
                'message': 'No such user exist'
            }
        _friend = Friend.get_or_none(((Friend.user == token.owner) & (Friend.friend == receiver)) | ((Friend.user == receiver) & (Friend.friend == token.owner)))
        if not _friend:
            return {
                'status': 1,
                'message': receiver.username + ' is not your friend'
            }

        if Token.get_or_none(Token.owner == receiver): #online
            #send action
            if _friend.user == token.owner:
                self.__send_to_queue(token.owner.username, _friend.friend.username, 'queue', ' '.join(args))
            else:
                self.__send_to_queue(token.owner.username, _friend.user.username, 'queue', ' '.join(args))
            return {
                'status': 0,
                'message': 'Success!'
            }
        else: 
            return {
                'status': 1,
                'message': friend + ' is not online'
            }


    @__auth
    def post(self, token, *args):
        if len(args) <= 0:
            return {
                'status': 1,
                'message': 'Usage: post <user> <message>'
            }
        Post.create(user=token.owner, message=' '.join(args))
        return {
            'status': 0,
            'message': 'Success!'
        }

    @__auth
    def receive_post(self, token, *args):
        if args:
            return {
                'status': 1,
                'message': 'Usage: receive-post <user>'
            }
        res = Post.select().where(Post.user != token.owner).join(Friend, on=((Post.user == Friend.user) | (Post.user == Friend.friend))).where((Friend.user == token.owner) | (Friend.friend == token.owner))
        post = []
        for r in res:
            post.append({
                'id': r.user.username,
                'message': r.message
            })
        return {
            'status': 0,
            'post': post
        }

    @__auth
    def create_group(self, token, group=None, *args):
        if args or not group:
            return {
                'status': 1,
                'message': 'Usage: send <user> <friend> <message>'
            }
        _group = Group.get_or_none(Group.groupname == group)
        if _group:
            return {
                'status': 1,
                'message': group + ' already exist'
            }
        else:
            Group.create(groupname = group);
            _group = Group.get_or_none(Group.groupname == group)
            Membership.create(user = token.owner, join = _group)
            return {
                'status': 0,
                'message': 'Success!'
            }

    @__auth
    def list_group(self, token, *args):
        if args:
            return {
                'status': 1,
                'message': 'Usage: list-group <user>'
            }
        groups = Group.select(Group.groupname)
        if not groups:
            return {
                'status': 0,
                'message': 'No groups'
            }
        else:
            content = [];
            for g in groups:
                content.append(g.groupname);
            return {
                'status': 0,
                'groups': content
            }

    @__auth
    def list_joined(self, token, *args):
        if args:
            return {
                'status': 1,
                'message': 'Usage: list-joined <user>'
            }
        groups = Membership.select(Membership.join).where(Membership.user == token.owner)
        if not groups:
            return {
                'status': 0,
                'message': 'No groups'
            }
        else:
            content = [];
            for g in groups:
                content.append(g.join.groupname);
            return {
                'status': 0,
                'groups': content
            }

    @__auth
    def join_group(self, token, group=None, *args):
        if args or not group:
            return {
            'status': 1,
            'message': 'Usage: join-group <user> <group>'
            }
        _groups = Group.get_or_none(Group.groupname == group)
        if not _groups:
            return {
                'status': 1,
                'message': group + ' does not exist'
            }
        member = Membership.get_or_none((Membership.user == token.owner) & (Membership.join == _groups))
        if member:
            return {
                'status': 1,
                'message': 'Already a member of ' + group
            }
        else:
            Membership.create(user = token.owner, join = _groups)
            return {
                'status': 0,    
                'message': 'Success!'
            }

    @__auth
    def send_group(self, token, group=None, *args):
        if len(args) <= 0 or not group:
            return {
                'status': 1,
                'message': 'Usage: send-group <user> <group> <message>'
            }
        groups = Group.get_or_none(Group.groupname == group)
        if not groups:
            return {
                'status': 1,
                'message': 'No such group exist'
            }
        else:
            member = Membership.get_or_none((Membership.user == token.owner) & (Membership.join == groups))
            if not member:
                return {
                    'status': 1,
                    'message': 'You are not the member of ' + group
                }
            else:
                message = ' '.join(args)
                #send group message
                self.__send_to_queue(token.owner.username, group, 'topic', ' '.join(args))
                return {
                    'status': 0,
                    'message': 'Success!'
                }

    def __send_to_queue(self, sender, receiver, type, msg):
        conn = stomp.Connection10([('127.0.0.1', 61613)])
        conn.start()
        conn.connect()
        if type == 'queue':
            conn.send('/queue/' + receiver, '<<<' + sender + '->' + receiver + ': ' + msg + '>>>')
        else:
            conn.send('/topic/' + receiver, '<<<' + sender + '->GROUP<' + receiver + '>: ' + msg + '>>>')



class Server(object):
    def __init__(self, ip, port):
        try:
            socket.inet_aton(ip)
            if 0 < int(port) < 65535:
                self.ip = ip
                self.port = int(port)
            else:
                raise Exception('Port value should between 1~65535')
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.db = DBControl()
        except Exception as e:
            print(e, file=sys.stderr)
            sys.exit(1)

    def run(self):
        self.sock.bind((self.ip, self.port))
        self.sock.listen(100)
        socket.setdefaulttimeout(0.1)
        while True:
            #try:
                conn, addr = self.sock.accept()
                with conn:
                    cmd = conn.recv(4096).decode()
                    resp = self.__process_command(cmd)
                    conn.send(resp.encode())
            #except Exception as e:
            #    print(e, file=sys.stderr)

    def __process_command(self, cmd):
        command = cmd.split()
        if len(command) > 0:
            command_exec = getattr(self.db, command[0].replace('-', '_'), None)
            if command_exec:
                return json.dumps(command_exec(*command[1:]))
        return self.__command_not_found(command[0])

    def __command_not_found(self, cmd):
        return json.dumps({
            'status': 1,
            'message': 'Unknown command {}'.format(cmd)
        })


def launch_server(ip, port):
    c = Server(ip, port)
    c.run()

if __name__ == '__main__':
    if sys.argv[1] and sys.argv[2]:
        launch_server(sys.argv[1], sys.argv[2])
