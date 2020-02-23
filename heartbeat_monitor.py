#!/usr/bin/env python
# -*- encoding:utf-8 -*-
import json
import time
import sys
import os
from aliyun.log import LogClient, PutLogsRequest, LogItem


class LogtailHeartbeatMonitor:
    def __init__(self):
        # SLS 项目名，其中所有的机器组都会被监控。
        self.__project_name = '<your_sls_project_name>'
        # SLS 项目所属区域的 endpoint。
        self.__endpoint = '<endpoint_of_your_sls_project_region>'  # cn-hangzhou.log.aliyuncs.com
        # 心跳超时阈值（秒），超过此阈值的机器可能存在异常，默认为 15 分钟，可根据需求调整。
        self.__hb_timeout_threshold = 15 * 60
        # 服务日志项目名：存放指定服务日志的 SLS 项目。
        self.__logtail_status_project_name = '<status_log_project_name>'  # log-service-<your_aliuid>-<region_name>
        # 状态日志查询的时间范围（秒），默认为最近 10 分钟。
        self.__query_range = 10 * 60
        # 状态日志数阈值：每分钟一条，10 分钟内少于此阈值判定为异常。
        self.__status_log_count_threshold = 8  # at least 8 status logs during recent 10 minutes.
        # 用于上报异常信息的 project/logstore，为空表示不上报至 SLS。
        self.__report_project_name = self.__project_name  # same project by default
        self.__report_logstore = ''

        self.__client = LogClient(
            endpoint=self.__endpoint,
            accessKeyId='',  # access key to call SLS APIs.
            accessKey='')

    def inspect(self):
        abnormal_machines = self.__do_inspect()
        if abnormal_machines:
            print 'abnormal machines are found: '
            print json.dumps(abnormal_machines, indent=True)
            self.__report({
                'type': 'abnormal_machines',
                'count': len(abnormal_machines),
                'machines': ','.join(abnormal_machines.keys())
            })
            sys.exit(1)

    def __do_inspect(self):
        machine_groups = self.__client.list_machine_group(self.__project_name, offset=0, size=-1).get_machine_group()
        if not machine_groups:
            print 'no machine group in project %s' % self.__project_name
            return
        print 'machine groups (count %s): %s' % (len(machine_groups), machine_groups)

        hb_timeout_machines = {}
        for m in machine_groups:
            machines = self.__inspect_machine_group(m)
            for ip, meta in machines.items():
                if ip not in hb_timeout_machines:
                    hb_timeout_machines[ip] = meta
        print 'heartbeat timeout machines (count %s): %s' % (len(hb_timeout_machines),
                                                             hb_timeout_machines.keys()[0: 10])
        if not hb_timeout_machines:
            return

        abnormal_machines = {}
        machine_status_count = self.__count_status_log(hb_timeout_machines.keys())
        for machine_ip, machine_meta in hb_timeout_machines.items():
            log_count = machine_status_count.get(machine_ip, 0)
            if log_count < self.__status_log_count_threshold:
                machine_meta['status_log_count'] = log_count
                abnormal_machines[machine_ip] = machine_meta
            else:
                print 'log count of machine %s: %s' % (machine_ip, log_count)
        return abnormal_machines

    def __report(self, report_data):
        """
        Args:
            report_data: dict[string]string.
        """
        if not self.__report_logstore:
            return
        log = LogItem()
        for key, data in report_data.items():
            log.push_back(key, '%s' % data)
        req = PutLogsRequest(project=self.__project_name, logstore=self.__report_logstore, logitems=[log])
        self.__client.put_logs(req)

    def __inspect_machine_group(self, group_name):
        abnormal_machines = {}
        machines = self.__client.list_machines(self.__project_name, group_name).get_machines()
        cur_time = int(time.time())
        for machine_status in machines:
            if cur_time - machine_status.heartbeat_time >= self.__hb_timeout_threshold:
                abnormal_machines[machine_status.ip] = {
                    'group_name': group_name,
                    'last_heartbeat_time': machine_status.heartbeat_time
                }
        return abnormal_machines

    def __count_status_log(self, machines):
        count_rst = {}
        batch_count = 25
        for batch_seq in range(0, len(machines) / batch_count + 1):
            batch_machines = machines[batch_count * batch_seq: batch_count * (batch_seq + 1)]
            ip_condition = ' or '.join(['ip:' + ip for ip in batch_machines])
            query = '__topic__: logtail_status and (%s) | select ip, count(*) as c group by ip' % ip_condition
            try:
                res = self.__do_get_log(project=self.__logtail_status_project_name,
                                        logstore='internal-diagnostic_log',
                                        query=query,
                                        from_time=int(time.time()) - self.__query_range,
                                        to_time=int(time.time()))
                for log in res.get_logs():
                    ip, count = log.contents['ip'], log.contents['c']
                    count_rst[ip] = count
            except Exception as e:
                self.__report({
                    'type': 'get_log_error',
                    'query': query,
                    'err': e.message
                })
        return count_rst

    def __do_get_log(self, project, logstore, query, from_time, to_time):
        err_msg = ''
        for idx in range(0, 10):
            try:
                res = self.__client.get_log(project=project, logstore=logstore,
                                            query=query, from_time=from_time, to_time=to_time)
                if not res.is_completed():
                    err_msg += '[%s] incomplete' % idx
                    continue
                return res
            except Exception as e:
                err_msg += '[%s] get_log error: %s\n' % (idx, e)
            finally:
                time.sleep(1)
        raise err_msg


if __name__ == '__main__':
    # 保证系统中同时只有一个进程在巡检。
    name = os.path.basename(sys.argv[0])
    cmd = ('c=`ps -ef | grep "%s"$ | grep -v vim | grep -v grep | wc -l`;'
           'if [ $c -ne 1 ]; then exit 1; fi' % name)
    if os.system(cmd):
        sys.exit(1)

    LogtailHeartbeatMonitor().inspect()
