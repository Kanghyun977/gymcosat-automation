# gymcosat-automation

재활 PT샵 **짐코사트(GYMCOSAT)** 의 인스타그램·네이버 블로그·티스토리 마케팅 업무 자동화.

- 인스타: 팔로워 성장 (릴스·시리즈·프로필 정비·정기 발행)
- 네이버 블로그: 검색 유입 (검색량 기반 키워드·SEO 구조)
- 티스토리: 구글 검색 유입 (네이버 글 SEO 재구성 이전 + 서치콘솔)

## 구조

```
backup/                     원본 백업 — 수정 금지
  naver_blog/
    posts_index.json        569개 글 메타 목록
    posts/<logNo>.json      제목·날짜·카테고리·본문 텍스트·이미지 URL
    html/<logNo>.html       원본 HTML
    images/<logNo>/*.jpg    본문 이미지 (git 제외, 로컬/OneDrive 보관)
  instagram/
    media/<shortcode>/      게시물 이미지·영상 원본 (git 제외)
data/
  instagram/
    profile.json            프로필 (팔로워·바이오·링크·고정 게시물·하이라이트)
    posts.json              게시물 68개 (캡션·해시태그·좋아요·댓글·공동작성자)
    post_urls.json
scripts/
  backup_naver_blog.py      네이버 블로그 전체 백업 (재실행 시 이어받기)
```

## 백업 현황 (2026-09-11)

| 채널 | 수량 | 비고 |
|---|---|---|
| 네이버 블로그 | 글 569 · 이미지 8,570 | 공개 글 전체 |
| 인스타그램 | 게시물 68 (캐러셀 49 · 이미지 18 · 릴스 1) · 미디어 389 파일 | 평균 좋아요 8.7 |

## 실행

```bash
python scripts/backup_naver_blog.py            # 이미지 포함
python scripts/backup_naver_blog.py --no-images
```

발행·수집 등 로그인이 필요한 작업은 Aside CLI(브라우저 에이전트)로 수행. 자격증명은 저장소에 두지 않음 (`.env`는 git 제외).
