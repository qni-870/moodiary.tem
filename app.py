<<<<<<< HEAD
from flask import Flask, render_template, request, jsonify
import requests
import sqlite3
import os
import uuid
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

# -------------------- 환경 변수 --------------------
CLOVA_API_KEY = os.environ.get("CLOVA_API_KEY")
CLOVA_API_KEY_ID = os.environ.get("CLOVA_API_KEY_ID")
CLOVA_API_URL = os.environ.get("CLOVA_API_URL")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

DB_PATH = "app.db"


# -------------------- DB 초기화 --------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS diary (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    content TEXT,
                    date TEXT UNIQUE,
                    weather TEXT,
                    emotion TEXT,
                    youtube_title TEXT,
                    youtube_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
    conn.commit()
    conn.close()


init_db()


# -------------------- YouTube 검색 --------------------
def search_youtube(query):
    """주어진 검색어(query)로 유튜브에서 영상 검색"""
    if not YOUTUBE_API_KEY:
        print("[WARNING] YouTube API Key가 설정되지 않았습니다.")
        return []

    search_url = (
        "https://www.googleapis.com/youtube/v3/search"
        f"?part=snippet&type=video&maxResults=5&q={query}&key={YOUTUBE_API_KEY}"
    )

    response = requests.get(search_url)
    results = []

    if response.status_code == 200:
        data = response.json()
        for item in data.get("items", []):
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            results.append({
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
            })
    else:
        print("[ERROR] YouTube API 실패:", response.text)

    return results


# -------------------- 홈 --------------------
@app.route('/')
def index():
    # ✔ diary.html 렌더링
    return render_template('diary.html')


# -------------------- 최근 일기 목록 --------------------
@app.route('/diary/list', methods=['GET'])
def get_diary_list():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, title, content, date, weather, emotion, youtube_url, created_at 
        FROM diary 
        ORDER BY date ASC
    """)
    rows = c.fetchall()
    conn.close()

    return jsonify({
        "items": [{
            "id": r[0],
            "title": r[1],
            "content": r[2],
            "date": r[3],
            "weather": r[4],
            "emotion": r[5],
            "recommended_url": r[6],
            "created_at": r[7],
        } for r in rows]
    })


# -------------------- 일기 삭제 --------------------
@app.route('/diary/delete', methods=['POST'])
def delete_diary():
    data = request.get_json()
    diary_id = data.get('id')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM diary WHERE id=?", (diary_id,))
    conn.commit()
    conn.close()

    return jsonify({"status": "deleted"})


# -------------------- 테마 저장 (미사용 Placeholder) --------------------
@app.route('/profile/update', methods=['POST'])
def update_profile():
    return jsonify({"status": "ok"})


# -------------------- 감정 분석 + 음악 추천/저장 --------------------
@app.route('/mcp/recommend', methods=['POST'])
def recommend_music():
    data = request.get_json()

    content = data.get('diary') or data.get('content')
    title = data.get('title', '무제')
    date = data.get('date')
    weather = data.get('weather', '')

    if not content:
        return jsonify({"error": "내용이 없습니다."}), 400

    should_save = data.get('save', False)
    should_recommend = data.get('recommend', True)

    # 저장이 아니면 자동으로 추천 실행
    if should_save is False:
        should_recommend = True

    emotion = ""
    recommended_url = ""
    youtube_title = ""

    # ---------- 1. 감정 분석 ----------
    if should_recommend:
        if CLOVA_API_KEY and CLOVA_API_URL:
            payload = {
                "messages": [
                    {"role": "system", "content": "당신은 감정을 분석하는 비서입니다. 한 단어로만 감정을 분석해줘."},
                    {"role": "user", "content": f"다음 일기의 감정을 한 단어로 분석해줘: {content}"}
                ]
            }

            headers = {
                "Authorization": f"Bearer {CLOVA_API_KEY}",
                "X-NCP-CLOVASTUDIO-REQUEST-ID": str(uuid.uuid4()),
                "Content-Type": "application/json",
            }

            try:
                response = requests.post(CLOVA_API_URL, headers=headers, json=payload)
                print("[DEBUG] CLOVA 응답:", response.status_code, response.text[:200])

                if response.status_code == 200:
                    result = response.json()
                    emotion = result["result"]["message"]["content"].split('\n')[0].strip()
                else:
                    print("[ERROR] CLOVA 분석 실패:", response.text)

            except Exception as e:
                print("[ERROR] CLOVA API 오류:", e)

        # 실패 대비
        emotion = emotion or "중립"

        # ---------- 2. 유튜브 검색 ----------
        query = f"{emotion} 감정에 어울리는 음악"
        youtube_results = search_youtube(query)

        print("[DEBUG] YouTube 결과:", youtube_results)

        if youtube_results:
            youtube_title = youtube_results[0]["title"]
            recommended_url = youtube_results[0]["url"]
        else:
            print("[WARNING] YouTube 검색 결과 없음")

    # ---------- 3. DB 저장 ----------
    if should_save:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()

            c.execute("""
                INSERT OR REPLACE INTO diary 
                (date, title, content, weather, emotion, youtube_title, youtube_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (date, title, content, weather, emotion, youtube_title, recommended_url))

            conn.commit()
            print(f"[INFO] 일기 저장 완료 ({date})")

        except Exception as e:
            print("[CRITICAL ERROR] DB 저장 실패:", e)
            return jsonify({"error": str(e)}), 500
        finally:
            if conn:
                conn.close()

    # ---------- 4. 결과 반환 ----------
    return jsonify({
        "emotion": emotion,
        "recommended_music_url": recommended_url
    })


# -------------------- Flask 실행 --------------------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
=======
# app.py - 일기 감정 분석 기반 음악 추천 MCP 서버 (HyperCLOVA X 버전)

from flask import Flask, request, jsonify, render_template, url_for
import requests
import random
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import sqlite3
from pathlib import Path
import uuid

app = Flask(__name__)

# --- Logging: write to logs/app.log and console ---
LOG_DIR = Path(__file__).with_name("logs")
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

log_file_handler = RotatingFileHandler((LOG_DIR / "app.log").as_posix(), maxBytes=1_000_000, backupCount=3, encoding="utf-8")
log_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
log_file_handler.setFormatter(log_formatter)

logging.basicConfig(level=logging.INFO, handlers=[log_file_handler])
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logging.getLogger().addHandler(console_handler)

# --- 환경 변수 및 상수 설정 (수정된 부분) ---
# .env 우선 로드, 없거나 비어 있으면 env.example 보조 로드
load_dotenv()
if not os.environ.get('CLOVA_API_KEY'):
    load_dotenv('env.example')

"""HyperCLOVA X API 환경 변수
필수: CLOVA_API_KEY, CLOVA_API_KEY_ID, CLOVA_API_URL
선택: CLOVA_MODEL (기본값: HCX-D001)
"""
CLOVA_API_KEY = os.environ.get('CLOVA_API_KEY')
CLOVA_API_KEY_ID = os.environ.get('CLOVA_API_KEY_ID')
CLOVA_API_URL = os.environ.get('CLOVA_API_URL')
CLOVA_MODEL = os.environ.get('CLOVA_MODEL', 'HCX-003')

def _build_clova_headers() -> dict:
    return {
        "Authorization": f"Bearer {CLOVA_API_KEY}",
        "X-NCP-CLOVASTUDIO-REQUEST-ID": str(uuid.uuid4()),
        "Content-Type": "application/json",
    }

# --- SQLite: Diary storage ---
DB_PATH = Path(__file__).with_name("app.db")

