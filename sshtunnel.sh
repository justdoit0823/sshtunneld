#!/bin/bash

start()
{
	start-stop-daemon --start --nodook --name sshtunneld --pidfile /var/run/sshtunnel.pid --startas /usr/local/bin/sshtunnel --daemon
	echo "start sshtunneld server"
}

stop()
{
	start-stop-daemon --stop --nodook --name sshtunneld --pidfile /var/run/sshtunnel.pid --retry 5
	echo "stop sshtunneld server"
}

status()
{
	start-stop-daemon --status --nodook --name sshtunneld --pidfile

}


check()
{
	if [ ! -x /usr/local/bin/sshtunnel ]; then

		echo "can not execute sshtunnel"
		exit 1
	fi
	if [ ! -r /etc/sshtunnel.conf ]; then

		echo "no sshtunnel.conf file"
		exit 1
	fi
}
