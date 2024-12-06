
# V2G: Voice to ChatGPT

V2G 是一个基于 ChatGPT 和 FishAudioTTS 的语音对话程序，支持语音输入、文本输入，并以文本和语音形式返回回复。它结合了自然语言处理和语音技术，带来流畅的人机交互体验。

## 功能特点
- 实时语音和文本交互。
- 自动化语音回复。
- 支持用户长按按钮录音并自动发送。
- 提供简洁的网页界面，支持跨平台使用。
- 可自定义语音音色。

---

## 目录
- [安装](#安装)
- [使用步骤](#使用步骤)
- [语音音色自定义](#语音音色自定义)
- [贡献](#贡献)
- [许可证](#许可证)

---

## 安装

### 1. 环境依赖
- Python 3.8 或以上
- Node.js 和 npm
- FishAudioTTS API 密钥
- OpenAI ChatGPT API 密钥

### 2. 克隆代码仓库
```bash
git clone https://github.com/yourusername/V2G.git
cd V2G
```

### 3. Python 依赖安装
建议创建一个虚拟环境：
```bash
python -m venv v2g-env
source v2g-env/bin/activate  # 对于 Windows 用户：v2g-env\Scripts\activate
```

安装依赖：
```bash
pip install -r requirements.txt
```

### 4. 配置 API 密钥，通过操作系统配置环境变量
```plaintext
OPENAI_API_KEY=your_openai_api_key
FISH_API_KEY=your_fish_audio_tts_key
```

### 5. 启动后端服务
运行以下命令启动 Flask 后端：
```bash
python app.py
```

### 6. 访问应用
在浏览器中打开 [http://localhost:3000](http://localhost:3000) 即可访问 V2G。

---

## 使用步骤

1. 打开浏览器，访问应用。
2. 点击麦克风按钮开始录音，松开按钮发送语音。
3. 输入文本并点击 **Send** 按钮发送消息。
4. 通过切换静音按钮（🔊/🔇）控制语音播放。

---

## 语音音色自定义

在 `app.py` 中，可以通过修改 `reference_id` 参数自定义语音音色：
```python
"reference_id": "7c66db6e457c4d53b1fe428a8c547953"
```

- **说明**: `reference_id` 表示音色 ID，可替换为您喜欢的音色。
- **获取方法**: 前往 [FishAudio](https://fish.audio/) 平台，浏览并选择不同的音色，获取对应的 `reference_id`。

---

## 贡献

欢迎提交 issue 或 Pull Request 参与项目贡献！

1. Fork 本项目。
2. 创建新分支：
   ```bash
   git checkout -b feature/new-feature
   ```
3. 提交代码并推送：
   ```bash
   git commit -m "Add new feature"
   git push origin feature/new-feature
   ```
4. 发起 Pull Request。

---

## 许可证

MIT License.

---

## 联系方式

如有任何疑问或建议，请通过邮箱 aaronthecowboy1@gmail.com 联系我们。

