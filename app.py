from flask import Flask, request, jsonify, Response, stream_with_context, render_template, send_file
import json
import os
from openai import OpenAI
import time
from collections import deque
from werkzeug.utils import secure_filename
import glob
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 启用 CORS
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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
    # 重置任何其他需要的状态
    # ...
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

    # 打印transcript内容以供调试
    print(transcript)

    os.remove(audio_path)  # Optional: remove the audio file after processing

    chat_history.append({"role": "user", "content": transcript})
    new_user_message = True
    return jsonify(success=True, transcript=transcript)

def generate_audio_response(text):
    audio_response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text,
    )
    filename = f"audio_response_{int(time.time())}.mp3"
    audio_response.stream_to_file(filename)
    return filename


@app.route("/stream")
def stream():
    def generate():
        global new_user_message
        processed_text = ""  # 用来存储已经发送给TTS的文本
        complete_gpt_response = ""  # 用于累积完整的GPT回答

        while True:
            while audio_files_queue:
                # 在这里，如果队列中有音频文件，就立即发送给前端
                if audio_files_queue:
                    audio_filename = audio_files_queue.popleft()
                    yield f"data: {json.dumps({'message': '', 'audio_filename': audio_filename})}\n\n"

            if new_user_message:
                new_user_message = False
                completion = client.chat.completions.create(
                    model="gpt-4-1106-preview",
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
                            # 提取新的TTS文本部分
                            new_text_for_tts = complete_gpt_response[len(processed_text):]
                            # 创建TTS音频文件
                            audio_filename = generate_audio_response(new_text_for_tts)
                            # 这里立即发送生成的音频文件名给前端
                            yield f"data: {json.dumps({'message': '', 'audio_filename': audio_filename})}\n\n"
                            audio_files_queue.append(audio_filename)
                            # 更新已处理文本变量
                            processed_text = complete_gpt_response

                    # 当GPT模型完成回答
                    finish_reason = getattr(chunk.choices[0], "finish_reason", None)
                    if finish_reason:
                        # 如果有剩下的未处理文本，也发送给TTS
                        remaining_text = complete_gpt_response[len(processed_text):]
                        if remaining_text.strip():
                            audio_filename = generate_audio_response(remaining_text)
                            audio_files_queue.append(audio_filename)
                            # 更新已处理文本变量
                            processed_text = complete_gpt_response

                        # 回答完成，重置变量
                        complete_gpt_response = ""
                        processed_text = ""
                        break  # Break out of the loop since response is finished

            time.sleep(1)

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


# Setup a new route to serve the audio file
@app.route("/audio/<filename>")
def audio(filename):
    # Ensure there's an added layer of security here like authentication
    # You would also want to clean up these files after they have been served to the client
    return send_file(filename, mimetype='audio/mpeg')

def clean_up_mp3_files(directory):
    for mp3_file in glob.glob(os.path.join(directory, '*.mp3')):
        try:
            os.remove(mp3_file)
            print(f"Deleted old audio file: {mp3_file}")
        except Exception as e:
            print(f"Error deleting file {mp3_file}: {e}")


if __name__ == "__main__":
    clean_up_mp3_files(os.path.dirname(os.path.realpath(__file__)))
    app.run(host='0.0.0.0', port=5123, debug=True)
