# 🚀 Render 무료 배포 가이드

## 📋 배포 준비 체크리스트

✅ 배포 설정 파일 생성 완료
- `render.yaml` - Render 배포 설정
- `requirements.txt` - Python 의존성
- `.gitignore` - Git 제외 파일
- `app.py` - 프로덕션 환경 대응 완료

## 🌐 Render 배포 단계별 가이드

### 1단계: GitHub 레포지토리 생성

1. **GitHub에서 새 레포지토리 생성**
   - 레포지토리 이름: `opendart-finance-analyzer` (또는 원하는 이름)
   - Public 또는 Private 선택 (둘 다 가능)
   - README, .gitignore는 체크하지 마세요 (이미 있음)

2. **로컬 Git 설정 및 푸시**
   ```bash
   # Git 초기화
   git init
   
   # 파일 추가
   git add .
   
   # 첫 커밋
   git commit -m "Initial commit: OpenDART Finance Analyzer"
   
   # GitHub 레포지토리 연결 (YOUR_USERNAME을 실제 사용자명으로 변경)
   git remote add origin https://github.com/YOUR_USERNAME/opendart-finance-analyzer.git
   
   # 메인 브랜치로 푸시
   git branch -M main
   git push -u origin main
   ```

### 2단계: Render에서 웹 서비스 생성

1. **Render 계정 생성 및 로그인**
   - https://render.com 접속
   - GitHub 계정으로 로그인 (권장)

2. **새 웹 서비스 생성**
   - Dashboard에서 "New +" 클릭
   - "Web Service" 선택
   - GitHub 레포지토리 연결

3. **서비스 설정**
   - **Name**: `opendart-finance-analyzer`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && python xml_to_db.py`
   - **Start Command**: `python app.py`
   - **Plan**: `Free` 선택

4. **환경 변수 설정**
   - `FLASK_ENV` = `production`
   - `PYTHONUNBUFFERED` = `1`

### 3단계: 배포 완료 및 확인

1. **자동 배포 시작**
   - Render가 자동으로 빌드 및 배포 시작
   - 빌드 로그에서 진행 상황 확인

2. **배포 완료 확인**
   - 배포 완료 후 제공되는 URL로 접속
   - 예: `https://opendart-finance-analyzer.onrender.com`

3. **기능 테스트**
   - 웹페이지 정상 로딩 확인
   - 회사 검색 기능 테스트
   - API 엔드포인트 동작 확인

## 🔧 Render 무료 플랜 특징

### ✅ 장점
- **완전 무료** (월 750시간 제공)
- **자동 SSL** 인증서 제공
- **GitHub 연동** 자동 배포
- **커스텀 도메인** 지원
- **로그 및 모니터링** 제공

### ⚠️ 제한사항
- **콜드 스타트**: 15분 비활성 후 슬립 모드
- **빌드 시간**: 최대 90초
- **메모리**: 512MB RAM
- **대역폭**: 100GB/월

## 🛠️ 배포 후 관리

### 코드 업데이트
```bash
# 코드 수정 후
git add .
git commit -m "Update: 변경사항 설명"
git push origin main
# → Render에서 자동으로 재배포됨
```

### 로그 확인
- Render Dashboard → 서비스 선택 → "Logs" 탭

### 도메인 연결 (선택사항)
- Dashboard → Settings → Custom Domains

## 🚨 문제 해결

### 빌드 실패 시
1. **로그 확인**: Render 대시보드에서 빌드 로그 확인
2. **의존성 문제**: `requirements.txt` 확인
3. **데이터베이스**: `companies.db` 파일 존재 확인

### 느린 응답 시
- 무료 플랜의 콜드 스타트 현상 (정상)
- 첫 접속 시 15-30초 소요 가능

### API 키 관리
- 환경 변수로 민감한 정보 관리
- GitHub에 API 키 노출 금지

## 📞 지원

배포 중 문제가 발생하면:
1. Render 공식 문서 확인
2. GitHub Issues 생성
3. Render 커뮤니티 포럼 활용

---

**🎉 축하합니다! 이제 전 세계 어디서든 접속 가능한 웹 서비스가 완성되었습니다!**
