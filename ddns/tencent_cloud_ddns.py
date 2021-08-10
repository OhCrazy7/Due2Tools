#! /bin/env python3

import socket
import ipaddress

import json
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.dnspod.v20210323.dnspod_client import DnspodClient
from tencentcloud.dnspod.v20210323 import models

'''
ddns configure file
On archlinux, put it into /etc/NetworkManager/dispatcher.d/ddns.d

domain=qq.com
secretId=YOUR_ID
secretKey=YOUR_KEY
subdomains=www,@,mail,etc
'''
configfile = "/etc/NetworkManager/dispatcher.d/ddns.d/ddns.conf"

def getipv6addr():
    hostname = socket.gethostname()
    # host: hostname, port: None, family: AF_INET6, type: SOCK_STREAM (tcp)
    addrinfo = socket.getaddrinfo(hostname, None, socket.AF_INET6, socket.SOCK_STREAM)
    ipv6addr = set()
    for info in addrinfo:
        addr = info[4][0]
        # global address
        if ipaddress.IPv6Address(addr).is_global:
            ipv6addr.add(addr)
    return ipv6addr


def parseconfig():
    config = {}
    with open(configfile, "r") as f:
        lines = f.read().split("\n")
        for line in lines:
            for key in ["domain", "secretId", "secretKey", "subdomains"]:
                if line.startswith(key):
                    config[key] = line[len(key)+1:]
                    break
    for key in ["domain", "secretId", "secretKey", "subdomains"]:
        assert key in config, "config file miss {}".format(key)
    config["subdomains"] = config["subdomains"].split(",")
    return config


def getdnspodclient(config:dict) -> DnspodClient:
    cred = credential.Credential(secretId=config["secretId"], secretKey=config["secretKey"])
    httpProfile = HttpProfile(endpoint="dnspod.tencentcloudapi.com")
    clientProfile = ClientProfile(httpProfile=httpProfile)
    client = DnspodClient(cred, "", clientProfile) 
    return client


def getrecords(client:DnspodClient, config, ipv6addr) -> list[models.RecordListItem]:
    req = models.DescribeRecordListRequest()
    params = {
        "Domain": config["domain"]
    }
    req.from_json_string(json.dumps(params))
    resp = client.DescribeRecordList(req)
    records = []
    for record in resp.RecordList:
        if record.Type != "AAAA" or \
            record.Name not in config["subdomains"] or \
            record.Value == ipv6addr or \
            record.Status != "ENABLE":
            continue
        records.append(record)
    return records


def modifyrecords(client:DnspodClient, records:list[models.RecordListItem], ipv6addr) -> None:
    req = models.ModifyRecordBatchRequest()
    params = {
        "RecordIdList" : [record.RecordId for record in records],
        "Change" : "value",
        "ChangeTo" : ipv6addr
    }
    req.from_json_string(json.dumps(params))
    resp = client.ModifyRecordBatch(req)
    print(resp.to_json_string())


if __name__ == "__main__":
    # get system current ipv6 address
    ipv6addr = getipv6addr()
    assert len(ipv6addr) != 0, "No ipv6 address is found!"
    ipv6addr = ipv6addr.pop()
    print("DDNS IPV6: {}".format(ipv6addr))
    # parse config file
    config = parseconfig()
    print("DDNS Domain: {}".format(config["domain"]))
    print("DDNS SubDomains: {}".format(config["subdomains"]))
    # get the tencent dnspod client
    try:
        client = getdnspodclient(config)
        records = getrecords(client, config, ipv6addr)
        for record in records:
            print("DDNS Record: {}".format(record))
        if len(records) != 0:
            modifyrecords(client, records, ipv6addr)
    except TencentCloudSDKException as err:
        print(err)
        exit(1)
