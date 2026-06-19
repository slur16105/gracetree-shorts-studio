import electronLogo from './assets/electron.svg'

function App(): React.JSX.Element {
  return (
    <>
      <img alt="" className="logo" src={electronLogo} />
      <div className="creator">GraceTree Shorts Studio</div>
      <div className="text">안전한 로컬 영상 제작 기반이 준비되었습니다.</div>
      <p className="tip">제품 작업 흐름은 다음 Story부터 순차적으로 추가됩니다.</p>
    </>
  )
}

export default App
