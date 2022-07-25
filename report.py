#!/usr/bin/env python3

import weasyprint
import requests
from collections import defaultdict
from tabulate import tabulate

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



AOS_SERVER = "https://127.0.0.1:8888/api"
AOS_USERNAME = "admin"
AOS_PASSWORD = "admin"


class aos(object):
    url = ""

    def __init__(self, host, username, password, verify = True):
      self.host = host
      self.verify = verify
      self.s = requests.Session()

      url = self.host + "/user/login"
      body = { "username": username, "password": password }

      r = self.s.post(url, json = body, verify=self.verify)

      if r.status_code != 201:
        raise ConnectionError("Failed to get token")

      self.s.headers["AUTHTOKEN"] = r.json()['token']
      self.s.verify = self.verify

    def get_leafs(self, bp):
        url = self.host + "/blueprints/" + bp + "/ql"
        body = { "query": "{ system_nodes(role: \"leaf\" ){id, label, system_id}}"}

        r = self.s.post(url, json = body)
        if r.status_code != 200:
            raise ConnectionError("Failed to get leafs")

        return r.json()['data']['system_nodes']

    def get_nodes(self, bp):
        return self.get_spines(bp) + self.get_leafs(bp)

    def get_spines(self, bp):
        url = self.host + "/blueprints/" + bp + "/ql"
        body = { "query": "{ system_nodes(role: \"spine\" ){id, label, system_id}}"}

        r = self.s.post(url, json = body)
        if r.status_code != 200:
            raise ConnectionError("Failed to get spines")

        return r.json()['data']['system_nodes']

    def get_system_mac(self, system_id):
        url = self.host + "/systems/" + system_id + "/services/mac/data"

        r = self.s.get(url)
        if r.status_code != 200:
            raise ConnectionError("Failed to get mac address")

        return r.json()['items']

    def get_system_interface(self, system_id):
        url = self.host + "/systems/" + system_id + "/services/interface/data"

        r = self.s.get(url)
        if r.status_code != 200:
            raise ConnectionError("Failed to get mac address")

        return r.json()['items']

# login to AOS Server
s = aos(AOS_SERVER, AOS_USERNAME, AOS_PASSWORD, verify=False)

# get nodes
all_spines = s.get_spines("f9494b44-7d1f-4318-aeb6-167aa051dc1b")
all_leafs = s.get_leafs("f9494b44-7d1f-4318-aeb6-167aa051dc1b")
all_nodes = all_spines + all_leafs

# get mac statistics per vlan per switch
mac_stats = []
mac_table_headers = ["node", "vlan", "mac count"]
for l in all_leafs:
    mac_dict = defaultdict(int)
    m = s.get_system_mac(l['system_id'])

    for mac in m:
        mac_dict[(l['system_id'], mac['identity']['vlan'])] += 1
    for k,v in mac_dict.items():
        mac_stats.append([k[0], k[1], v])

print(tabulate(mac_stats, mac_table_headers))

# get interface status on all switches
interface_stats = []
interfaces_dict = defaultdict(int)
interface_status_dict = {}
for n in all_nodes:
    interfaces = s.get_system_interface(n['system_id'])
    for i in interfaces:
        #just focus on physical interface, ignoring subinterfaces
        if '.' in i["identity"]["interface_name"]:
            continue
        interfaces_dict[(n['system_id'], (i["status"], i["actual"]["value"]))] += 1
        interface_status_dict[(i["status"], i["actual"]["value"])] = None

interface_headers = sorted(interface_status_dict.keys())
for n in all_nodes:
    row = [n['system_id']]
    for s in interface_headers:
        row.append(interfaces_dict[(n['system_id'],s)])
    interface_stats.append(row)
print(tabulate(interface_stats, interface_headers))