def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS diaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT NOT NULL,
                sentiment TEXT,
                situation TEXT,
                weather TEXT,
                recommended_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # 사용자 프로필 테이블 (단일 레코드 사용)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT,
                photo_url TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # 기본 프로필 레코드 보장
        cur = conn.execute("SELECT COUNT(*) FROM profiles WHERE id=1")
        if cur.fetchone()[0] == 0:
            conn.execute("INSERT INTO profiles(id, name, photo_url) VALUES (1, ?, ?)", ("사용자", None))
        try:
            conn.execute("ALTER TABLE diaries ADD COLUMN title TEXT")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE diaries ADD COLUMN weather TEXT")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE profiles ADD COLUMN photo_url TEXT")
        except Exception:
            pass
        # 댓글 테이블
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                diary_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(diary_id) REFERENCES diaries(id) ON DELETE CASCADE
            )
            """
        )
        # 즐겨찾기 테이블 (하루 한 일기 단위로 즐겨찾기)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                diary_id INTEGER NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(diary_id) REFERENCES diaries(id) ON DELETE CASCADE
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

init_db()

# --- Index ---
@app.get('/')
def index():
    # 프로필 이름 조회
    conn = sqlite3.connect(DB_PATH)
    name = "사용자"
    photo_url = None
    try:
        row = conn.execute("SELECT name, photo_url FROM profiles WHERE id=1").fetchone()
        if row:
            if row[0]:
                name = row[0]
            if row[1]:
                photo_url = row[1]
    finally:
        conn.close()
    return render_template('index.html', profile_name=name, profile_photo_url=photo_url)


from data.mappings import SITUATION_KEYWORDS, MAPPING_DATA

# --- 1단계: 감정 분석 함수 (HyperCLOVA X 호출로 변경) ---
def analyze_sentiment(diary_text):
    # 환경변수 미설정 시에도 서비스 지속성을 위해 로컬 폴백 사용
    if not (CLOVA_API_KEY and CLOVA_API_KEY_ID and CLOVA_API_URL):
        logging.info("[sentiment] Using fallback (env not set)")
        return _fallback_analyze_sentiment(diary_text)

    # HyperCLOVA X에게 감정 분석을 요청하는 프롬프트
    prompt_text = (
        "주어진 일기 내용을 분석하여 사용자의 감성을 파악하고, "
        "오직 'Positive', 'Negative', 'Neutral' 세 단어 중 하나로만 답변하시오.\n\n"
        "일기: " + diary_text
    )

    # Chat Completions 요청 형식 (docs)
    data = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant for sentiment classification."},
            {"role": "user", "content": prompt_text}
        ],
        "maxTokens": 64,
        "temperature": 0.3,
        "topP": 0.8
    }

    try:
        # Chat Completions 엔드포인트 (docs)
        api_endpoint = CLOVA_API_URL.rstrip('/') + f"/v1/chat-completions/{CLOVA_MODEL}"
        logging.info(f"[sentiment] Using HyperCLOVA API model={CLOVA_MODEL} endpoint={api_endpoint}")
        response = requests.post(api_endpoint, headers=_build_clova_headers(), json=data, timeout=15)
        try:
            logging.info(f"[sentiment] HTTP {response.status_code} from HyperCLOVA")
            # 로그 확인용으로 응답 일부만 출력 (너무 길면 300자까지만)
            _preview = (response.text or "")[:300]
            logging.info(f"[sentiment] Response preview: {_preview}")
        except Exception:
            pass
        response.raise_for_status()

        result = response.json()
        
        # 응답 텍스트 추출 (Chat Completions 형식)
        sentiment_text = None
        try:
            # docs: result.message.content
            if isinstance(result, dict) and 'result' in result:
                inner = result.get('result', {}) or {}
                msg = inner.get('message', {}) if isinstance(inner, dict) else {}
                sentiment_text = (msg or {}).get('content')
            # 과거 포맷/호환
            if not sentiment_text and 'choices' in result:
                sentiment_text = result['choices'][0].get('message', {}).get('content')
        except Exception:
            pass
        if not sentiment_text and isinstance(result, dict):
            # 다른 키 시도
            for key in ("result", "message", "text"):
                if key in result and isinstance(result[key], str):
                    sentiment_text = result[key]
                    break
        if not sentiment_text:
            logging.info("[sentiment] Fallback: parse failure")
            # 파싱 실패 시 폴백
            return _fallback_analyze_sentiment(diary_text)

        sentiment = sentiment_text.strip().capitalize()
        
        # 응답이 예상한 감정 분류에 없으면 Neutral 처리 (안전 장치)
        if sentiment not in ["Positive", "Negative", "Neutral"]:
            logging.info("[sentiment] Fallback: invalid class")
            return _fallback_analyze_sentiment(diary_text)

        return sentiment 

    except Exception as e:
        # API 오류 시 폴백 사용
        logging.error(f"HyperCLOVA X API Error: {e}")
        try:
            # requests.HTTPError일 경우 응답 정보 추가 로깅
            _resp = getattr(e, 'response', None)
            if _resp is not None:
                logging.error(f"[sentiment] Error HTTP {getattr(_resp, 'status_code', '?')}")
                _preview_err = (getattr(_resp, 'text', '') or '')[:300]
                logging.error(f"[sentiment] Error response preview: {_preview_err}")
        except Exception:
            pass
        logging.info("[sentiment] Fallback: exception")
        return _fallback_analyze_sentiment(diary_text)

def _fallback_analyze_sentiment(diary_text: str) -> str:
    """간단한 키워드 기반 감정 분류 (API 오류/미설정 대비)."""
    text = diary_text.lower()
    negative_keywords = [
        "이별", "헤어짐", "헤어졌", "헤어지", "실연", "슬프", "우울", "힘들", "짜증", "지치", "답답", "눈물"
    ]
    positive_keywords = [
        "성공", "합격", "해냈", "기쁘", "행복", "축하", "만족", "좋았"
    ]
    if any(k in text for k in negative_keywords):
        return "Negative"
    if any(k in text for k in positive_keywords):
        return "Positive"
    return "Neutral"
# --- 2단계: 음악 추천 함수 (이중 매핑) ---
def recommend_music(sentiment, diary_text):
    # 이중 매핑을 위한 상황 분석
    text_lower = diary_text.lower()
    detected_situation = "default"
    
    # 1. 키워드 검사: 감정과 무관하게 먼저 상황을 탐지
    for situation, keywords in SITUATION_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            detected_situation = situation
            break

    # 1.5 상황에 따라 감정 보정 (브레이크업/스트레스는 Negative, 성취는 Positive로 보정)
    if detected_situation in ("Breakup", "Stress"):
        sentiment = "Negative"
    elif detected_situation == "Achievement":
        sentiment = "Positive"

    # 2. 매핑 및 URL 반환
    # 해당 감정과 상황에 맞는 리스트를 가져오거나, 감정의 기본 리스트를 사용
    sentiment_data = MAPPING_DATA.get(sentiment, MAPPING_DATA["Neutral"])
    music_list = sentiment_data.get(detected_situation, sentiment_data["default"])
    
    return random.choice(music_list), detected_situation # URL과 상황 이름 반환


# --- MCP 서버 엔드포인트 ---
@app.route('/mcp/recommend', methods=['POST'])
def recommend():
    try:
        data = request.get_json()
        diary_text = data.get('diary')
        title = (data.get('title') or '').strip() or None
        weather = (data.get('weather') or '').strip() or None
        save_date = (data.get('date') or '').strip() or None  # YYYY-MM-DD (optional)

        if not diary_text:
            return jsonify({"error": "일기 내용(diary)을 입력해주세요."}), 400

        # 1단계: 감정 분석 실행
        sentiment = analyze_sentiment(diary_text)

        # 2단계: 음악 추천 실행 (이중 매핑)
        music_url, detected_situation = recommend_music(sentiment, diary_text)
        
        # 분석된 상황이 default가 아니면 메시지 생성
        if detected_situation != "default":
            message = f"분석된 감정은 '{sentiment}'이며, '{detected_situation}' 상황에 맞는 음악을 추천했습니다."
        else:
            message = f"분석된 감정 '{sentiment}'에 따라 기본 음악을 추천했습니다."

        # 저장 플래그가 있으면 DB에 보관
        should_save = bool(data.get('save'))
        if should_save:
            conn = sqlite3.connect(DB_PATH)
            try:
                # 하나의 날짜에는 하나의 글만 허용: 존재 시 거절
                from datetime import datetime as _dt
                target_date = (save_date or _dt.now().strftime('%Y-%m-%d'))
                exists = conn.execute(
                    "SELECT id FROM diaries WHERE date(created_at)=? LIMIT 1",
                    (target_date,)
                ).fetchone()
                if exists:
                    return jsonify({
                        "error": "오늘은 이미 일기를 작성하였습니다.",
                        "existing_id": exists[0]
                    }), 409
                conn.execute(
                    (
                        "INSERT INTO diaries(title, content, sentiment, situation, weather, recommended_url, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, COALESCE(datetime(? || ' ' || time('now','localtime')), CURRENT_TIMESTAMP))"
                    ),
                    (
                        title,
                        diary_text,
                        sentiment,
                        detected_situation,
                        weather,
                        music_url,
                        target_date,
                    )
                )
                conn.commit()
            finally:
                conn.close()

        # 최종 결과 반환: 음악 링크만 제공
        return jsonify({
            "recommended_music_url": music_url
        })

    except Exception as e:
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

@app.get('/debug/check_urls')
def debug_check_urls():
    """현재 매핑된 YouTube URL들의 도달 가능 여부를 점검합니다."""
    # MAPPING_DATA에서 모든 URL 수집
    urls = []
    for sentiment_data in MAPPING_DATA.values():
        for url_list in sentiment_data.values():
            urls.extend(url_list)

    results = []
    for u in urls:
        try:
            resp = requests.head(u, allow_redirects=True, timeout=8)
            if resp.status_code >= 400:
                resp = requests.get(u, allow_redirects=True, timeout=8)
            results.append({
                "url": u,
                "status": resp.status_code,
                "final_url": resp.url,
                "ok": resp.status_code < 400
            })
        except Exception as e:
            results.append({
                "url": u,
                "status": None,
                "final_url": None,
                "ok": False,
                "error": str(e)
            })

    return jsonify({"count": len(results), "results": results})

@app.post('/diary/save')
def diary_save():
    data = request.get_json() or {}
    diary_text = (data.get('diary') or '').strip()
    title = (data.get('title') or '').strip() or None
    weather = (data.get('weather') or '').strip() or None
    save_date = (data.get('date') or '').strip() or None
    if not diary_text:
        return jsonify({"error": "일기 내용(diary)을 입력해주세요."}), 400

    # 추천까지 하고 저장
    sentiment = analyze_sentiment(diary_text)
    music_url, detected_situation = recommend_music(sentiment, diary_text)

    conn = sqlite3.connect(DB_PATH)
    try:
        # 중복 날짜 검사
        from datetime import datetime as _dt
        target_date = (save_date or _dt.now().strftime('%Y-%m-%d'))
        exists = conn.execute(
            "SELECT id FROM diaries WHERE date(created_at)=? LIMIT 1",
            (target_date,)
        ).fetchone()
        if exists:
            return jsonify({"error": "오늘은 이미 일기를 작성하였습니다.", "existing_id": exists[0]}), 409
        conn.execute(
            (
                "INSERT INTO diaries(title, content, sentiment, situation, weather, recommended_url, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, COALESCE(datetime(? || ' ' || time('now','localtime')), CURRENT_TIMESTAMP))"
            ),
            (title, diary_text, sentiment, detected_situation, weather, music_url, target_date)
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify({"recommended_music_url": music_url})

@app.get('/diary/list')
def diary_list():
    date_str = (request.args.get('date') or '').strip()  # YYYY-MM-DD
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if date_str:
            rows = conn.execute(
                "SELECT id, title, content, sentiment, situation, weather, recommended_url, created_at FROM diaries WHERE date(created_at)=? ORDER BY id DESC LIMIT 200",
                (date_str,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, content, sentiment, situation, weather, recommended_url, created_at FROM diaries ORDER BY id DESC LIMIT 50"
            ).fetchall()
        items = [dict(r) for r in rows]
    finally:
        conn.close()
    return jsonify({"items": items})

@app.put('/diary/update')
def diary_update():
    data = request.get_json() or {}
    diary_id = data.get('id')
    title = (data.get('title') or '').strip() or None
    diary_text = (data.get('diary') or '').strip()
    weather = (data.get('weather') or '').strip() or None
    if not diary_id:
        return jsonify({"error": "id가 필요합니다."}), 400
    if not diary_text:
        return jsonify({"error": "일기 내용을 입력해주세요."}), 400

    sentiment = analyze_sentiment(diary_text)
    music_url, detected_situation = recommend_music(sentiment, diary_text)

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute("SELECT id, date(created_at) AS d FROM diaries WHERE id=?", (diary_id,)).fetchone()
        if not cur:
            return jsonify({"error": "존재하지 않는 일기입니다."}), 404
        # 하루가 지나면 수정 불가
        from datetime import datetime as _dt
        if cur[1] < _dt.now().strftime('%Y-%m-%d'):
            return jsonify({"error": "하루가 지나 수정할 수 없습니다."}), 403
        conn.execute(
            "UPDATE diaries SET title=?, content=?, sentiment=?, situation=?, weather=?, recommended_url=? WHERE id=?",
            (title, diary_text, sentiment, detected_situation, weather, music_url, diary_id)
        )
        conn.commit()
    finally:
        conn.close()
    return jsonify({"recommended_music_url": music_url})

@app.get('/favorites')
def favorites_list():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT f.id AS fav_id, d.id AS diary_id, d.title, d.content, d.created_at
            FROM favorites f
            JOIN diaries d ON d.id=f.diary_id
            ORDER BY f.id DESC LIMIT 100
            """
        ).fetchall()
        items = [dict(r) for r in rows]
    finally:
        conn.close()
    return jsonify({"items": items})

@app.post('/favorites/toggle')
def favorites_toggle():
    data = request.get_json() or {}
    diary_id = data.get('diary_id')
    if not diary_id:
        return jsonify({"error": "diary_id가 필요합니다."}), 400
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute("SELECT id FROM diaries WHERE id=?", (diary_id,)).fetchone()
        if not cur:
            return jsonify({"error": "존재하지 않는 일기입니다."}), 404
        cur2 = conn.execute("SELECT id FROM favorites WHERE diary_id=?", (diary_id,)).fetchone()
        if cur2:
            conn.execute("DELETE FROM favorites WHERE diary_id=?", (diary_id,))
            conn.commit()
            return jsonify({"favorited": False})
        else:
            conn.execute("INSERT INTO favorites(diary_id) VALUES (?)", (diary_id,))
            conn.commit()
            return jsonify({"favorited": True})
    finally:
        conn.close()

@app.get('/comments')
def comments_list():
    diary_id = request.args.get('diary_id')
    if not diary_id:
        return jsonify({"error": "diary_id가 필요합니다."}), 400
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, diary_id, content, created_at FROM comments WHERE diary_id=? ORDER BY id DESC LIMIT 200",
            (diary_id,)
        ).fetchall()
        items = [dict(r) for r in rows]
    finally:
        conn.close()
    return jsonify({"items": items})

