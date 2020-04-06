import sys
import socket
from model import *
import json
import uuid
import stomp
import boto3
import time


class DBControl(object):
    def __init__(self, mq_ip='54.90.75.203', mq_port='61613'):
        #try:
        self.mq = stomp.Connection([(mq_ip, mq_port)])
        self.mq.start()
        self.mq.connect(wait=True)
        self.login_management = dict() #user -> ip
        self.user_count = dict() #ip -> number of user
        self.machine_management = dict() #ip -> id
        #except Exception as e:
        #    print(e, file=sys.stderr)
        #    print("mq error")

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
        dns = self.login_management[token.owner.username]
        if self.user_count[dns] <= 1:
        	del self.user_count[dns]
        	machine_id = self.machine_management[dns]
        	#delete instance
        	ec2clt = boto3.client('ec2', region_name = 'us-east-1')
        	ec2clt.terminate_instances(InstanceIds = [machine_id])
        	del self.machine_management[dns]
        else:
        	self.user_count[dns] -= 1
        del self.login_management[token.owner.username]
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
                token = uuid.uuid4()
                t = Token.create(token=str(token), owner=res, channel=token.hex[:15].upper())
            g = GroupMember.select().where(GroupMember.member == res)
            channels = []
            channels.append({
                'type': 0,
                'channel': t.channel
            })
            for i in g:
                channels.append({
                    'type': 1,
                    'name': i.group.name,
                    'channel': i.group.channel
                })
            server_availiable = False
            for app_ip, num in self.user_count.items():
                if num < 10:
                    server_availiable = True
            if server_availiable == True:
                dns = app_ip
                self.user_count[app_ip] += 1
                self.login_management[username] = dns
            else:
                ec2rsc = boto3.resource('ec2', region_name = 'us-east-1')
                user_data = '''#!/bin/bash
apt-get update
apt-get install -y python3-stomp
apt-get install -y python3-pip
pip3 install peewee
pip3 install PyMySQL
apt-get install -y github
apt-get install -y python3-boto3
git clone https://github.com/RaymondHuang210129/AWS-Project-for-server-cloning.git
python3 AWS-Project-for-server-cloning/server-login.py 0.0.0.0 65432
'''
                result = ec2rsc.create_instances(ImageId = 'ami-03213fe17be839df9', InstanceType = 't2.micro', MinCount = 1, MaxCount = 1, SecurityGroups = ['NP'], UserData = user_data, KeyName = 'NCTU-InternetProgramDesign')
                print('wait until running')
                result[0].wait_until_running()
                ec2clt = boto3.client('ec2', region_name = 'us-east-1')
                print('wait status ok')
                #client.get_waiter('instance_status_ok').wait(InstanceIds=[instance[0].instance_id])
                ec2clt.get_waiter('instance_status_ok').wait(InstanceIds = [result[0].instance_id])
                collection = ec2rsc.instances.filter(InstanceIds = [result[0].instance_id])
                for col in collection:
                    dns = col.public_ip_address
                if dns != '':
                    self.login_management[username] = dns
                    print(username, self.login_management[username])
                    self.user_count[dns] = 1
                    self.machine_management[dns] = result[0].id
