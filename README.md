# 📘 XiaoquantSystem / 小宽量化

**XiaoquantSystem（小宽量化）** is a modular, scalable, and AI-assisted factor mining framework for quantitative research and portfolio construction.  
**小宽量化**是一个模块化、可扩展并结合 GPT 智能分析的量化因子挖掘与组合评估平台，旨在服务于金融科研人员与量化实盘开发者。

---

## 🧠 Features / 特性亮点

- 🚀 **High-performance Data Layer**: Multi-threaded + distributed data fetching and storage via ClickHouse.  
  **高性能数据层**：使用 ClickHouse 进行多线程（支持分布式）历史数据拉取与存储。
- ✅ **Modular Architecture**: Clean separation of data fetching, factor engine, scoring, and execution.  
  **模块化架构**：清晰分离的数据获取、因子引擎、评分系统和执行模块。
- 📈 **Alpha Factor Framework**: Built-in Alpha101 / Alpha191 support, extendable factor library.  
  **因子框架**：支持 Alpha101 / 191，便于扩展与复用。
- 🤖 **GPT Reporting Engine**: GPT-4o chart interpretation & PDF generation.  
  **GPT 智能分析**：结合 GPT 生成报告和解读图表。
- 🧪 **Backtesting Pipeline**: From factor → score → portfolio → backtest.  
  **完整回测流程**：从因子评分到组合构建与净值回测。
- 🗃️ **AST-based Parser**: Expression parser → AST → validation → execution.  
  **表达式语法树系统**：因子表达式→AST→合法性校验→执行。
- 🖼 **Report Automation**: PDF tear sheet generation with multilingual support.  
  **报告自动化**：生成支持中英文的 PDF 报告。

---

## 📁 Directory Structure / 项目结构

```
XiaoquantSystem/
├── data/
│   ├── alphas/                 # 自定义因子表达式
│   ├── data_ingestion/        # 数据拉取模块（支持 Tushare, Binance 等）
│   ├── data_standardizer/     # 数据标准化处理
│   └── factor_engine/
│       ├── alphas/            # 因子输出文件（csv）
│       ├── core/              # Alpha101/191 主类
│       ├── executor/          # AST 执行器
│       ├── fetcher/           # ClickHouse 适配器
│       ├── factor_analysis/   # Alphalens 分析 + GPT 报告模块
│       ├── portfolio_evaluation/  # 股票评分 → 组合构建 → 回测
│       └── registry/          # 因子注册 / 表达式解析
├── django/                    # 后台管理（Django 后端）
├── exchanges/                 # 交易所适配（A 股、币安）
├── strategies/                # 策略模块
├── trading_execution/         # 执行器模块（订单撮合）
├── docker_composed/           # Docker 启动 ClickHouse + Kafka
├── utils/                     # 项目路径管理、工具函数
└── config.py / .env           # 全局配置 / 环境变量
```


---

## 🚀 Visual Workflow / 可视化流程演示

### 1. Data Ingestion / 数据拉取
![Data Ingestion](https://github.com/mortysean/Xiaoquant/blob/main/docs/images/fa9efa05-fd8e-426f-ac2a-0f9441c573cd.png)

### 2. Factor Computation / 因子计算
![Factor Computation](https://github.com/mortysean/Xiaoquant/blob/main/docs/images/b11bf6c6-e6dd-4dd5-b001-bee9083ac29c.png)

### 3. Factor Analysis / 因子分析
![Factor Alphalens](https://github.com/mortysean/Xiaoquant/blob/main/docs/images/51a7c40b-c256-4f97-b299-5575bd80ea7a.png)
![IC Chart](https://github.com/mortysean/Xiaoquant/blob/main/docs/images/c64e61d3-e6a6-4590-90e0-44a885cfd18d.png)
![Factor Score](https://github.com/mortysean/Xiaoquant/blob/main/docs/images/387711e8-1cd7-4ae1-b45b-b599c30d2f10.png)

### 4. GPT Report Generation / AI 分析报告
![GPT Summary](https://github.com/mortysean/Xiaoquant/blob/main/docs/images/8075411f-0a1c-44de-932a-5435a32efe88.png)
![PDF Report Example](https://github.com/mortysean/Xiaoquant/blob/main/docs/images/c1e28d4d-8584-4ae2-8533-b98e0eea0af8.png)

---

## ⚙️ Quick Start / 快速上手

### 1. 安装依赖
```bash
conda create -n FactorMiner python=3.10 -y
conda activate FactorMiner
pip install -r requirements.txt
```

### 2. 设置环境变量
```bash
# .env 文件
OPENAI_API_KEY='sk-xxx'
XIAOQUANT_ROOT=/your/path/to/XiaoquantSystem
TUSHARE_TOKEN="your_token_here"
```

---

## 🧪 Factor Workflow / 因子工作流

```bash
# Step 1: 数据拉取、因子计算与分析
python data/main.py

# Step 2: 基于因子文件做评分、构建组合、并回测
python data/factor_engine/portfolio_evaluation/main.py
```

---

## 📑 报告自动化

```python
# data/main.py  stop.0 Config
ANALYSIS_MODE = "single"
OUTPUT_PDF = True
```

---

## 📎 TODO / 后续计划

- [ ] 集成 Dash 或 Vue 的前端可视化界面
- [ ] 支持模拟盘交易、交易日志与回测持仓展示
- [ ] 接入美股、数字货币数据源接口（Binance, Yahoo, Alpaca）
- [ ] 多因子组合层策略库（long-short、多因子权重优化）

---

## 👨‍💻 Author / 作者

Developed and maintained by **Sean Huang**  
由 **Sean Huang** 开发并维护 —— 致力于构建未来的开放量化基础设施。

---

## 📜 License

**MIT License** — Free to use, modify and distribute. Attribution appreciated.  
MIT 开源协议，允许自由使用、修改和发布，欢迎引用与标注。
