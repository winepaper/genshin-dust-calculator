# 开发、构建和发布

项目以Python 3.13及固定版本依赖构建。运行依赖与开发依赖分开。
建议在独立虚拟环境中安装 `requirements-dev.txt`，勿混用其他Qt绑定。

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe verify.py
.\.venv\Scripts\python.exe tests/gui_check.py
.\build.ps1 -Python .\.venv\Scripts\python.exe
```

可使用 `-OutputName` 指定EXE名称。未指定时输出 `dist/GenshinDustCalculator.exe`。
打包只在Windows进行，使用仓库的 `calculator.spec`。
隔离DLL搜索、统一VC运行库、排除私有ucrtbase.dll的规则不得随意移除。

`python tools/frozen_check.py dist/GenshinDustCalculator.exe` 实际运行成品、
核对独立结果并捕获两套主题。仅源代码测试通过不能证明成品DLL能加载。

CI的 `model` 作业不需第三方库；`windows` 作业安装固定依赖并测试和构建。
源码测试与CI构建均不要求原神账号、GitHub个人token或其他项目秘密。
GitHub Action引用固定提交，工作流权限按任务限制。

发布前更新 `engine.VERSION`、界面版本、README及CHANGELOG，并核对生成物。
推送形如 `v2.1.0` 的标签后，发布工作流在Windows构建EXE、ZIP、校验和，
并上传到相应GitHub Release。发布手动触发时使用当前 `engine.VERSION`。
若已有同版本发行版，工作流更新其文件，不创建第二个版本号。

发行包包含EXE、示例配置、用户及模型说明、项目许可证和第三方许可证。
源码由GitHub为发布标签自动提供，生成的EXE不提交到Git历史。
