# Taste-Chang

常州美食排行榜：Flask API + Vite/Vue 3 前端。

- 后端 API：`http://127.0.0.1:8999`
- 前端页面：`http://127.0.0.1:9000`

## 开发

终端 1（后端）：

```bash
pip install -r requirements.txt
python main.py
```

终端 2（前端）：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 **http://127.0.0.1:9000/**  
前端会把 `/api` 代理到 `8999`。

## 生产预览

```bash
cd frontend
npm run build
npm run preview
```

同时保持 `python main.py` 在 8999 运行，然后访问 http://127.0.0.1:9000/