#                    
#                ec2clt = boto3.client('ec2', region_name = 'us-east-1')
#                while True:
#                    info = ec2clt.describe_instances(InstanceIds = [result[0].id])
#                    print('check1')
#                    dns = info['Reservations'][0]['Instances'][0]['PublicIp']
#                    print(dns, 'debug') ##
#                    if dns == '':
#                        print('pending')
#                        time.sleep(1)
#                    else:
#                        self.login_management[username] = dns
#                        self.user_count[dns] = 1
#                        self.machine_management[dns] = result[0].id
#                        break
#                print('check2')
#                while True:
#                    try:
#                        print("wait")
#                        ip_port = (dns, 65432)
#                        sk = socket.socket()
#                        sk.settimeout(1)
#                        sk.connect(ip_port)
#                        break
#                    except Exception as e:
#                        print("wait", e)
#                        time.sleep(1)
#                    finally:
#                        sk.close()
#                print('check3')
            return {
                'status': 0,
                'token': t.token,
                'channel': channels,
                'dns': dns,
                'message': 'Success!'
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
        print(self.login_management)
        dns = self.login_management[token.owner.username]
        if self.user_count[dns] <= 1:
        	del self.user_count[dns]
        	machine_id = self.machine_management[dns]
        	#delete instance
        	ec2clt = boto3.client('ec2', region_name = 'us-east-1')
        	ec2clt.terminate_instances(InstanceIds = [machine_id])
        	del self.machine_management[dns]
        else:
        	self.user_count[dns] -= 1
        del self.login_management[token.owner.username]
        return {
            'status': 0,
            'message': 'Bye!'
        }
##########################################################
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
    def send(self, token, username=None, *args):
        if not args or not username:
            return {
                'status': 1,
                'message': 'Usage: send <user> <friend> <message>'
            }
        else:
            user = User.get_or_none(User.username == username)
            if user:
                friend = Friend.get_or_none(((Friend.user == token.owner) & (Friend.friend == user))
                                | ((Friend.friend == token.owner) & (Friend.user == user)))
                if friend:
                    t = Token.get_or_none(Token.owner == user)
                    if t:
                        msg = {
                            'type': 0,
                            'from': token.owner.username,
                            'to': user.username,
                            'message': " ".join(args)
                        }
                        self.mq.send("/queue/" + t.channel, json.dumps(msg))
                        return {
                            'status': 0,
                            'message': 'Success!'
                        }
                    else:
                        return {
                            'status': 1,
                            'message': '{} is not online'.format(username)
                        }
                else:
                    return {
                        'status': 1,
                        'message': '{} is not your friend'.format(username)
                    }
            else:
                return {
                    'status': 1,
                    'message': 'No such user exist'
                }

    @__auth
    def create_group(self, token, group_name=None, *args):
        if not group_name or args:
            return {
                'status': 1,
                'message': 'Usage: create-group <user> <group>'
            }
        group = Group.get_or_none(Group.name == group_name)
        if not group:
            channel = uuid.uuid4().hex[:20].upper()
            g = Group.create(name=group_name, member=token.owner, channel=channel)
            GroupMember.create(group=g, member=token.owner)
            return {
                'status': 0,
                'message': 'Success!',
                'channel': channel
            }
        else:
            return {
                'status': 1,
                'message': '{} already exist'.format(group_name)
            }

    @__auth
    def list_group(self, token, *args):
        if args:
            return {
                'status': 1,
                'message': 'Usage: list-group <user>'
            }
        groups = Group.select()
        res = []
        for g in groups:
            res.append(g.name)
        return {
            'status': 0,
            'group': res
        }

    @__auth
    def list_joined(self, token, *args):
        if args:
            return {
                'status': 1,
                'message': 'Usage: list-joined <user>'
            }
        groups = GroupMember.select().where(GroupMember.member == token.owner)
        res = []
        for g in groups:
            res.append(g.group.name)
        return {
            'status': 0,
            'group': res
        }

    @__auth
    def join_group(self, token, group_name=None, *args):
        if not group_name or args:
            return {
                'status': 1,
                'message': 'Usage: join-group <user> <group>'
            }
        group = Group.get_or_none(Group.name == group_name)
        if group:
            added = GroupMember.select().where((GroupMember.group == group) & (GroupMember.member == token.owner))
            if not added:
                GroupMember.create(group=group, member=token.owner)
                return {
                    'status': 0,
                    'message': 'Success!',
                    'channel': group.channel
                }
            else:
                return {
                    'status': 1,
                    'message': 'Already a member of {}'.format(group_name)
                }
        else:
            return {
                'status': 1,
                'message': '{} does not exist'.format(group_name)
            }

    @__auth
    def send_group(self, token, group_name=None, *args):
        if not args or not group_name:
            return {
                'status': 1,
                'message': 'Usage: send-group <user> <group> <message>'
            }
        else:
            group = Group.get_or_none(Group.name == group_name)
            if group:
                g = GroupMember.get_or_none((GroupMember.group == group) & (GroupMember.member == token.owner))
                if g:
                    msg = {
                        'type': 1,
                        'from': token.owner.username,
                        'to': g.group.name,
                        'message': " ".join(args)
                    }
                    self.mq.send('/topic/' + g.group.channel, json.dumps(msg))
                    return {
                        'status': 0,
                        'message': 'Success!'
                    }
                else:
                    return {
                        'status': 1,
                        'message': 'You are not the member of {}'.format(group_name)
                    }
            else:
                return {
                    'status': 1,
                    'message': 'No such group exist'
                }


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
                print(command)
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
