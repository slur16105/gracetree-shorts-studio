# 외부 배포 릴리즈 체크리스트 (Story 2.17)

배포 담당자가 외부 배포 전에 다음 항목을 순서대로 확인한다.

## 1. 사전 조건

- [ ] Story 2.15 오프라인 스모크 테스트 PASS (Windows + macOS)
- [ ] Story 2.16 7일 안정성 검증 PASS (`tests/stability/stability-report-template.md` 작성 완료)
- [ ] CI 시크릿 설정 완료:
  - `CSC_LINK` (Windows PFX — Base64 인코딩)
  - `CSC_KEY_PASSWORD`
  - `CSC_LINK_MAC` (macOS 인증서 — Base64)
  - `CSC_KEY_PASSWORD_MAC`
  - `APPLE_ID`
  - `APPLE_APP_SPECIFIC_PASSWORD`
  - `APPLE_TEAM_ID`

## 2. 빌드 검증

- [ ] `RELEASE_CHANNEL=external` 로 빌드가 완료됨
- [ ] `scripts/verify-package.mjs` PASS (각 플랫폼)
- [ ] `scripts/verify-signing.mjs --channel external` PASS (각 플랫폼)

## 3. Windows 서명 확인

```powershell
# Windows에서 실행:
signtool verify /pa /v "GraceTree Shorts Studio-<version>-windows-x64-setup.exe"
# Expected: "Successfully verified"
```

- [ ] Authenticode 서명 유효
- [ ] 타임스탬프 포함
- [ ] 서명 체인이 신뢰된 루트까지 연결됨

## 4. macOS 서명 + Notarization 확인

```bash
# 서명 확인
codesign --verify --deep --strict --verbose=2 "GraceTree Shorts Studio.app"

# Notarization + Stapling 확인
spctl --assess --verbose=2 --type open --context context:primary-signature \
  "GraceTree-Shorts-Studio-<version>-macos-arm64.dmg"

# Staple 확인
stapler validate "GraceTree-Shorts-Studio-<version>-macos-arm64.dmg"
```

- [ ] codesign 검증 통과
- [ ] Hardened Runtime 활성화 확인
- [ ] spctl ACCEPTED
- [ ] Notarization ticket stapled

## 5. 시크릿 노출 확인

- [ ] CI 빌드 로그에 인증서/비밀번호가 평문으로 노출되지 않음
- [ ] 릴리즈 artifact에 서명 키 포함 안 됨
- [ ] GitHub Release body에 `channel=external` 표시 확인

## 6. 자동 업데이트 미포함 확인

- [ ] `apps/desktop/electron-builder.yml`의 `publish: null` 유지
- [ ] Electron `autoUpdater` API 코드 없음: `grep -r "autoUpdater" apps/desktop/src/`
- [ ] 앱이 실행 중 외부로 버전 체크 연결하지 않음

## 7. 최종 승인

배포 승인자:
날짜:
배포 버전:
