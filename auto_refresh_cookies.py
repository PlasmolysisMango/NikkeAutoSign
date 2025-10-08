import json
import logging
import os
import random
import subprocess
import time

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from common import COOKIES_FILE_PATH, ACCOUNT_FILE_PATH

_LOGGER = logging.getLogger(__name__)

# 要访问的网站
LOGIN_URL = "https://www.blablalink.com/login"

# Cookie 列表（已解析）
LOGIN_COOKIES = [
    {'name': 'OptanonAlertBoxClosed', 'value': '2025-08-30T08:32:13.551Z', 'domain': 'www.blablalink.com', 'path': '/'},
    {'name': '__ss_storage_cookie_cache_game_id__', 'value': '29080', 'domain': 'www.blablalink.com', 'path': '/'},
    {'name': '__ss_storage_cookie_cache_lang__', 'value': 'zh-TW', 'domain': 'www.blablalink.com', 'path': '/'},
]


def load_account(file_path):
    with open(file_path, 'r') as f:
        dic = json.load(f)
    return dic["EMAIL"], dic["PASSWORD"]


def load_server(file_path):
    with open(file_path, 'r') as f:
        dic = json.load(f)
    server = os.getenv("SERVER") or dic["SERVER"]
    port = os.getenv("PORT") or dic["PORT"]
    return server, port


def login(username, password):
    # 配置 Edge 选项
    options = webdriver.EdgeOptions()
    # options.add_argument("--headless")  # 可选：无头模式运行
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # 使用 webdriver_manager 自动管理驱动（推荐）或指定本地路径
    # service = Service(EdgeChromiumDriverManager().install())
    # 或者使用本地路径：
    service = Service(executable_path="./edgedriver_win64/msedgedriver.exe")

    # 启动浏览器
    driver = webdriver.Edge(service=service, options=options)
    try:
        # 必须先访问目标域名，才能设置同源 Cookie
        driver.get("https://www.blablalink.com/")

        # 清除可能存在的旧 cookie（可选）
        # driver.delete_all_cookies()

        # 添加每个 cookie
        for cookie in LOGIN_COOKIES:
            try:
                # 移除 domain 字段（有时会导致 InvalidCookieDomainException）
                safe_cookie = cookie.copy()
                if 'domain' in safe_cookie:
                    del safe_cookie['domain']
                driver.add_cookie(safe_cookie)
                _LOGGER.info(f"成功添加 Cookie: {safe_cookie['name']}")
            except Exception as e:
                _LOGGER.info(f"无法添加 Cookie {cookie.get('name', 'unknown')}: {e}")

        # 直接跳转到登录页或目标页（Cookie 已生效）
        driver.get(LOGIN_URL)

        wait = WebDriverWait(driver, 30)

        # ========== 1. 输入账号 ==========
        email_input = wait.until(
            EC.presence_of_element_located((By.ID, "loginPwdForm_account"))
        )
        email_input.clear()
        # 模拟人类输入速度
        for char in username:
            email_input.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))

        # ========== 2. 输入密码 ==========
        password_input = wait.until(
            EC.presence_of_element_located((By.ID, "loginPwdForm_password"))
        )
        password_input.clear()
        for char in password:
            password_input.send_keys(char)
            time.sleep(random.uniform(0.08, 0.25))

        # ========== 3. 点击登录按钮（使用 name 属性，最稳定）==========
        login_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//button[@name="confirm" and @type="submit"]'))
        )

        # 记录当前url
        old_url = driver.current_url

        # 可加一点停顿，模拟思考
        time.sleep(random.uniform(0.5, 1.5))
        login_button.click()

        # ========== 4. 等待登录成功 ==========
        _LOGGER.info("🔍 正在等待登录完成...")
        try:
            # 修改此处：根据你登录后跳转的页面调整 URL 关键词
            wait.until(EC.url_changes(old_url))
            _LOGGER.info("✅ 登录成功！已跳转到主页。")
        except:
            _LOGGER.error("❌ 登录失败或出现验证码。")
            time.sleep(10)  # 停留以便手动查看
            raise

        # ========== 5. 获取 Cookies ==========
        cookies = driver.get_cookies()
        _LOGGER.info(f"🔐 成功获取 {len(cookies)} 个 Cookies：")
        for cookie in cookies:
            _LOGGER.info(f"  {cookie['name']} = {cookie['value']}")
        return cookies
    except Exception as e:
        _LOGGER.error(f"发生错误: {e}")
    finally:
        # 手动关闭浏览器，或取消注释下一行自动退出
        # driver.quit()
        pass


def refresh_cookies(refresh=True):
    _LOGGER.info("开始刷新 Cookies...")
    formated_cookies = None
    if refresh:
        _LOGGER.info("正在登录，远程获取Cookies...")
        username, password = load_account(ACCOUNT_FILE_PATH)
        ret_cookies = login(username, password)
        formated_cookies = {
            cookie['name']: cookie['value'] for cookie in ret_cookies
        }
        with open(COOKIES_FILE_PATH, 'w') as f:
            json.dump(formated_cookies, f)
    else:
        _LOGGER.info("正在本地读取 Cookies...")
        with open(COOKIES_FILE_PATH) as f:
            formated_cookies = json.load(f)
    return formated_cookies


def upload_json(json_dict):
    server, port = load_server(ACCOUNT_FILE_PATH)
    ssh_tunnel = None
    try:
        _LOGGER.info("正在启动 SSH 隧道...")
        local_port = "8888"
        remote_server = f"127.0.0.1:{port}"
        ssh_tunnel = subprocess.Popen([
            'ssh', '-L', f'{local_port}:{remote_server}', '-N', '-f',
            '-o', 'StrictHostKeyChecking=no',
            f'root@{server}'
        ])
        _LOGGER.info(f"SSH 隧道已启动，正在转发到 {remote_server}...")
        upload_url = f"http://127.0.0.1:{local_port}/upload_cookies"
        ret = requests.post(upload_url, json=json_dict)
        ret.raise_for_status()
        json_ret = ret.json()
        _LOGGER.info(f"结果: {json_ret}")
    finally:
        if ssh_tunnel:
            ssh_tunnel.terminate()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[logging.StreamHandler()])
    ret = refresh_cookies(refresh=False)
    upload_json(ret)
