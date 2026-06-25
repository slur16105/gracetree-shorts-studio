import { useState } from 'react'

import styles from './GuideView.module.css'

type SectionKey = 'first-video' | 'file-naming' | 'script' | 'troubleshoot' | 'storage' | 'about'

interface Section {
  key: SectionKey
  label: string
  headingId: string
}

const SECTIONS: Section[] = [
  { key: 'first-video', label: '첫 영상 만들기', headingId: 'guide-first-video' },
  { key: 'file-naming', label: '파일명 규칙', headingId: 'guide-file-naming' },
  { key: 'script', label: '스크립트 작성법', headingId: 'guide-script' },
  { key: 'troubleshoot', label: '오류 해결', headingId: 'guide-troubleshoot' },
  { key: 'storage', label: '저장 위치', headingId: 'guide-storage' },
  { key: 'about', label: '앱 정보', headingId: 'guide-about' }
]

export function GuideView(): React.JSX.Element {
  const [activeSection, setActiveSection] = useState<SectionKey>('first-video')

  const currentSection = SECTIONS.find((s) => s.key === activeSection)!

  return (
    <div className={styles.layout}>
      <nav aria-label="가이드 섹션" className={styles.sectionNav}>
        <ul className={styles.navList}>
          {SECTIONS.map((section) => (
            <li key={section.key}>
              <button
                aria-current={activeSection === section.key ? 'true' : undefined}
                className={styles.navButton}
                onClick={() => setActiveSection(section.key)}
                type="button"
              >
                {section.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div aria-labelledby={currentSection.headingId} className={styles.content} role="region">
        {activeSection === 'first-video' && (
          <FirstVideoSection headingId={currentSection.headingId} />
        )}
        {activeSection === 'file-naming' && (
          <FileNamingSection headingId={currentSection.headingId} />
        )}
        {activeSection === 'script' && <ScriptSection headingId={currentSection.headingId} />}
        {activeSection === 'troubleshoot' && (
          <TroubleshootSection headingId={currentSection.headingId} />
        )}
        {activeSection === 'storage' && <StorageSection headingId={currentSection.headingId} />}
        {activeSection === 'about' && <AboutSection headingId={currentSection.headingId} />}
      </div>
    </div>
  )
}

interface SectionProps {
  headingId: string
}

function FirstVideoSection({ headingId }: SectionProps): React.JSX.Element {
  return (
    <>
      <h2 id={headingId}>첫 영상 만들기</h2>
      <p className={styles.sectionLead}>
        아래 3단계를 순서대로 진행하면 첫 영상을 만들 수 있습니다.
      </p>
      <ol className={styles.stepList}>
        <li>
          <article className={styles.guideCard}>
            <h3 className={styles.cardStep}>1단계</h3>
            <h4 className={styles.cardTitle}>게시 날짜 선택</h4>
            <p>
              홈 화면에서 게시 날짜 버튼을 클릭해 달력을 엽니다. 날짜를 선택하면 해당 날짜의 작업이
              자동으로 생성되거나 복원됩니다.
            </p>
          </article>
        </li>
        <li>
          <article className={styles.guideCard}>
            <h3 className={styles.cardStep}>2단계</h3>
            <h4 className={styles.cardTitle}>파일 등록·검증</h4>
            <p>
              썸네일, 음성, 영상, 스크립트 파일을 드래그하거나 파일 선택 버튼으로 등록합니다. 각
              슬롯의 상태 표시로 파일이 올바르게 인식되었는지 확인하세요.
            </p>
          </article>
        </li>
        <li>
          <article className={styles.guideCard}>
            <h3 className={styles.cardStep}>3단계</h3>
            <h4 className={styles.cardTitle}>생성·결과 확인</h4>
            <p>
              모든 슬롯이 정상 상태가 되면 영상 생성을 시작할 수 있습니다. 완료된 결과물은 게시 날짜
              작업 폴더의 output 디렉터리에 저장됩니다.
            </p>
          </article>
        </li>
      </ol>
    </>
  )
}

function FileNamingSection({ headingId }: SectionProps): React.JSX.Element {
  return (
    <>
      <h2 id={headingId}>파일명 규칙</h2>
      <p className={styles.sectionLead}>
        파일명 앞부분으로 역할이 자동 분류됩니다. 올바른 이름을 사용하면 파일을 등록할 때 역할을
        직접 지정하지 않아도 됩니다.
      </p>
      <ul className={styles.ruleList}>
        <li>
          <strong>
            <code>voice.*</code>
          </strong>{' '}
          — 음성 파일 (예: <code>voice.mp3</code>, <code>voice.wav</code>)
        </li>
        <li>
          <strong>
            <code>bgm.*</code>
          </strong>{' '}
          — 배경 음악 파일 (예: <code>bgm.mp3</code>)
        </li>
        <li>
          기타 파일은 <strong>미분류</strong>로 등록되며, 역할 선택 드롭다운으로 직접 지정해야
          합니다.
        </li>
      </ul>
      <h3>올바른 파일명 예시</h3>
      <ul className={styles.exampleList}>
        <li>
          <code>voice.mp3</code> → 음성 역할로 자동 분류
        </li>
        <li>
          <code>bgm.mp3</code> → 배경음악 역할로 자동 분류
        </li>
        <li>
          <code>recording.mp3</code> → 미분류 (역할 지정 필요)
        </li>
      </ul>
      <h3>수정 예시</h3>
      <p>
        파일이 미분류로 등록된 경우, 파일명을 변경한 뒤 다시 등록하거나 슬롯의 역할 선택 드롭다운을
        사용하세요.
      </p>
      <ul className={styles.exampleList}>
        <li>
          변경 전: <code>my-recording.mp3</code> (미분류)
        </li>
        <li>
          변경 후: <code>voice.mp3</code> → 음성으로 자동 인식
        </li>
      </ul>
    </>
  )
}

function ScriptSection({ headingId }: SectionProps): React.JSX.Element {
  return (
    <>
      <h2 id={headingId}>스크립트 작성법</h2>
      <p className={styles.sectionLead}>
        스크립트 파일은 구역 태그로 내용을 구분합니다. 세 구역 모두 필수이며 순서대로 작성해야
        합니다.
      </p>
      <h3>필수 구역</h3>
      <ul className={styles.ruleList}>
        <li>
          <code>[제목]</code> — 영상 제목 텍스트
        </li>
        <li>
          <code>[말씀]</code> — 성경 구절 또는 본문
        </li>
        <li>
          <code>[기도]</code> — 기도 내용
        </li>
      </ul>
      <h3>스크립트 예시</h3>
      <pre className={styles.codeBlock}>
        <code>{`[제목]
오늘의 은혜

[말씀]
하나님이 세상을 이처럼 사랑하사
독생자를 주셨으니
이는 그를 믿는 자마다
멸망하지 않고 영생을 얻게 하려 하심이라
(요한복음 3:16)

[기도]
주님, 오늘 하루도 주님의 사랑 안에
거하게 하옵소서. 아멘.`}</code>
      </pre>
      <h3>수정 예시</h3>
      <p>구역 태그가 없거나 오탈자가 있으면 파일이 거부됩니다. 다음 예시처럼 정확히 입력하세요.</p>
      <ul className={styles.exampleList}>
        <li>
          잘못된 예: <code>[Title]</code>, <code>[제 목]</code> (공백 포함), <code>제목:</code>
        </li>
        <li>
          올바른 예: <code>[제목]</code>, <code>[말씀]</code>, <code>[기도]</code>
        </li>
      </ul>
    </>
  )
}

function TroubleshootSection({ headingId }: SectionProps): React.JSX.Element {
  return (
    <>
      <h2 id={headingId}>오류 해결</h2>
      <p className={styles.sectionLead}>파일 등록 중 자주 발생하는 오류와 해결 방법입니다.</p>
      <ul className={styles.troubleshootList}>
        <li>
          <strong>지원하지 않는 파일 형식</strong>
          <p>음성은 MP3·WAV, 영상은 MP4·MOV, 스크립트는 TXT 파일을 사용하세요.</p>
        </li>
        <li>
          <strong>파일을 읽을 수 없음</strong>
          <p>
            파일이 다른 앱에서 열려 있거나 권한이 없을 수 있습니다. 파일을 닫은 뒤 다시 선택하세요.
          </p>
        </li>
        <li>
          <strong>앱 관리 폴더의 파일은 재등록 불가</strong>
          <p>
            앱이 관리하는 폴더 안의 파일은 직접 등록할 수 없습니다. 원본 파일 위치에서 다시
            선택하세요.
          </p>
        </li>
        <li>
          <strong>바로가기·심볼릭 링크 거부</strong>
          <p>파일 바로가기 대신 실제 파일을 직접 선택하거나 드래그하세요.</p>
        </li>
        <li>
          <strong>파일 크기 초과</strong>
          <p>지원하는 최대 크기를 초과한 파일입니다. 파일 용량을 줄인 뒤 다시 등록하세요.</p>
        </li>
        <li>
          <strong>같은 이름의 파일이 이미 있음</strong>
          <p>기존 파일 슬롯의 교체 버튼을 사용해 파일을 교체하세요.</p>
        </li>
        <li>
          <strong>파일 복사 실패</strong>
          <p>
            저장 공간이 부족하거나 폴더 쓰기 권한이 없을 수 있습니다. 저장 공간을 확인하고 다시
            시도하세요.
          </p>
        </li>
      </ul>
    </>
  )
}

function StorageSection({ headingId }: SectionProps): React.JSX.Element {
  return (
    <>
      <h2 id={headingId}>저장 위치</h2>
      <p className={styles.sectionLead}>
        모든 파일은 게시 날짜별 작업 폴더에 저장됩니다. 폴더 구조는 다음과 같습니다.
      </p>
      <ul className={styles.storageList}>
        <li>
          <strong>입력 파일</strong> (<code>input/</code>)
          <p>
            등록한 음성, 배경음악, 스크립트, 썸네일 파일이 복사됩니다. 원본 파일은 변경되지
            않습니다.
          </p>
        </li>
        <li>
          <strong>결과물</strong> (<code>output/</code>)
          <p>영상 생성이 완료되면 결과 영상 파일이 저장됩니다.</p>
        </li>
        <li>
          <strong>처리 로그</strong> (<code>logs/</code>)
          <p>
            영상 생성 중 발생한 오류나 경과 정보가 기록됩니다. 문제가 발생했을 때 로그 파일을
            확인하세요.
          </p>
        </li>
      </ul>
      <p>
        작업 폴더의 위치는 앱이 사용하는 데이터 디렉터리 아래에 게시 날짜 이름으로 만들어집니다.
        절대 경로는 운영 체제와 설치 환경에 따라 다르지만, 앱 안에서 날짜를 선택하면 해당 폴더가
        자동으로 준비됩니다.
      </p>
    </>
  )
}

function AboutSection({ headingId }: SectionProps): React.JSX.Element {
  return (
    <>
      <h2 id={headingId}>앱 정보</h2>
      <p className={styles.sectionLead}>
        GraceTree Shorts Studio는 교회 단편 영상을 로컬에서 제작하기 위한 도구입니다.
      </p>
      <ul className={styles.ruleList}>
        <li>모든 처리는 인터넷 연결 없이 로컬에서 실행됩니다.</li>
        <li>저장된 데이터는 이 기기의 앱 데이터 폴더에만 보관됩니다.</li>
        <li>외부 서버로 파일이나 개인 정보를 전송하지 않습니다.</li>
      </ul>
      <h3>현재 버전 기능</h3>
      <ul className={styles.ruleList}>
        <li>날짜별 작업 생성 및 관리</li>
        <li>입력 파일 등록 및 자동 분류</li>
        <li>스크립트 기반 자막 생성</li>
      </ul>
    </>
  )
}
