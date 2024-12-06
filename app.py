from flask import Flask, request, jsonify, Response, stream_with_context, render_template, send_file
import json
import os
import time
from collections import deque
from werkzeug.utils import secure_filename
import glob
from flask_cors import CORS
import requests  # 导入 requests 库

app = Flask(__name__)
CORS(app)  # 启用 CORS

# 从环境变量获取 OpenAI 的 API 令牌
from openai import OpenAI
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 从环境变量获取 TTS 厂商的 API 令牌
API_TOKEN = os.environ.get("FISH_AUDIO_API_TOKEN")

chat_history = [
    {"role": "system", "content": "You are a helpful assistant."},
]

new_user_message = False

# 用于暂存生成的音频文件名
audio_files_queue = deque()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/reset_session", methods=["POST"])
def reset_session():
    global new_user_message
    new_user_message = False
    global chat_history
    chat_history = [{"role": "system", "content": "You are a helpful assistant."}]
    return jsonify(success=True, action="reset_session")


@app.route("/send_message", methods=["POST"])
def send_message():
    global new_user_message
    user_message = request.form["message"]
    print(f"Received user message: {user_message}")
    chat_history.append({"role": "user", "content": user_message})
    new_user_message = True
    return jsonify(success=True)


@app.route("/send_audio", methods=["POST"])
def send_audio():
    global new_user_message
    print("Received request in /send_audio")  # 打印日志
    if 'audio' not in request.files:
        print("No audio file in request")  # 打印错误日志
        return jsonify(success=False, error="No audio file found in request")

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify(success=False, error="No selected file")

    filename = secure_filename(audio_file.filename)

    # 获取当前脚本的目录，并创建音频文件的存储路径
    base_dir = os.path.dirname(os.path.realpath(__file__))
    audio_dir = os.path.join(base_dir, 'user_input_audio')
    os.makedirs(audio_dir, exist_ok=True)  # 确保目录存在
    audio_path = os.path.join(audio_dir, filename)

    audio_file.save(audio_path)

    try:
        with open(audio_path, "rb") as file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=file,
                response_format="text"
            )
    except Exception as e:
        return jsonify(success=False, error=str(e))

    # 打印 transcript 内容以供调试
    print(transcript)

    os.remove(audio_path)  # 可选：处理后删除音频文件

    chat_history.append({"role": "user", "content": transcript})
    new_user_message = True
    return jsonify(success=True, transcript=transcript)


def generate_audio_response(text):
    url = "https://api.fish.audio/v1/tts"
    payload = {
        "text": text,
        "reference_id": "7c66db6e457c4d53b1fe428a8c547953",  # 在这里填写您的 reference_id  郭德纲7c66db6e457c4d53b1fe428a8c547953   雷军738d0cc1a3e9430a9de2b544a466a7fc
        "chunk_length": 200,
        "normalize": True,
        "format": "mp3",
        "mp3_bitrate": 64,
        "latency": "normal"
    }
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        filename = f"audio_response_{int(time.time())}.mp3"
        with open(filename, 'wb') as f:
            f.write(response.content)
        return filename
    else:
        print(f"Error in TTS API call: {response.status_code}, {response.text}")
        return None


@app.route("/stream")
def stream():
    def generate():
        global new_user_message
        processed_text = ""  # 用来存储已经发送给 TTS 的文本
        complete_gpt_response = ""  # 用于累积完整的 GPT 回答

        while True:
            while audio_files_queue:
                # 如果队列中有音频文件，就立即发送给前端
                if audio_files_queue:
                    audio_filename = audio_files_queue.popleft()
                    yield f"data: {json.dumps({'message': '', 'audio_filename': audio_filename})}\n\n"

            if new_user_message:
                new_user_message = False
                completion = client.chat.completions.create(
                    model="chatgpt-4o-latest",
                    messages=chat_history,
                    stream=True
                )

                for chunk in completion:
                    if chunk.choices[0].delta.content:
                        gpt_response = chunk.choices[0].delta.content
                        complete_gpt_response += gpt_response
                        chat_history.append({"role": "assistant", "content": gpt_response})

                        # Streaming response to client
                        yield f"data: {json.dumps({'message': gpt_response})}\n\n"

                        # 如果累积的回答长度大于60，并且以停止符号结尾
                        if (len(complete_gpt_response) - len(processed_text)) > 60 and \
                                complete_gpt_response[-1] in {".", "!", "。", "?"}:
                            # 提取新的 TTS 文本部分
                            new_text_for_tts = complete_gpt_response[len(processed_text):]
                            # 创建 TTS 音频文件
                            audio_filename = generate_audio_response(new_text_for_tts)
                            if audio_filename:
                                # 立即发送生成的音频文件名给前端
                                yield f"data: {json.dumps({'message': '', 'audio_filename': audio_filename})}\n\n"
                                audio_files_queue.append(audio_filename)
                                # 更新已处理文本变量
                                processed_text = complete_gpt_response
                            else:
                                print("Failed to generate audio response.")

                    # 当 GPT 模型完成回答
                    finish_reason = getattr(chunk.choices[0], "finish_reason", None)
                    if finish_reason:
                        # 如果有剩下的未处理文本，也发送给 TTS
                        remaining_text = complete_gpt_response[len(processed_text):]
                        if remaining_text.strip():
                            audio_filename = generate_audio_response(remaining_text)
                            if audio_filename:
                                audio_files_queue.append(audio_filename)
                                # 更新已处理文本变量
                                processed_text = complete_gpt_response
                            else:
                                print("Failed to generate audio response.")

                        # 回答完成，重置变量
                        complete_gpt_response = ""
                        processed_text = ""
                        break  # 跳出循环，因为回答已完成

            time.sleep(1)

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


# 修改此路由以处理音频文件的 MIME 类型
@app.route("/audio/<filename>")
def audio(filename):
    # 根据文件扩展名设置正确的 MIME 类型
    if filename.endswith('.mp3'):
        mimetype = 'audio/mpeg'
    elif filename.endswith('.wav'):
        mimetype = 'audio/wav'
    else:
        mimetype = 'application/octet-stream'  # 默认 MIME 类型


    return send_file(filename, mimetype=mimetype)


def clean_up_mp3_files(directory):
    for audio_file in glob.glob(os.path.join(directory, '*.mp3')):
        try:
            os.remove(audio_file)
            print(f"Deleted old audio file: {audio_file}")
        except Exception as e:
            print(f"Error deleting file {audio_file}: {e}")


if __name__ == "__main__":
    clean_up_mp3_files(os.path.dirname(os.path.realpath(__file__)))
    app.run(host='0.0.0.0', port=5123, debug=True)
