import urllib.request
import config
from pyzabbix import ZabbixAPI, ZabbixAPIException


def get_url_set(listhost):
    response = urllib.request.urlopen(listhost)
    hosts = response.read().decode('utf-8')
    hosts_list = hosts.split()
    return set(hosts_list)

def get_urls_from_host(zapi, hostid):
    urls =  set()
    web_scenarios = zapi.httptest.get(selectSteps = 'extend', hostids = hostid)
    for scenario in web_scenarios:
        for step in scenario['steps']:
            if scenario['status'] == '0':          # enabled
                urls.add(step['url'])
    return urls


def get_scenario_id(zapi, hostid, name):
    webscenarios = zapi.httptest.get(hostids = hostid)
    scenario = dict(
        list(
            filter(lambda s: s['name'] == name, webscenarios)
        )[0])   # We assume that scenario name is unique in host!
    return scenario['httptestid']


def get_trigger_id(zapi, hostid, description):
    triggers = zapi.trigger.get(hostids = hostid)
    trigger = dict(
        list(
            filter(lambda t: t['description'] == description, triggers)
        )[0])    # description must be unique in host!
    return trigger['triggerid']


def get_trigger_description(url, hostname):
    return 'Scenario '+url+' on host '+hostname


def add_urls_to_host(zapi, urls, hostid, hostname):
    for url in urls:
        trigger_description = get_trigger_description(url, hostname)
        try:
            zapi.httptest.create(
                name = url,
                hostid = hostid,
                steps = [{
                    'name': url,
                    'url': url,
                    'status_codes' : config.http_status_codes_ok }])
        except ZabbixAPIException as ex:
            scenarioid = get_scenario_id(zapi, hostid, url)
            zapi.httptest.update(httptestid = scenarioid , status = '0')
            #print(ex)

        try:
            zapi.trigger.create(
                description = trigger_description,
                priority = '3',
                expression = '{'+hostname+':web.test.fail['+url+'].last()}<>0')
        except ZabbixAPIException as ex:
            triggerid = get_trigger_id(zapi, hostid, trigger_description)
            zapi.trigger.update(triggerid = triggerid, status = '0')
            #print(ex)


def disable_urls_on_host(zapi, urls, hostid, hostname):
    for url in urls:
        trigger_description = get_trigger_description(url, hostname)

        try:
            scenarioid = get_scenario_id(zapi, hostid, url)
            zapi.httptest.update(httptestid = scenarioid , status = '1')
        except ZabbixAPIException as ex:
            print(ex)

        try:
            triggerid = get_trigger_id(zapi, hostid, trigger_description)
            zapi.trigger.update(triggerid = triggerid, status = '1')
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
# dict name -> ID
hosts =  get_hosts_name_id(zapi)

for h in hosts:
    # hostname separator is used to drop suffix in zabbix host object.
    list_url = config.list_url_base + h.split(config.hostname_separator)[0]
    urls = get_url_set(list_url)
    current_urls = get_urls_from_host(zapi, hosts[h])
    add_urls_to_host(zapi, urls - current_urls, hosts[h], h)
    disable_urls_on_host(zapi, current_urls - urls, hosts[h], h)

