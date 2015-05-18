#!/bin/bash


DAEMON="/usr/local/bin/sshtunnel"
PIDFILE="/var/run/sshtunnel.pid"
DAEMON_NAME="sshtunneld"
CONFIGFILE="/etc/sshtunnel.conf"


start()
{
	start-stop-daemon --start --oknodo --name $DAEMON_NAME --pidfile $PIDFILE --startas $DAEMON --daemon
	echo "start sshtunneld server"
}

stop()
{
	start-stop-daemon --stop --oknodo --name $DAEMON_NAME --pidfile $PIDFILE --retry 5
	echo "stop sshtunneld server"
}

status()
{
	start-stop-daemon --status --oknodo --name $DAEMON_NAME --pidfile $PIDFILE
	if [ $? == 0 ]; then
	    echo "sshtunnel daemon is running"
	fi
}


check()
{
	if [ ! -x $DAEMON ]; then

		echo "can not execute sshtunnel"
		exit 1
	fi
	if [ ! -r /etc/sshtunnel.conf ]; then

		echo "no sshtunnel.conf file"
		exit 1
	fi
}
