# -*- coding: utf-8 -*-

import click
import os
import select
import signal
import socket
import sys
import time


class sshConfig:

    cmd_template = '{cmd} -qTfnN -D{localhost}:{localport} -p{sshport} {user}@{host}'
    defalt_config = {
        'cmd': '/usr/bin/ssh', 'localhost': '0.0.0.0',
        'localport': 8888, 'sshport': 22}

    def __init__(self, config_file=None, **kwargs):
        self.config = dict(self.defalt_config)
        self.config.update(kwargs)
        if config_file is not None:
            self.init_from_file(config_file)

    def init_from_file(self, config_file):
        config_data = {}
        self.config.update(config_data)

    def get_sshtunnel_cmd(self):
        return self.cmd_template.format(**self.config)

    def get_sshtunnel_args(self):
        config = self.config
        cmd = config['cmd']
        localhost = config['localhost']
        localport = config['localport']
        sshport = config['sshport']
        user = config['user']
        host = config['host']
        cmd_args = (
            cmd, '-qTfnN',
            '-D{localhost}:{localport}'.format(
                localhost=localhost, localport=localport),
            '-p{0}'.format(sshport) if sshport else '',
            '{0}@{1}'.format(user, host))
        return tuple(filter(None, cmd_args))


class sshTunneld(object):

    max_failure_num = 5

    def __init__(self, log_file=None, pid_file=None, **kwargs):
        self._config = sshConfig(**kwargs)
        self._log = log_file or os.devnull
        self._pidfile = pid_file
        self._fd = None
        self._pidfd = None
        self._child_pid = None
        self.failure_num = self.max_failure_num
        self._cmd_args = self._config.get_sshtunnel_args()

    def check(self):
        try:
            self._fd = os.open(self._log, os.O_WRONLY|os.O_APPEND|os.O_CREAT)
        except PermissionError:
            print('open file {0} permission denied'.format(self._log))
            sys.exit(1)

        try:
            self._pidfd = os.open(self._pidfile, os.O_RDWR|os.O_CREAT)
        except PermissionError:
            print('open file {0} permission denied'.format(self._log))
            sys.exit(1)
        else:
            pid_str = os.read(self._pidfd, 1024)
            pid = int(pid_str) if pid_str else 0
            if pid:
                try:
                    # check whether child process exists
                    os.kill(pid, 0)
                except ProcessLookupError:
                    pass
                else:
                    sys.exit(0)

        if 'SSH_AUTH_SOCK' not in os.environ:
            print('please run ssh-agent first')
            sys.exit(1)

    def daemond(self):
        pid = os.fork()
        if pid != 0:
            sys.exit(1)
        if os.setsid() == -1:
            print('setsid error')
            sys.exit(1)
        if self._fd is not None:
            stdfd = [s.fileno() for s in [sys.stdin, sys.stdout, sys.stderr]]
            for ofd in stdfd:
                os.dup2(self._fd, ofd)

        if self._pidfd:
            os.truncate(self._pidfd, 0)
            os.write(self._pidfd, str(os.getpid()).encode())
            os.close(self._pidfd)

    def run(self, daemon=True):
        self.check()
        if daemon:
            self.daemond()
        while True:
            self.start()
            self.stop()
        sys.exit(1)

    def start(self):
        try:
            pid = os.fork()
        except OSError:
            print('start ssh tunnel error')
            sys.exit(1)
        if pid == 0:
            # child process
            env = {'SSH_AUTH_SOCK': os.environ['SSH_AUTH_SOCK']}
            os.execve(self._cmd_args[0], self._cmd_args, env)
            sys.exit(1)
            print('must no come here')
        else:
            os.waitpid(pid, 0)
            if self.failure_num == 0:
                print('to many failure')
                sys.exit(1)
            self._sock = self.new_connection()
            if self._sock is None:
                return
            self._child_pid = self.get_sshtunnel_pid()
            self.listen()

    def stop(self):
        self.close_connection()
        if self._child_pid is None or self._child_pid == 0:
            return
        try:
            # check whether child process exists
            os.kill(self._child_pid, 0)
        except ProcessLookupError:
            return
        try:
            os.kill(self._child_pid, signal.SIGKILL)
        except OSError:
            print('kill ssh tunnel error')

    @staticmethod
    def execute(cmd):
        chunk = []
        p1 = os.popen(cmd)
        while True:
            try:
                output = p1._stream.read(1024)
            except OSError:
                break
            if not output:
                break
            chunk.append(output)
        p1.close()
        return ''.join(chunk)

    def get_sshtunnel_pid(self):
        config = self._config.config
        inet_info = '4TCP@{localhost}:{localport}'.format(
            localhost=config['localhost'], localport=config['localport'])
        cmd_str = "lsof -i{inet_info}|awk '/LISTEN/ {{print $2}}'".format(
            inet_info=inet_info)
        pid = self.execute(cmd_str)
        return int(pid) if pid else 0

    def listen(self):
        print('start ssh tunnel monitoring server.')
        while True:
            r, _, _ = select.select([self._sock.fileno()], [], [])
            if r and self._sock.fileno() in set(r):
                break

    def new_connection(self, retry_num=5):
        config = self._config.config
        for i in range(retry_num + 1):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect((config['localhost'], config['localport']))
                self.reset_failure_num()
                return sock
            except ConnectionError:
                sock.close()
                time.sleep(2*i)

        print("can't connect to ssh tunnel")
        self.failure_num -= 1

    def close_connection(self):
        if self._sock:
            self._sock.close()
            self._sock = None
        print('close connection to ssh tunnel')

    def reset_failure_num(self):
        self.failure_num = self.max_failure_num

    def respawn(self):
        pid = self.get_sshtunnel_pid()
        if not pid:
            return
        try:
            # check whether child process exists
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            print('respawn error')


@click.group(help='A simple ssh tunnel tool')
def main():

    pass


@main.command(name='start', help='start ssh tunnel daemon')
@click.argument('user')
@click.argument('host')
@click.argument('port', default='')
def start(**kwargs):

    tunnel = sshTunneld(
        user=kwargs['user'], log_file='/tmp/ssh.log', host=kwargs['host'],
        sshport=kwargs['port'], pid_file='/tmp/sshtunnel.pid')
    tunnel.run()


@main.command(name='spawn', help='respawn a new ssh tunnel')
@click.argument('user')
@click.argument('host')
@click.argument('port', default='')
def spawn(**kwargs):

    tunnel = sshTunneld(
        user=kwargs['user'], log_file='/tmp/ssh.log', host=kwargs['host'],
        sshport=kwargs['port'], pid_file='/tmp/sshtunnel.pid')
    tunnel.respawn()


if __name__ == '__main__':
    main()
