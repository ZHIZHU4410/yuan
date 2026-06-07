import json

with open("data.cdb", "r", encoding="utf-8") as f:
    content = f.read(200)
    print("文件开头:", repr(content))
    f.seek(0)
    try:
        data = json.load(f)
        print("顶层类型:", type(data))
        if isinstance(data, dict):
            print("顶层键:", list(data.keys())[:10])
        elif isinstance(data, list):
            print("顶层数组长度:", len(data))
            if len(data) > 0:
                print("第一个元素的键:", list(data[0].keys())[:10])
    except json.JSONDecodeError as e:
        print("JSON 解析错误:", e)