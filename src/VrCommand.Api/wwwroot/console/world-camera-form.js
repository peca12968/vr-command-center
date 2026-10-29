const $ = id => document.getElementById(id);
const degrees = radians => radians * 180 / Math.PI;

// A local camera draft. Incoming frames and bookmark reads never replace edits.
// Persistence still goes through the existing authenticated bookmark controls.
export function mountWorldCameraForm(getScene, applied) {
  const names = ['x', 'y', 'z', 'azimuth', 'elevation', 'distance'];
  const input = name => $('world-camera-' + name);
  let session = null;
  function message(text, error = false) {
    $('world-camera-message').textContent = text;
    $('world-camera-message').classList.toggle('replay-error', error);
  }
  function read() {
    const scene = getScene(); if (!session || !scene) return;
    const view = scene.view();
    const values = [...view.target, degrees(view.theta), degrees(Math.PI / 2 - view.phi), view.radius];
    names.forEach((name, index) => { input(name).value = String(values[index]); });
    message('已讀取目前鏡頭；編輯後按套用，不會自動保存為書籤。');
  }
  function apply() {
    const scene = getScene(); if (!session || !scene) return;
    const values = names.map(name => input(name).valueAsNumber);
    const [x, y, z, azimuth, elevation, radius] = values;
    const phi = Math.PI / 2 - elevation * Math.PI / 180;
    if (!values.every(Number.isFinite) || [x, y, z].some(value => Math.abs(value) > 120)
      || Math.abs(azimuth) > 180 || phi < .06 - 1e-12 || phi > 1.5 + 1e-12 || radius < 2 || radius > 240) {
      message('請填完整數值：看向座標各 ±120 公尺、水平角 ±180°、俯視角約 4.057–86.562°、距離 2–240 公尺。', true);
      return;
    }
    scene.restoreView({ target: [x, y, z], theta: azimuth * Math.PI / 180, phi: Math.max(.06, Math.min(1.5, phi)), radius });
    applied(); message('已套用自由鏡頭。需要日後切換時，請在下方命名保存目前位置。');
  }
  $('world-camera-read').addEventListener('click', read);
  $('world-camera-apply').addEventListener('click', apply);
  $('world-camera-editor').addEventListener('keydown', event => {
    if (event.key === 'Enter' && event.target instanceof HTMLInputElement) { event.preventDefault(); apply(); }
  });
  function reset() {
    session = null; $('world-camera-editor').disabled = true;
    names.forEach(name => { input(name).value = ''; }); message('');
  }
  reset();
  return { reset, bind(id) {
    if (session === id) return;
    reset(); if (!id) return;
    session = id; $('world-camera-editor').disabled = false; read();
  } };
}
