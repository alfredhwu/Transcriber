from logging import disable
from funasr import AutoModel
import json, sys
from datetime import datetime

from funasr.auto.auto_model import merge_vad
# paraformer-zh is a multi-functional asr model
# use vad, punc, spk or not as you need
model = AutoModel(
                    # model="paraformer-zh",  
                    model="iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
                    # model="iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
                    # model="iic/Whisper-large-v3",
                    vad_model="fsmn-vad",  
                    vad_kwargs={"max_single_segment_time": 30000},
                    punc_model="ct-punc", 
                    spk_model="cam++", 
                    # model_revision="v2.0.9",
                    # vad_model_revision="v2.0.4",
                    # punc_model_revision="v2.0.4",
                    # spk_model_revision="v2.0.2",
                    # disable_update=True, ## disable update to avoid downloading models
                    # disable_log = True,
                    disable_pbar = True,
                  )

audio = sys.argv[1]
audioname = audio.split("/")[-1]

print(f"[{datetime.now()}] now transcribig [{audio}] ...")

res = model.generate(input=f"{audio}", 
                     batch_size_s=300, 
                     use_itn=True,
                     merge_vad=True,
                     merge_length_s=15,
                     hotword='魔搭')

transcription_json = res[0]["sentence_info"]


print(f"[{datetime.now()}] now exporting files ...")

with open(f"{audio}.json", "w", encoding="utf8") as f:
    json.dump(transcription_json, f, ensure_ascii=False)


transcription_txt = ""
if len(transcription_json) > 0:
    transcription_txt += f"[{transcription_json[0]['start']/1000}][Speaker {transcription_json[0]['spk']}]: "
    current_speaker = transcription_json[0]["spk"]
    for phrase in transcription_json:
        if phrase["spk"] != current_speaker:
            ## start a new line
            transcription_txt += f"\n[{phrase['start']/1000}][Speaker {phrase['spk']}]: "
            current_speaker = phrase["spk"]
            
        ## continue current line
        transcription_txt += phrase["text"]

with open(f"{audio}.txt", "w", encoding="utf8") as f:
    f.write(transcription_txt)

trans_content_html = "<div class='transcription'>"
if len(transcription_json) > 0: 
    speaker_id = transcription_json[0]["spk"]
    trans_content_html += f"<div class='trans-box speaker{speaker_id}'>"
    trans_content_html += f"<div class='trans-speaker'>speaker{speaker_id}</div>"
    trans_content_html += "<div class='trans-line'>"
    for phrase in transcription_json:
        if (speaker_id != phrase["spk"]):
            speaker_id = phrase["spk"]
            ## start a new line
            trans_content_html += "</div></div>" ## close trans-line, then trans-box
            ## start new box
            trans_content_html += f"<div class='trans-box speaker{speaker_id}'>"
            trans_content_html += f"<div class='trans-speaker'>speaker{speaker_id}</div>"
            trans_content_html += "<div class='trans-line'>"

        trans_content_html += f"<a href='#' class='phrase' onclick='jumpToSegment({phrase["start"]})'>{phrase["text"]}</a>"

    trans_content_html += "</div>" ## close trans-line
    trans_content_html +="</div>" ## close trans-box
trans_content_html += "</div>" ## close transcription