@app.post('/comments')
def comments_add():
    data = request.get_json() or {}
    diary_id = data.get('diary_id')
    content = (data.get('content') or '').trim() if hasattr(str, 'trim') else (data.get('content') or '').strip()
    if not diary_id or not content:
        return jsonify({"error": "diary_id와 content가 필요합니다."}), 400
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute("SELECT id FROM diaries WHERE id=?", (diary_id,)).fetchone()
        if not cur:
            return jsonify({"error": "존재하지 않는 일기입니다."}), 404
        conn.execute("INSERT INTO comments(diary_id, content) VALUES (?, ?)", (diary_id, content))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"ok": True})

@app.delete('/comments')
def comments_delete():
    data = request.get_json(silent=True) or {}
    comment_id = data.get('id') or request.args.get('id')
    if not comment_id:
        return jsonify({"error": "id가 필요합니다."}), 400
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute("SELECT id FROM comments WHERE id=?", (comment_id,)).fetchone()
        if not cur:
            return jsonify({"error": "존재하지 않는 댓글입니다."}), 404
        conn.execute("DELETE FROM comments WHERE id=?", (comment_id,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"ok": True})

@app.get('/diary/dates')
def diary_dates():
    """특정 월(YYYY-MM)에 저장된 일기 날짜 목록 반환."""
    month = (request.args.get('month') or '').strip()  # YYYY-MM
    if not month:
        # 기본: 오늘 기준 월
        from datetime import datetime
        month = datetime.now().strftime('%Y-%m')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT date(created_at) AS d, COUNT(*) AS c FROM diaries WHERE strftime('%Y-%m', created_at)=? GROUP BY d ORDER BY d",
            (month,)
        ).fetchall()
        days = [r['d'] for r in rows]
    finally:
        conn.close()
    return jsonify({"month": month, "days": days})

