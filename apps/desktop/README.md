# GraceTree Desktop

Electron + electron-vite + React/TypeScript 기반 데스크톱 애플리케이션이다.

모든 명령은 저장소 루트에서 pnpm 11.8.0을 사용해 실행한다.

```bash
pnpm install --frozen-lockfile
pnpm dev
```

검증:

```bash
pnpm typecheck
pnpm lint
pnpm test
pnpm --filter gracetree-desktop run build
```

패키징과 설치 파일 생성은 후속 Story에서 추가한다.
