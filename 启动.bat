@echo off
cd /d "%~dp0"
echo.
echo ============================================
echo   AI 项目提示词生成器 正在启动...
echo   界面将在浏览器中自动打开
echo   如果未自动打开，请手动访问:
echo   http://localhost:8501
echo ============================================
echo.
start http://localhost:8501
streamlit run src/webui.py --server.headless true
