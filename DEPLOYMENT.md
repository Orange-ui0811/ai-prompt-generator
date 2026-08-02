# 三平台部署说明

本项目共用同一套 `src/`、`templates/` 和 `config/` 生成逻辑，并针对不同平台提供两个网页入口：

- Vercel：`app.py`（FastAPI）+ `public/index.html`
- Streamlit Community Cloud：`src/webui.py`
- Render：`render.yaml` 启动 `src/webui.py`

## 1. 部署到 Vercel

1. 把当前目录的修改提交并推送到 GitHub。
2. 登录 Vercel，点击 **Add New → Project**。
3. 导入当前 GitHub 仓库。
4. Framework Preset 保持 **Other**，Root Directory 保持仓库根目录。
5. 不填写 Build Command、Output Directory 和 Install Command，直接点击 **Deploy**。

Vercel 会自动发现根目录的 `app.py`，并将其中名为 `app` 的 FastAPI 应用作为入口。部署完成后可访问：

- `/`：提示词生成网页
- `/api/health`：健康检查
- `/docs`：FastAPI 接口调试页面

如果需要 AI 增强，在 Vercel 项目的 **Settings → Environment Variables** 添加：

```text
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL
```

添加后需要重新部署。没有配置这些变量时，关闭网页中的“使用 AI 增强”，仍可正常使用模板生成。

## 2. 部署到 Streamlit Community Cloud

1. 打开 <https://share.streamlit.io/> 并登录。
2. 点击 **Create app**。
3. 选择当前仓库和分支。
4. Main file path 填写：

```text
src/webui.py
```

5. 点击 **Deploy**。

如需 AI 增强，在应用设置的 **Secrets** 中添加：

```toml
LLM_API_KEY = "你的密钥"
LLM_BASE_URL = "OpenAI 兼容接口地址"
LLM_MODEL = "模型名称"
```

Streamlit 页面中填写的项目资料会保存在当前会话和实例文件中。云端实例重启后，本地文件可能被清空，请及时下载生成结果。

## 3. 部署到 Render

仓库根目录已提供 `render.yaml`，推荐通过 Blueprint 创建：

1. 登录 Render，点击 **New → Blueprint**。
2. 连接当前 GitHub 仓库。
3. Render 会读取 `render.yaml`，点击 **Apply**。
4. 在服务的 **Environment** 页面填写需要的环境变量，然后重新部署。

Blueprint 使用以下设置：

```text
Build Command: pip install -r requirements.txt
Start Command: streamlit run src/webui.py --server.address 0.0.0.0 --server.port $PORT --server.headless true
Health Check: /_stcore/health
```

也可以不用 Blueprint，手动新建 Python Web Service，然后填写相同的 Build Command 和 Start Command。

## 本地检查

### Streamlit 页面

```bash
streamlit run src/webui.py
```

### Vercel/FastAPI 页面

```bash
uvicorn app:app --reload
```

浏览器打开 <http://127.0.0.1:8000/>。

### 测试

```bash
pytest tests/ -v
```

## 文件保存说明

Vercel 函数不依赖服务器本地文件保存用户资料，Vercel 网页会使用浏览器 `localStorage` 自动保存九项项目信息。Render 和 Streamlit Community Cloud 的文件系统也不应当被当作永久数据库；如果以后需要跨设备、跨用户保存，可再连接数据库。
