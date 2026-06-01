# Open Campus Matrix

面向校园与组织场景的可信子母 Agent 集群平台。

通过 PQC + 对称加密保护身份和知识，通过离线 Capability 支持边缘自治，通过链上锚定实现版本、权限和审计可验证。

## 与原产品关系

Open Campus Matrix 不是 Open Campus / Metacampus 的替代品，而是**第二产品线**。
原产品负责中心化业务平台（招生、运营、RAG、CRM、合规审计），Matrix 负责分布式可信智能协作。

## 目录结构

```
products/matrix/
├── docs/                          # 产品文档
├── matrix-protocols/              # Agent Identity、Capability、Manifest、Audit 协议 Schema
├── mother-control-plane/          # Mother Agent Gateway (Go)
├── child-agent-runtime/           # Child Agent Runtime (Python)
├── knowledge-pack-builder/        # 加密知识包构建 (Python)
├── adapters/                      # 原产品 Adapter（知识导出、策略导出、审计导入）
└── matrix-console/               # Matrix 管理控制台 (React/TypeScript)
└── usb_distribution/             # Open Campus Matrix USB Edition 打包器
```

## 快速开始

```bash
# Mother Agent API
cd products/matrix/mother-control-plane
go run ./cmd/matrix-mother

# Child Agent CLI
cd products/matrix/child-agent-runtime
python -m child_agent_runtime register --mother-url http://localhost:18080
python -m child_agent_runtime sync
python -m child_agent_runtime run-offline
python -m child_agent_runtime upload-audit
```

## 安全模型

- **身份**: ML-DSA-65 签名密钥对
- **密钥封装**: ML-KEM-768 封装知识包 DEK
- **数据加密**: AES-256-GCM 加密知识包和本地缓存
- **密钥派生**: HKDF-SHA384 会话密钥派生
- **哈希**: SHA-384 / BLAKE3 用于 Merkle Root 和内容寻址

## USB Edition 分发包

```bash
python -m pip install -r products/matrix/usb_distribution/requirements.txt
python products/matrix/usb_distribution/build_usb_bundle.py --smoke --zip
```

生成目录位于 `products/matrix/dist/OPEN_CAMPUS_MATRIX_USB/`，压缩包位于
`products/matrix/dist/open_campus_matrix_usb_edition_v0.1.zip`。该包包含本地
runtime、离线 Mother/Child Agent 配置、ML-KEM-768 封装 DEK、AES-256-GCM 加密
知识包、ML-DSA-65 签名 manifest、离线审计日志和模拟联网同步入口。
