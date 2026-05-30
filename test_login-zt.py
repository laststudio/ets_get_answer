from utils import *
from typing import Dict, List, Tuple, Optional, Any
import webview
import os

# 最终目标为返回token
def loginzt(login: str, user_id: str, suc_user_token: str,
            device_code: str = "BF1CB2218D9A88B9|0C072A134F008B9F",
            device_name: str = "1337",
            suc_device_name: str = "Other",
            os_type: str = "windows",
            system: str = "4",
            sign_response: int = 1,
            global_client_version: str = "",
            sn: str = "test") -> Optional[str]:
    """
    新版登录函数（适配 user/login-zt 接口）
    """

    # https://pass.changyan.com/login?nextpage=aHR0cHM6Ly93d3cuZXRzMTAwLmNvbS9sb2dpbkNoZWNrLmh0bWw=&customConfig=aW4iLHByb2R1Y3RfYXBwa2V5OiJxaW5nZGFvX2V0cyIsIm5lZWRUaWNrZXQiOiJ0cnVlIiwibG9naW5fbm90QXV0byI6InRydWUifQ&from=ew&appId=pass6port18

    params = {
        "sn": sn,
        "login": login,
        "user_id": user_id,
        "device_name": device_name,
        "device_code": device_code,
        "suc_user_token": suc_user_token,
        "suc_device_name": suc_device_name,
        "os_type": os_type,
        "system": system,
        "global_client_version": global_client_version,
        "sign_response": sign_response,
    }

    # 仍使用 create_request_payload 生成基础结构，然后按新接口要求包装成数组
    payload = create_request_payload("user/login-zt", params)
    response = send_api_request(f"{BASE_URL}/user/login-zt", payload)

    if response[0]["code"] == 0:
        token = response[0]["body"]["token"]
        print(token)

    return response

    # if response and len(response) > 0 and "body" in response[0] and "token" in response[0]["body"]:
    #     return response[0]["body"]["token"]
    # else:
    #     print("登录失败，请检查参数")
    #     return None

# def save_userid(login, user_id):

#     with open("userinfo.json", "a+", encoding = "utf-8") as f:
        

# def userinfo(phone: str, password: str, sn: str = "test") -> Optional[str]:
#     """
#     获取用户信息
#     """
#     params = {
#         "sn": sn,
#         "phone": phone,
#         "password": password,
#     }

#     # 仍使用 create_request_payload 生成基础结构，然后按新接口要求包装成数组
#     payload = create_request_payload("user/info", params)
#     response = send_api_request(f"{BASE_URL}/user/info", payload)

#     return response

# def loginbyticket(device_name: str, device_code: str, ticket: str, sn: str = "test") -> Optional[str]:
#     params = {
#         "sn": sn,
#         "ticket": ticket,
#         "device_code": device_code,
#         "device_name": device_name,
#     }

#     payload = create_request_payload("user/login-by-ticket", params)
#     response = send_api_request(f"{BASE_URL}/user/login-by-ticket", payload)

#     return response

# 屎山代码发力了
class Api:
    def __init__(self):
        # self.window = window
        self.userid = None

    # def getwindow(self, window):
    #     self.window = window
    def capture(self, data):
        try:
            data = json.loads(data)
        except:
            pass
        # print(data)
        if "/login/checkLogin" in data["url"]:
            if int(data["status"]) == 200:
                responseBody = json.loads(data["responseBody"])
                if responseBody["Code"] == 0:
                    responseBodyData = json.loads(responseBody["Data"])
                    self.userid = responseBodyData["uid"]
                    # print(data["requestParams"]["i"])
                    # print(self.userid)
                    # print(responseBodyData["captchaResult"])
                    # 移交执行权到 loginzt，外部执行剩余步骤
                    # 这里后期可以换为读取已有的hwid
                    # 应保存user_id，这个user_id就是login接口的phone
                    loginzt(login = data["requestParams"]["i"], user_id = self.userid, suc_user_token = responseBodyData["captchaResult"])
                    # 预留save接口，不写了，累
                    # save_userid(login = data["requestParams"]["i"], user_id = self.userid)
                    # 释放，避免截取跳转其他页面出现bug
                    # self.window.destroy()
                    os._exit(0)
                else:
                    print(f"Error: 错误的请求返回代码{str(responseBody['Code'])}")
                    # self.window.evaluate_js('location.reload()')
                    print("失败，请重新运行")
                    os._exit(0)
            else:
                print(f"Error: 错误的请求状态码{str(data['status'])}")
                print("失败，请重新运行")
                # self.window.evaluate_js('location.reload()')
                os._exit(0)

