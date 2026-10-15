# AI数字人直播系统 V0.4

本目录是内部测试交付包。业务代码、模型、Avatar、数据库结构、知识库和测试数据均来自已验收版本；交付整理仅进行了密钥脱敏、缓存清理和文档补充。

## 已实现功能

- AI数字人直播
- WebRTC视频流
- Wav2Lip口型同步
- Edge TTS语音
- AI弹幕回复
- qwen3.7-plus大模型
- RAG知识库
- Chroma向量检索
- Persona主播人格
- 自动话术
- HIGH/LOW优先级队列
- Analytics直播统计

## 环境要求

- Windows
- Python 3.10+
- Node.js 20+
- CUDA
- NVIDIA显卡
- Miniconda或Anaconda

## Conda环境

项目使用以下已有环境名称：

- `livetalking`
- `livestream`

交付包不包含 Conda 环境和前端 `node_modules`。接收方需要准备兼容环境，并在前端首次启动前安装依赖。

## 首次配置

出于安全原因，交付数据库中的 LLM API Key 和 Embedding API Key 已清空。

1. 参考根目录 `.env.example` 准备自己的测试密钥。
2. 当前 LiveStream 的业务配置保存在数据库 `app_settings` 表中，请启动系统后在前端“系统配置”页面填写测试 Key。
3. 模型保持 `qwen3.7-plus`，Embedding 模型保持 `text-embedding-v4`。
4. LiveTalking 地址保持 `http://127.0.0.1:8010`。

不要把包含真实密钥的数据库或配置文件再次对外分发。

## 启动顺序

### 第一步：启动数字人

```bat
conda activate livetalking
cd LiveTalking
python app.py
```

默认运行地址：`http://127.0.0.1:8010`

### 第二步：启动后端

打开新的命令行窗口：

```bat
conda activate livestream
cd LiveStream\backend
uvicorn app.main:app --reload
```

默认访问地址：

- 后端：`http://127.0.0.1:8000`
- API文档：`http://127.0.0.1:8000/docs`

### 第三步：启动前端

打开新的命令行窗口：

```bat
cd LiveStream\frontend
npm install
npm run dev
```

浏览器访问：`http://localhost:5173`

## 使用注意事项

- 不要直接打开 LiveTalking 官方页面创建播放 Session。
- 只通过 LiveStream Dashboard 的“连接数字人”功能使用数字人。
- 浏览器看到的 Session 应与 Backend 当前绑定的 Session 保持一致。
- 首次启动后先确认 8010、8000、5173 三个端口正常，再开始直播测试。
- API Key 已脱敏；未配置测试 Key 时，LLM回复和Embedding功能无法正常调用。

## 建议验收顺序

1. Dashboard 能显示数字人 WebRTC 画面。
2. 测试文本能触发 Edge TTS 和 Wav2Lip 口型。
3. Mock弹幕能够进入 HIGH Queue 并生成AI回复。
4. 无弹幕时，启用话术能够进入 LOW Queue 自动播报。
5. 知识库问题能够通过 RAG 返回资料内答案。
6. `/api/analytics/live/current` 能返回当前直播统计。
