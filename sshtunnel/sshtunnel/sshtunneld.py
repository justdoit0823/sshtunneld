# -*- coding: utf-8 -*-


import socket
import os
import sys
import select
import signal
import time


class sshTunneld(object):

    def __init__(self, cmd='/usr/bin/ssh', user='justdoit',
                 local_host='0.0.0.0', local_port=8888,
                 remote_host='shareyou.net.cn', remote_port=22122,
                 log_file=None):
        self._cmd = cmd
        self._user = user
        self._lhost = local_host
        self._lport = local_port
        self._rhost = remote_host
        self._rport = remote_port
        self._log = log_file or os.devnull
        self._fd = None
        self.failure_num = 5
        addr = ':'.join((self._lhost, str(self._lport)))
        self._cmd_args = (cmd, '-qTfnN', '-D{0}'.format(addr),
                          '-p{0}'.format(str(self._rport)),
                          '{0}@{1}'.format(self._user, self._rhost))

    def check(self):
        try:
            self._fd = os.open(self._log, os.O_WRONLY|os.O_APPEND)
        except PermissionError:
            print('open file {0} permission denied'.format(self._log))
            sys.exit(1)
        if 'SSH_AUTH_SOCK' not in os.environ:
            print('please run ssh-agent first')
            sys.exit(1)

    def daemond(self):
        pid = os.fork()
        if pid != 0:
            sys.exit(1)
        if os.setsid() == -1:
            print('setsid error\n')
            sys.exit(1)
        if self._fd is not None:
            stdfd = [s.fileno() for s in [sys.stdin, sys.stdout, sys.stderr]]
            for ofd in stdfd:
                os.dup2(self._fd, ofd)

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
            print('start ssh tunnel error\n')
            sys.exit(1)
        if pid == 0:
            # child process
            env = {'SSH_AUTH_SOCK': os.environ['SSH_AUTH_SOCK']}
            os.execve(self._cmd, self._cmd_args, env)
            sys.exit(1)
            print('must no come here\n')
        else:
            os.waitpid(pid, 0)
            if self.failure_num == 0:
                print('to many failure\n')
                sys.exit(1)
            self._sock = self.new_connection()
            if self._sock is None:
                return
            self._child_pid = self.get_sshtunnel_pid()
            self.listen()

    def stop(self):
        self.close_connection()
        if self._child_pid == 0:
            return
        try:
            os.kill(self._child_pid, signal.SIGKILL)
        except OSError:
            print('kill ssh tunnel error\n')
            pass

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
        cmd_str = ' '.join(self._cmd_args)
        grep_str = ("ps aux|grep \"{0}\" | grep -v grep "
                    "| awk '{{print $2}}'").format(cmd_str)
        pid = self.execute(grep_str)
        return int(pid) if pid else 0

    def listen(self):
        print('start ssh tunnel monitoring server.\n')
        while True:
            r, _, _ = select.select([self._sock.fileno()], [], [])
            if r and self._sock.fileno() in set(r):
                break

    def new_connection(self, retry_num=5):
        for i in range(retry_num + 1):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect((self._lhost, self._lport))
                return sock
            except ConnectionError:
                sock.close()
                time.sleep(2**i)
        print("can't connect to ssh tunnel\n")
        self.failure_num -= 1

    def close_connection(self):
        self._sock.close()
        self._sock = None


def main():
    d1 = sshTunneld(user='anoproxy', log_file="/tmp/ssh.log")
    d1.run()


if __name__ == '__main__':
    main()
