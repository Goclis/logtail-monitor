## 背景
[SLS 服务日志](https://help.aliyun.com/document_detail/85663.html)支持记录 Project 内的用户操作日志等多种日志数据，并提供多种分析维度的仪表盘。在开通此功能后，相关的日志都会被存储到指定位置（project）下的两个特殊 logstore：`internal-operation_log` 以及 `internal-diagnostic_log`，我们可以像操作普通 logstore 一样，对它们进行查询、分析、消费以及构建仪表盘等。

服务日志的开启过程涉及到一系列 SLS 资源的创建，包括 logstore、索引、仪表盘等，因此，目前仅支持通过控制台开启此功能。但考虑到我们需要管理的 project 数量可能会有几十上百个，逐个到控制台开启费时费力，无法满足自动化运维的需求。对此，本文将介绍如何通过日志服务的 API 来实现服务日志功能的开启。


## 准备工作
### 1. SLS CLI 安装
参考[文档](https://aliyun-log-cli.readthedocs.io/en/latest/README_CN.html?spm=a2c4g.11186623.2.9.7f51384cM9fZkG#%E5%AE%89%E8%A3%85)安装或者直接在控制台上打开 CloudShell（入口参考下图）。

![](https://tva1.sinaimg.cn/large/00831rSTly1gdfhtdlxlij30od01caa4.jpg)

### 2. 使用 Git 下载脚本
代码已托管于 [Github](https://github.com/Goclis/logtail-monitor)，可直接下载：

```
$ git clone https://github.com/Goclis/logtail-monitor.git
$ ls -al logtail-monitor/sls_project_logging_ctl.py
```


## 使用说明
针对指定的 project，工具脚本会创建对应的 logstore 来存储服务日志，并对相关的索引/仪表盘进行创建或**更新**（会对当前已存在的配置进行覆盖，请在执行前确认是否会有影响）。

在使用之前，需要修改脚本 `sls_project_logging_ctl.py` 的内容，对以下参数进行配置：

- `access_key_id`：AK 信息，必填。
- `access_key_secret`：AK 信息，必填。
- `region_endpoint`：要开启服务日志的 project 所在 region 的 endpoint，可通过参数指定。
- `project_name`：要开启服务日志的 project 名，可通过参数指定。

可执行 `sls_project_logging_ctl.py -h` 可查看更多相关说明。

**注意：操作日志（internal-operation_log）为收费内容，请根据需要来确认是否开启。**


## 使用示例
### 根据脚本中配置进行开启
```
# 开启所有日志
./sls_project_logging_ctl.py enable all
# 仅开启诊断日志
./sls_project_logging_ctl.py enable internal-diagnostic_log
# 仅开启操作日志
./sls_project_logging_ctl.py enable internal-operation_log
```

### 命令行参数中指定 region/project
```
# 开启所有日志（cn-hangzhou 公网）
./sls_project_logging_ctl.py enable cn-hangzhou.log.aliyuncs.com my-project-name all
# 仅开启诊断日志（cn-shanghai 公网）
./sls_project_logging_ctl.py enable cn-shanghai.log.aliyuncs.com my-project-name internal-diagnostic_log
# 仅开启操作日志（cn-hangzhou 内网）
./sls_project_logging_ctl.py enable cn-hangzhou-intranet.log.aliyuncs.com my-project-name internal-operation_log
```


## 更多阅读
基于服务日志进行 logtail 监控：

- [全方位](https://yq.aliyun.com/articles/691336)
- [心跳最佳实践](https://yq.aliyun.com/articles/727322)
