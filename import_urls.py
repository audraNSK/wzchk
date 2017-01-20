import urllib.request
import config
from pyzabbix import ZabbixAPI, ZabbixAPIException


def get_url_list(listhost):
    response = urllib.request.urlopen(listhost)
    hosts = response.read().decode('utf-8')
    hosts_list = hosts.split()
    return hosts_list

def get_urls_from_host(zapi, hostid):
    urls = []
    web_scenarios = zapi.httptest.get(selectSteps = 'extend', hostids = hostid)
    for scenario in web_scenarios:
        for step in scenario['steps']:
            urls.append(step['url'])
    return urls

def add_urls_to_host(zapi, urls, hostid, hostname):
    for url in urls:
        try:
            zapi.httptest.create(name = url, hostid = hostid,
                                    steps = [{'name': url, 'url': url,
                                              'status_codes' : '1-499' }])
            zapi.trigger.create(
                description = 'Scenario '+url+' on host '+hostname,
                priority = '3',
                expression = '{'+hostname+':web.test.fail['+url+'].last()}<>0')
        except ZabbixAPIException as ex:
            print(ex)

def get_hosts_name_id(zapi, groupid = config.zabbix_group_id):
    result = {}
    hosts = zapi.host.get(output = 'extend', grpupids = groupid)
    for h in hosts:
        result[h['name']] = h['hostid']
    return result



zapi = ZabbixAPI(config.zabbix_api_url)
zapi.login(config.zabbix_username, config.zabbix_password)

# get all hosts in prconfigured zabbix server hostgroup
hosts =  get_hosts_name_id(zapi)

for h in hosts:
    list_url = config.list_url_base + h.split(config.hostname_separator)[0]
    urls = get_url_list(list_url)
    add_urls_to_host(zapi, urls, hosts[h], h)