# https://pass.changyan.com/login?nextpage=aHR0cHM6Ly93d3cuZXRzMTAwLmNvbS9sb2dpbkNoZWNrLmh0bWw=&customConfig=e3ZpZXdfdHlwZToiV0VCIixoaWRkZW5fbW9kdWxlOiAiaGVhZGVyLHRhaWwsbG9naW5CeVZlcmlmeUNvZGUscmVnaXN0ZXIsbG9naW5CeVRoaXJkTG9naW4iLHByb2R1Y3RfYXBwa2V5OiJxaW5nZGFvX2V0cyIsIm5lZWRUaWNrZXQiOiJ0cnVlIiwibG9naW5fbm90QXV0byI6InRydWUifQ&from=ew&appId=pass6port18
# window = webview.create_window('教育版登录', 'about:blank')
api = Api()

window = None

def on_loaded():
    # 页面 DOM 就绪后注入，拦截此后所有 jQuery Ajax 请求
    window.evaluate_js("""
        if (window.$) {
            $(document).ajaxComplete(function(event, xhr, settings) {
                // 解析完整 URL 中的查询参数
                var urlObj = new URL(settings.url, window.location.origin);
                var queryParams = Object.fromEntries(urlObj.searchParams);

                // 请求体/参数处理
                var requestBody = '';
                var requestParams = {};
                if (settings.data) {
                    if (typeof settings.data === 'string') {
                        requestBody = settings.data;
                        try {
                            requestParams = Object.fromEntries(new URLSearchParams(settings.data));
                        } catch(e) {}
                    } else {
                        requestBody = JSON.stringify(settings.data);
                        requestParams = settings.data;
                    }
                }

                // 组装所有信息
                var payload = {
                    url: settings.url,
                    method: settings.type || 'GET',
                    queryParams: queryParams,          // URL 里的查询参数
                    requestHeaders: settings.headers || {},
                    requestBody: requestBody,
                    requestParams: requestParams,      // POST 的表单/JSON 参数（解析后）
                    status: xhr.status,
                    responseHeaders: xhr.getAllResponseHeaders(),
                    responseBody: xhr.responseText
                };

                window.pywebview.api.capture(JSON.stringify(payload));
            });
        } else {
            console.log('页面未使用 jQuery');
        }
    """)
    # # 加载真正的登录页面
    # window.load_url("https://pass.changyan.com/login?nextpage=aHR0cHM6Ly93d3cuZXRzMTAwLmNvbS9sb2dpbkNoZWNrLmh0bWw=&customConfig=e3ZpZXdfdHlwZToiV0VCIixoaWRkZW5fbW9kdWxlOiAiaGVhZGVyLHRhaWwsbG9naW5CeVZlcmlmeUNvZGUscmVnaXN0ZXIsbG9naW5CeVRoaXJkTG9naW4iLHByb2R1Y3RfYXBwa2V5OiJxaW5nZGFvX2V0cyIsIm5lZWRUaWNrZXQiOiJ0cnVlIiwibG9naW5fbm90QXV0byI6InRydWUifQ&from=ew&appId=pass6port18")

    # # 重要：移除本事件，避免二次加载时重复注入
    # window.events.loaded -= on_loaded

if __name__ == "__main__":
    window = webview.create_window('教育版登录', 'https://pass.changyan.com/login?nextpage=aHR0cHM6Ly93d3cuZXRzMTAwLmNvbS9sb2dpbkNoZWNrLmh0bWw=&customConfig=e3ZpZXdfdHlwZToiV0VCIixoaWRkZW5fbW9kdWxlOiAiaGVhZGVyLHRhaWwsbG9naW5CeVZlcmlmeUNvZGUscmVnaXN0ZXIsbG9naW5CeVRoaXJkTG9naW4iLHByb2R1Y3RfYXBwa2V5OiJxaW5nZGFvX2V0cyIsIm5lZWRUaWNrZXQiOiJ0cnVlIiwibG9naW5fbm90QXV0byI6InRydWUifQ&from=ew&appId=pass6port18', js_api = api)
    window.events.loaded += on_loaded
    webview.start() # debug = True