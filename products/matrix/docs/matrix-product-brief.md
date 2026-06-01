# Open Campus Matrix 产品简介

## 一句话定义

Open Campus Matrix 是一个面向校园与组织场景的可信子母 Agent 集群平台，通过 PQC + 对称加密保护身份和知识，通过离线 Capability 支持边缘自治，通过链上锚定实现版本、权限和审计可验证。

## 核心定位

| 维度 | 现有产品：Open Campus / Metacampus | 新产品：Open Campus Matrix |
|---|---|---|
| 核心定位 | 校园招生、校园运营、知识检索、合规审计、CRM | 子母 Agent 集群，可信自治、离线运行、加密知识包 |
| 系统形态 | Go Control Plane + Python Capability Services | Mother Agent + Child Agent Runtime + Encrypted Knowledge Mesh |
| 运行条件 | 主要在线运行 | 联网同步，离线按本地授权执行 |
| 安全模型 | 中心化认证、路由合约、审计 | PQC 身份、PQC 密钥封装、对称加密知识包、链上锚定 |

## 与原产品关系

- **不覆盖原产品**：原产品继续作为中心化业务平台运行
- **不破坏原产品**：只通过 Adapter 单向导出授权数据
- **不污染原产品**：Matrix 代码在 `products/matrix/` 独立目录，不 import 原业务模块

## 目标用户

- 学校 IT 管理员、边缘节点管理员
- 跨校区协作团队
- 开发者、科研团队
- 隐私敏感机构（政府、企业）

## 产品线

| 版本 | 目标客户 | 卖点 |
|---|---|---|
| Matrix Edge | 学校、校区、展厅、招生点 | 离线校园问答、低联网环境稳定运行 |
| Matrix Secure | 政府、企业、隐私敏感机构 | PQC 加密、权限隔离、可审计知识分发 |
| Matrix Developer | 开发者、科研团队 | 子母 Agent SDK、知识包协议、插件能力 |
| Matrix Mesh | 多校区/多组织网络 | 跨节点知识同步、版本锚定、分布式审计 |
