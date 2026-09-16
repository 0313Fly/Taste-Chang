# Taste-Chang

常州美食排行榜：Flask API + Vite/Vue 3 前端。

- 后端 API：`http://127.0.0.1:8999`
- 前端页面：`http://127.0.0.1:9000`
- **需先注册/登录**才能查看榜单
- 普通用户：浏览、搜索、今晚吃什么、给饭店打分（每店一次，可修改）
- 公共评分 = 所有用户评分的平均
- 管理员：还可新增 / 编辑 / 删除


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