html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{audioname}</title>
    <style>
        .player-container {{
            width: 500px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .progress-container {{
            width: 100%;
            height: 5px;
            background: #ddd;
            border-radius: 3px;
            margin: 15px 0;
            cursor: pointer;
            position: relative;
        }}

        .progress-bar {{
            height: 100%;
            background: #2196F3;
            border-radius: 3px;
            width: 0;
            transition: width 0.1s linear;
        }}

        .time-display {{
            display: flex;
            justify-content: space-between;
            color: #666;
            font-size: 14px;
        }}

        .controls {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-top: 10px;
        }}

        button {{
            padding: 8px 15px;
            background: #2196F3;
            border: none;
            color: white;
            border-radius: 5px;
            cursor: pointer;
            transition: background 0.3s;
        }}

        button:hover {{
            background: #1976D2;
        }}

        input[type="range"] {{
            width: 100%;
            margin: 10px 0;
        }}

        .timestamp-input {{
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }}

        .timestamp-input input {{
            padding: 5px;
            width: 100px;
        }}

        .speaker0 {{
            /* color: blue; */
            background-color: lightpink;
            /* border: red; */
        }}

        .speaker1 {{
            /* color: green; */
            background-color: lightgreen;
        }}
    </style>
</head>
<body>
    <div id="transcription-area" src="{audioname}.json">
        {trans_content_html}
    </div>
    <div class="player-container">
        
        <div class="progress-container" id="progressContainer">
            <div class="progress-bar" id="progressBar"></div>
        </div>
        
        <div class="time-display">
            <span id="currentTime">0:00</span>
            <span id="duration">0:00</span>
        </div>

        <div class="controls">
            <button id="playButton">播放</button>
            <button id="pauseButton">暂停</button>
        </div>

        <div class="timestamp-input">
            <input type="text" id="jumpTime" placeholder="输入时间(秒)">
            <button onclick="jumpToTimestamp()">跳转</button>
        </div>
    </div>

    <script>
        const audio = new Audio('{audioname}');
        const playButton = document.getElementById('playButton');
        const pauseButton = document.getElementById('pauseButton');
        const progressBar = document.getElementById('progressBar');
        const progressContainer = document.getElementById('progressContainer');
        const currentTimeDisplay = document.getElementById('currentTime');
        const durationDisplay = document.getElementById('duration');

        const transcriptArea = document.getElementById('transcription-area');

        // 播放/暂停控制
        playButton.addEventListener('click', () => {{
            audio.play();
            playButton.style.display = 'none';
            pauseButton.style.display = 'inline-block';
        }});

        pauseButton.addEventListener('click', () => {{
            audio.pause();
            pauseButton.style.display = 'none';
            playButton.style.display = 'inline-block';
        }});

        // 进度条拖拽
        progressContainer.addEventListener('click', (e) => {{
            const rect = progressContainer.getBoundingClientRect();
            const pos = (e.clientX - rect.left) / rect.width;
            audio.currentTime = pos * audio.duration;
        }});

        // 时间显示更新
        audio.addEventListener('timeupdate', () => {{
            const progress = (audio.currentTime / audio.duration) * 100;
            progressBar.style.width = `${{progress}}%`;
            currentTimeDisplay.textContent = formatTime(audio.currentTime);
        }});

        // 音频加载完成时显示总时长
        audio.addEventListener('loadedmetadata', () => {{
            durationDisplay.textContent = formatTime(audio.duration);
        }});

        // 播放片段
        function jumpToSegment(start) {{
            const time = parseFloat(start) / 1000;
            
            if (!isNaN(time) && time >= 0 && time <= audio.duration) {{
                audio.currentTime = time;
                audio.play();
            }}
        }}

        // 时间戳跳转功能
        function jumpToTimestamp() {{
            const input = document.getElementById('jumpTime').value;
            const time = parseFloat(input);
            
            if (!isNaN(time) && time >= 0 && time <= audio.duration) {{
                audio.currentTime = time;
            }}
        }}

        // 时间格式化（分钟:秒）
        function formatTime(seconds) {{
            const minutes = Math.floor(seconds / 60);
            seconds = Math.floor(seconds % 60);
            return `${{minutes}}:${{seconds.toString().padStart(2, '0')}}`;
        }}

        // 初始化时隐藏暂停按钮
        pauseButton.style.display = 'none';
    </script>
</body>
</html>
"""

with open(f"{audio}.html", "w", encoding="utf8") as f:
    f.write(html_template.format(audio=audio, audioname=audioname, trans_content_html=trans_content_html))
print(f"audio recording transcribed successfully !")