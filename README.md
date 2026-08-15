# 22 家每日打卡（GitHub Actions）

脚本会依次处理 22 家单位，每家完成后等待 10 秒；默认不保存截图。运行结束后会通过 Bark 推送成功/失败汇总。

## 上传到 GitHub

1. 在 GitHub 新建一个**私有仓库**。
2. 将本文件夹内的全部文件上传到仓库根目录，保留 `.github/workflows/daily-checkin.yml` 的目录结构。
3. 打开仓库的 `Settings` -> `Secrets and variables` -> `Actions`，新增两个 Repository secrets：

   - `CHECKIN_PASSWORD`：统一登录密码。
   - `BARK_URL`：Bark 的基础地址，例如 `https://api.day.app/你的设备密钥`。不要在地址后附加推送内容。

4. 打开仓库的 `Actions` 页，选择 `Daily Check-in`，点击 `Run workflow` 先手动测试一次。

## 自动运行时间

工作流默认每天北京时间 06:35 运行。GitHub 的定时任务偶尔会有几分钟延迟；如需换时间，修改 `.github/workflows/daily-checkin.yml` 中的 cron 表达式。

## 本地运行

PowerShell 中设置环境变量后运行：

```powershell
$env:CHECKIN_PASSWORD = "你的统一密码"
$env:BARK_URL = "https://api.day.app/你的设备密钥"
python -m pip install -r requirements.txt
python -m playwright install chromium
python daily_checkin_22_units.py
```

袁记家常菜手机号暂按 `15150544420` 配置；如实际号码不同，请只修改脚本中该单位的 `username`。
