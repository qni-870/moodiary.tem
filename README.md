# 일기 감정 분석 기반 음악 추천 MCP 서버

HyperCLOVA X API를 활용한 일기 감정 분석 및 음악 추천 서비스입니다.

## 🚀 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정
레포지토리에는 자리표시자만 담긴 `env.example`가 포함되어 있습니다. 이를 복사해 `.env`를 만들고 실제 키를 입력하세요 (본 프로젝트는 `.env`가 없을 경우 `env.example`를 로드하며, 파일 값을 OS 환경변수보다 우선 적용합니다):

```bash
# .env 파일 생성
cp env.example .env

# .env 파일 편집 (실제 API 키 입력)
CLOVA_API_KEY=your_actual_api_key
CLOVA_API_KEY_ID=your_actual_api_key_id
CLOVA_API_URL=https://clovastudio.stream.ntruss.com/
# Chat Completions는 HCX-003 또는 HCX-DASH-001만 지원
CLOVA_MODEL=HCX-003
```

### 3. 서버 실행
```bash
python app.py
```

서버가 `http://localhost:5000`에서 실행됩니다.

## 🔑 API 키 발급 및 헤더

1. [네이버 클라우드 플랫폼](https://www.ncloud.com/) 접속
2. HyperCLOVA X 서비스 활성화
3. 테스트 앱 생성 후 API 키 발급 (예: `nv-...`)
4. `.env` 파일에 실제 키 값 입력

요청 헤더 (공식 스펙):

```http
Authorization: Bearer nv-****************
X-NCP-CLOVASTUDIO-REQUEST-ID: <UUID>
Content-Type: application/json
```

엔드포인트 (공식 스펙):

```
POST {CLOVA_API_URL}/v1/chat-completions/{CLOVA_MODEL}
# 예) https://clovastudio.stream.ntruss.com/v1/chat-completions/HCX-003
```

요청 바디 (예시):

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant for sentiment classification."},
    {"role": "user", "content": "분석 프롬프트"}
  ],
  "maxTokens": 64,
  "temperature": 0.3,
  "topP": 0.8
}
```

응답 파싱:

```json
{
  "status": {"code": "20000", "message": "OK"},
  "result": {
    "message": {"role": "assistant", "content": "Positive|Negative|Neutral"}
  }
}
```

## 📡 MCP API

### POST /mcp/recommend
일기 내용을 분석하여 감정에 맞는 음악을 추천합니다.

**요청:**
```json
{
  "diary": "오늘 하루 일기 내용",
  "title": "일기 제목 (선택사항)",
  "weather": "날씨 (선택사항)",
  "save": true
}
```

**응답:**
```json
{
  "recommended_music_url": "https://youtube.com/watch?v=..."
}
```

## 🛡️ 보안

- `.env` 파일은 Git에 커밋되지 않습니다 (이미 `.gitignore` 적용)
- 실제 API 키는 절대 공개 저장소에 업로드하지 마세요
- `env.example`은 예시 파일로만 사용하며, 레포지토리에 포함됩니다 (실제 키 금지)

추가 권장 설정:
- `logs/`, `static/uploads/` 디렉터리는 `.gitignore`에 포함
- `env.example`에는 실제 키를 넣지 말고 자리표시자 사용 (커밋 허용)

## 🧪 트러블슈팅

- 400 Bad Request + `.../HCX-D001`가 보이면 모델명을 `HCX-003`으로 변경 후 서버 재시작
- 401 Unauthorized: API 키 유효성/서비스 활성화/테스트 앱 여부 확인
- 404 Not Found: 엔드포인트를 `/v1/chat-completions/{model}`로 확인
- DNS 오류: `clovastudio.stream.ntruss.com`이 정상 해석되는지 확인

## 🔧 기능

- 일기 감정 분석 (Positive/Negative/Neutral)
- 감정 기반 음악 추천
- 일기 저장 및 관리
- 즐겨찾기 및 댓글 기능
- 프로필 관리

## 📝 라이선스

MIT License
