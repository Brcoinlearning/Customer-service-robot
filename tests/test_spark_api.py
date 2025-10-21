import json
import requests

# 请替换XXXXXXXXXX为您的 APIpassword, 获取地址：https://console.xfyun.cn/services/bmx1
api_key = "Bearer UuzpxGawsChJBdvajtVh:AEpkMYQXCPoRxvpQptmj"
url = "https://spark-api-open.xf-yun.com/v1/chat/completions"

# 请求模型，并将结果输出
def get_answer(message):
    # 初始化请求体
    headers = {
        'Authorization': api_key,
        'content-type': "application/json"
    }
    body = {
        "model": "lite",
        "user": "user_id",
        "messages": message,
        # 可选参数
        "stream": False
    }
    response = requests.post(url=url, json=body, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data['choices'][0]['message']['content']
    else:
        raise Exception(f"调用API时发生错误: {response.status_code}, {response.text}")

# 管理对话历史，按序编为列表
def getText(text, role, content):
    jsoncon = {}
    jsoncon["role"] = role
    jsoncon["content"] = content
    text.append(jsoncon)
    return text

# 获取对话中的所有角色的content长度
def getlength(text):
    length = 0
    for content in text:
        temp = content["content"]
        leng = len(temp)
        length += leng
    return length

# 判断长度是否超长，当前限制8K tokens
def checklen(text):
    while (getlength(text) > 11000):
        del text[0]
    return text

# 主程序入口
if __name__ == '__main__':

    # 对话历史存储列表
    chatHistory = []
    print("输入 'exit' 以结束对话。")
    # 循环对话轮次
    while True:
        try:
            # 等待控制台输入
            Input = input("\n我:")
            if Input.lower() == 'exit':
                print("结束对话。")
                break
            question = checklen(getText(chatHistory, "user", Input))
            # 开始输出模型内容
            print("星火:", end="", flush=True)
            answer = get_answer(question)
            print(answer)
            getText(chatHistory, "assistant", answer)
        except Exception as e:
            print(str(e))