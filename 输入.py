import pyautogui
import time

# 要输入的大段文字
text_to_type = """
s = input()
prefix = "请输入字符串："
if s.startswith(prefix):
    s = s[len(prefix):]

result = ''
for ch in s:
    if '\u4e00' <= ch <= '\u9fa5':
        result += ch

print(f"汉字有：{result}")
"""

print("5秒后开始输入，请立刻将光标放到目标输入框...")
time.sleep(5)

# 模拟逐字输入，interval控制打字速度（秒）
pyautogui.typewrite(text_to_type, interval=0.05)
print("输入完成！")