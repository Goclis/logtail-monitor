#!/usr/bin/env python
# -*- encoding:utf-8 -*-
import sys
import os
import time
import json


# Configurations
access_key_id = ''
access_key_secret = ''
region_endpoint = ''
project_name = ''
disable_output = True


cfg_dir = 'logging_config'
resource_map = {
    'internal-operation_log': {
        'with_index': True,
        'dashboards': ['internal_operation_statistics'],
        'types': ['operation_log']
    },
    'internal-diagnostic_log': {
        'with_index': True,
        'dashboards': [
            'internal_logtail_monitoring',
            'internal_consumer_group_monitoring',
            'internal_logtail_statistics'
        ],
        'types': [
            'consumergroup_log',
            'logtail_alarm',
            'logtail_profile',
            'logtail_status'
        ]
    }
}


def info_print(data) :
    print '\033[92m' + data + '\033[0m'


def error_print(data) :
    print '\033[91m' + data + '\033[0m'


def exec_aliyunlog_cli(subcmd):
    cmd = 'aliyunlog log %s --access-id=%s --access-key=%s --region-endpoint=%s' \
        % (subcmd, access_key_id, access_key_secret, region_endpoint)
    if disable_output:
        cmd += ' > /dev/null'
    return os.system(cmd)


def create_resources(logging_type):
    if exec_aliyunlog_cli('get_project --project_name=%s' % project_name):
        raise RuntimeError('project %s is not existing' % project_name)

    info_print('create/update SLS resources for project %s' % project_name)
    logstore_name = logging_type
    resource_cfg = resource_map[logstore_name]
    if exec_aliyunlog_cli('get_logstore --project_name=%s --logstore_name=%s'
        % (project_name, logstore_name)):
        info_print('logstore %s is not existing, create it' % logstore_name)
        if exec_aliyunlog_cli('create_logstore --project_name=%s --logstore_name=%s'
            % (project_name, logstore_name)):
            raise RuntimeError('create logstore %s error, abort' % logstore_name)

    if resource_cfg['with_index']:
        index_cfg_file = os.path.join(cfg_dir, '%s_index_config.json' % logstore_name)
        if exec_aliyunlog_cli('get_index_config --project_name=%s --logstore_name=%s'
            % (project_name, logstore_name)):
            info_print('index for logstore %s is not existing, create it' % logstore_name)
            if exec_aliyunlog_cli('create_index --project_name=%s --logstore_name=%s --index_detail="$(cat %s)"'
                % (project_name, logstore_name, index_cfg_file)):
                raise RuntimeError('create index for logstore %s error, abort' % logstore_name)
        else:
            info_print('index for logstore %s is existing, update it' % logstore_name)
            if exec_aliyunlog_cli('update_index --project_name=%s --logstore_name=%s --index_detail="$(cat %s)"'
                % (project_name, logstore_name, index_cfg_file)):
                error_print('update index for logstore %s error, skip' % logstore_name)

    for name in resource_cfg['dashboards']:
        dashboard_cfg_file = os.path.join(cfg_dir, '%s_dashboard_config.json' % name)
        if exec_aliyunlog_cli('get_dashboard --project=%s --entity=%s' % (project_name, name)):
            info_print('dashboard %s is not existing, create it' % name)
            if exec_aliyunlog_cli('create_dashboard --project=%s --detail="$(cat %s)"'
                % (project_name, dashboard_cfg_file)):
                raise RuntimeError('create dashboard %s error, abort' % name)
        else:
            info_print('dashboard %s is existing, update it' % name)
            if exec_aliyunlog_cli('update_dashboard --project=%s --detail="$(cat %s)"'
                % (project_name, dashboard_cfg_file)):
                info_print('update dashboard %s error, skip' % logstore_name)


def exec_logging_cli(method, config=''):
    cli_path = 'tools/logging_cli/logging_cli'
    if sys.platform == 'darwin':
        cli_path += '_darwin'
    cmd = './%s -project=%s -endpoint=%s -access-key-id=%s -access-key-secret=%s -method=%s -config="%s"' \
        % (cli_path, project_name , region_endpoint, access_key_id, access_key_secret, method, config)
    if disable_output:
        cmd += ' > /dev/null'
    return os.system(cmd)


def create_logging(logging_types):
    info_print('create logging for project %s' % project_name)
    logging = {
        'loggingProject': project_name,
        'loggingDetails': []
    }
    for log_type in logging_types:
        for tn in resource_map[log_type]['types']:
            logging['loggingDetails'].append({
                'type': tn,
                'logstore': log_type
            })
    config = json.dumps(logging)
    file_path = 'logging_config_temp.json'
    with open(file_path, 'w') as fh:
        fh.write(config)

    if exec_logging_cli('get'):
        info_print('logging is not existing, create it')
        if exec_logging_cli('create', file_path):
            raise RuntimeError('create logging error, abort')
    else:
        info_print('logging is existing, update it')
        if exec_logging_cli('update', file_path):
            raise RuntimeError('update logging error, abort')


def enable_loggings(type_name):
    types = [type_name] if type_name != 'all' else list(resource_map.keys())
    for name in types:
        create_resources(name)
    create_logging(types)


def print_usage():
    print 'Usage: ./sls_project_logging_ctl.py enable [<region_endpoint>] [<project_name>] <logging_type>'
    print ''
    print 'Options:'
    print '  <region_endpoint>: such as cn-hangzhou.log.aliyuncs.com, cn-shanghai-intranet.log.aliyuncs.com'
    print '                     see https://help.aliyun.com/document_detail/29008.html for more.'
    print '  <project_name>: the name of your SLS project'
    print '  <logging_type>: "internal-operation_log" for operation logs'
    print '                  "internal-diagnostic_log" for diagnostic logs, such as logtail and consumer group status'
    print '                  "all"'
    print ''
    print 'Examples:'
    print '  # Use region endpoint and project in configurations'
    print '  ./sls_project_logging_ctl.py enable all'
    print '  # Enable all kinds of SLS logging for project named my-project-name at region cn-hangzhou.'
    print '  ./sls_project_logging_ctl.py enable cn-hangzhou.log.aliyuncs.com my-project-name all'
    print '  # Enable diagnostic logs only for project named my-project-name at region cn-shanghai.'
    print '  ./sls_project_logging_ctl.py enable cn-shanghai.log.aliyuncs.com my-project-name internal-diagnostic_log'


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] in ['-h', '--help']:
        print_usage()
        sys.exit(0)

    if len(sys.argv) != 3 and len(sys.argv) != 5:
        error_print('[ERROR] invalid count of parameters')
        print_usage()
        sys.exit(1)

    subcmd = sys.argv[1]
    if subcmd != 'enable':
        error_print('[ERROR] unsupported sub command: %s' % subcmd)
        print_usage()
        sys.exit(1)

    if len(sys.argv) == 3:
        logging_type = sys.argv[2]
    elif len(sys.argv) == 5:
        region_endpoint = sys.argv[2]
        project_name = sys.argv[3]
        logging_type = sys.argv[4]

    if (not access_key_id or not access_key_secret
        or not region_endpoint or not project_name):
        error_print('please set configurations at the beginning of file')
        sys.exit(1)

    if logging_type != 'all' and logging_type not in resource_map:
        error_print('[ERROR] invalid logging type: %s' % logging_type)
        print_usage()
        sys.exit(1)

    enable_loggings(logging_type)