# app.py
import json
import logging
import os
import traceback

from flask import Flask, request, jsonify

from check_in import check_in
from send import sc_send

app = Flask(__name__)

# 配置
UPLOAD_FOLDER = 'upload'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
COOKIES_PATH = "cookies.json"
app.config['COOKIES_PATH'] = COOKIES_PATH

logger = logging.getLogger(__name__)


# ✅ 统一响应格式函数
def make_response(success=True, message="操作成功", data=None):
    return jsonify({
        "success": success,
        "message": message,
        "data": data
    })


# ✅ 自定义业务异常
class ApiException(Exception):
    def __init__(self, message="请求失败", status_code=400):
        super().__init__()
        self.message = message
        self.status_code = status_code


# 🛡️ 全局异常处理器

@app.errorhandler(ApiException)
def handle_api_exception(e):
    logger.warning(f"ApiException: {e.message}")
    return make_response(success=False, message=e.message), e.status_code


@app.errorhandler(404)
def handle_not_found(e):
    return make_response(success=False, message="接口未找到"), 404


@app.errorhandler(405)
def handle_method_not_allowed(e):
    return make_response(success=False, message="请求方法不被允许"), 405


@app.errorhandler(500)
def handle_internal_error(e):
    # 记录完整堆栈
    logger.error(f"InternalServerError: {str(e)}\n{traceback.format_exc()}")
    return make_response(success=False, message="服务器内部错误"), 500


# 捕获所有未处理的异常（包括 ValueError, FileNotFoundError 等）
@app.errorhandler(Exception)
def handle_unexpected_error(e):
    logger.error(f"UnexpectedError: {str(e)}\n{traceback.format_exc()}")
    return make_response(success=False, message="操作失败"), 500

def get_upload_cookies_path():
    return os.path.join(app.config['UPLOAD_FOLDER'], app.config['COOKIES_PATH'])

# ✅ 接口1：上传 Cookies
@app.route('/upload_cookies', methods=['POST'])
def upload_cookies():
    if 'file' in request.files:
        file = request.files['file']
        if not file.filename:
            raise ApiException("未选择文件")

        if not file.filename.endswith('.json'):
            raise ApiException("仅支持 .json 文件")

        filepath = get_upload_cookies_path()
        file.save(str(filepath))
        return make_response(message="Cookies 文件上传成功", data={"path": filepath})

    if request.is_json:
        data = request.get_json()
        if not isinstance(data, dict):
            raise ApiException("JSON 数据必须是一个 Cookie 字典")

        filepath = get_upload_cookies_path()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return make_response(message="Cookies JSON 数据保存成功", data={"path": filepath})

    raise ApiException("请上传 JSON 文件或发送 JSON 字典")


# ✅ 接口2：执行签到
@app.route('/sign', methods=['POST'])
def sign():
    filepath = get_upload_cookies_path()
    if not os.path.exists(filepath):
        raise ApiException("未找到 cookies 文件，请先上传")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
    except json.JSONDecodeError as e:
        raise ApiException(f"cookies 文件格式错误，JSON 解析失败: {str(e)}")
    except Exception as e:
        raise ApiException(f"读取 cookies 文件时发生错误: {str(e)}")

    if not isinstance(cookies, (dict, list)):
        raise ApiException("cookies 文件内容必须是对象或数组")

    # 调用签到逻辑
    try:
        ret = check_in(cookies=cookies)
        logger.info(f"签到结果: {ret}")
        sc_send(title="Nikke自动签到成功！", message=f"签到成功: {ret}")
    except Exception as e:
        sc_send(title="Nikke自动签到失败！", message=f"签到失败: {str(e)}")
        raise ApiException(f"签到失败: {str(e)}")
    return make_response(message="签到成功")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[logging.StreamHandler(), logging.FileHandler('app.log', encoding='utf-8')])
    app.run(host='0.0.0.0', port=5000, debug=False)  # 注意：生产环境务必 debug=False