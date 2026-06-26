# 免费节点订阅

自动化抓取、合并去重、每日更新的免费节点订阅服务。

## 订阅地址

| 类型 | 格式 | 地址 |
|------|------|------|
| Clash / Mihomo | YAML | `https://kunkun8888666.github.io/youyapai/output/clash.yaml` |
| V2Ray | URI 列表 | `https://kunkun8888666.github.io/youyapai/output/v2ray.yaml` |

## 数据来源

- [yoyapai.com](https://yoyapai.com/category/mianfeijiedian)
- [clash-rs.com](https://clash-rs.com/free-node/)

## 工作原理

1. GitHub Actions 每日北京时间 07:00 自动执行爬虫脚本
2. 从上述来源抓取近 3 天的免费节点订阅内容
3. 解析 Clash YAML 和 V2Ray URI 格式的节点
4. 按 (server, port, protocol) 三元组去重
5. 生成标准格式的配置文件并推送到仓库
6. 通过 GitHub Pages 对外提供订阅服务

## 使用方法

### Clash / Mihomo

1. 复制 Clash 订阅地址
2. 打开 Clash 客户端（推荐 Clash Verge Rev / Mihomo Party）
3. 在「配置」页面粘贴订阅地址并导入
4. 开启系统代理，选择节点

详细教程：[Clash 客户端教程](https://kunkun8888666.github.io/youyapai/clash.html)

### V2Ray

1. 复制 V2Ray 订阅地址
2. 打开 V2Ray 客户端（推荐 V2RayN / V2RayNG / Shadowrocket）
3. 在订阅设置中添加地址并更新
4. 选择节点并连接

详细教程：[V2Ray 客户端教程](https://kunkun8888666.github.io/youyapai/v2ray.html)

## 项目结构

```
├── .github/workflows/
│   └── fetch-nodes.yml      # GitHub Actions 定时任务
├── scripts/
│   └── fetch_nodes.py        # 爬虫脚本
├── output/
│   ├── clash.yaml            # Clash 配置文件
│   ├── v2ray.yaml            # V2Ray 订阅文件
│   └── stats.json            # 节点统计信息
├── index.html                # 首页
├── clash.html                # Clash 教程页
├── v2ray.html                # V2Ray 教程页
└── requirements.txt          # Python 依赖
```

## 免责声明

本项目仅供学习与技术研究用途，无意传播或倡导任何违反法律法规的行为。用户须自行了解所在地法律法规，合法合规使用；因使用不当产生的法律责任，与本站及作者无关。
