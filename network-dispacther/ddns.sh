#! /bin/bash

IF=$1
STATUS=$2


case "$2" in
        up|dhcp6-change)
        logger "NetworkManager DDNS `date`: $IF $STATUS"
	/etc/NetworkManager/dispatcher.d/ddns.d/tencent_cloud_ddns.py
	if [ $? -ne 0 ]; then logger "NetworkManager DDNS failed!"; fi
        ;;
        *)
        ;;
esac