@app.get('/diary/get')
def diary_get():
    diary_id = request.args.get('id')
    if not diary_id:
        return jsonify({"error": "id 파라미터가 필요합니다."}), 400
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, title, content, sentiment, situation, weather, recommended_url, created_at FROM diaries WHERE id=?",
            (diary_id,)
        ).fetchone()
        if not row:
            return jsonify({"error": "존재하지 않는 일기입니다."}), 404
        return jsonify(dict(row))
    finally:
        conn.close()

@app.delete('/diary/delete')
def diary_delete():
    data = request.get_json(silent=True) or {}
    diary_id = data.get('id') or request.args.get('id')
    if not diary_id:
        return jsonify({"error": "id가 필요합니다."}), 400
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute("SELECT id FROM diaries WHERE id=?", (diary_id,)).fetchone()
        if not cur:
            return jsonify({"error": "존재하지 않는 일기입니다."}), 404
        conn.execute("DELETE FROM diaries WHERE id=?", (diary_id,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"ok": True})

@app.get('/profile')
def profile_get():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT id, name, photo_url, updated_at FROM profiles WHERE id=1").fetchone()
        if not row:
            return jsonify({"error": "프로필이 없습니다."}), 404
        return jsonify(dict(row))
    finally:
        conn.close()

@app.post('/profile')
def profile_set():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({"error": "이름을 입력하세요."}), 400
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("UPDATE profiles SET name=?, updated_at=CURRENT_TIMESTAMP WHERE id=1", (name,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"ok": True})

@app.post('/profile/photo')
def profile_photo_upload():
    # 업로드 폴더 보장
    uploads_dir = Path(__file__).with_name('static') / 'uploads'
    uploads_dir.mkdir(parents=True, exist_ok=True)

    if 'photo' not in request.files:
        return jsonify({"error": "photo 파일을 업로드하세요."}), 400
    file = request.files['photo']
    if not file or file.filename == '':
        return jsonify({"error": "유효한 파일이 아닙니다."}), 400

    # 간단한 확장자 검증
    allowed = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        return jsonify({"error": "이미지 파일만 업로드 가능합니다."}), 400

    filename = f"profile_{uuid.uuid4().hex}{ext}"
    save_path = uploads_dir / filename
    file.save(save_path.as_posix())

    # static 경로 기준 URL 구성
    public_url = url_for('static', filename=f"uploads/{filename}")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("UPDATE profiles SET photo_url=?, updated_at=CURRENT_TIMESTAMP WHERE id=1", (public_url,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"ok": True, "photo_url": public_url})

if __name__ == '__main__':
    # 서버 실행
    app.run(host='0.0.0.0', port=5000, debug=True)
>>>>>>> 0b0355ea399da68e038f71b7d2e69a0d3f915d9b
