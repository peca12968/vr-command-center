const challengePattern = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
const emptyChallenge = '00000000-0000-0000-0000-000000000000';
const roles = ['主控', '房間 1', '房間 2', '房間 3', '房間 4', '房間 5'];

function privateAddress(value) {
  if (typeof value !== 'string' || !/^(?:0|[1-9][0-9]{0,2})(?:\.(?:0|[1-9][0-9]{0,2})){3}$/.test(value)) return false;
  const parts = value.split('.').map(Number), [a, b] = parts;
  return parts.every(part => part <= 255) && (a === 10 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168));
}

function readWitness(value, challenge) {
  const { version, workstation, source, listener, port, observedAtUnixSeconds, signature } = value ?? {};
  if (version !== 1 || value.challenge !== challenge || !Number.isInteger(workstation) || workstation < 0 || workstation >= roles.length
      || !privateAddress(source) || !privateAddress(listener) || !Number.isInteger(port) || port < 1 || port > 65535
      || !Number.isSafeInteger(observedAtUnixSeconds) || observedAtUnixSeconds < 1 || typeof signature !== 'string' || !/^[0-9a-f]{64}$/.test(signature))
    throw new Error('Invalid workstation witness');
  return { version, challenge, workstation, source, listener, port, observedAtUnixSeconds, signature };
}

async function readJson(file) {
  if (!file.size || file.size > 16 * 1024) throw new Error('Invalid workstation file size');
  return JSON.parse(await file.text());
}

export function mountOperatorNetwork(getState, api, download, uuid) {
  const $ = suffix => document.getElementById(suffix ? 'operator-network-' + suffix : 'operator-network');
  const panel = $(), challengeInput = $('challenge'), inventoryInput = $('inventory'), receiptsInput = $('receipts');
  const issue = $('issue'), verify = $('verify'), generate = $('generate'), status = $('status'), result = $('result');
  let active = false, pending = false, generation = 0;
  const workstation = () => getState().actor?.role === 'Master' ? 0 : getState().actor?.roomId;
  const challenge = () => challengeInput.value.trim().toLowerCase();
  function update() {
    const seat = workstation(), id = challenge();
    panel.hidden = !active || location.protocol !== 'https:' || !window.isSecureContext || !Number.isInteger(seat) || !roles[seat];
    $('master').hidden = generate.hidden = seat !== 0;
    challengeInput.disabled = generate.disabled = inventoryInput.disabled = receiptsInput.disabled = panel.hidden || pending;
    issue.disabled = challengeInput.disabled || !challengePattern.test(id) || id === emptyChallenge;
    verify.disabled = issue.disabled || seat !== 0 || inventoryInput.files.length !== 1 || receiptsInput.files.length !== roles.length;
  }
  function clear() {
    status.textContent = '';
    result.replaceChildren();
    update();
  }
  async function perform(message, failed, action) {
    const id = challenge(), seat = workstation(), token = ++generation, epoch = getState().epoch;
    const current = () => token === generation && epoch === getState().epoch && active;
    pending = true;
    clear();
    status.textContent = message;
    try { await action(id, seat, current); }
    catch (error) {
      if (current()) status.textContent = error.status === 404 ? '此站台未啟用工作站核對，請開啟場館 HTTPS 網址。' : failed;
    } finally {
      if (current()) { pending = false; update(); }
    }
  }
  for (const input of [challengeInput, inventoryInput, receiptsInput]) input.addEventListener('input', clear);
  generate.addEventListener('click', () => {
    challengeInput.value = uuid();
    clear();
    challengeInput.select();
  });
  issue.addEventListener('click', () => {
    if (issue.disabled) return;
    void perform('正在向管理服務取得本站回條…', '無法取得本站回條。請確認已直接連到場館 HTTPS 網址及本輪代號。', async (id, seat, current) => {
      const witness = readWitness(await api('/operator-network/witness?challenge=' + id), id);
      if (!current()) return;
      if (witness.workstation !== seat || witness.port !== Number(location.port || 443)) throw new Error('Unexpected workstation');
      const name = seat === 0 ? 'master' : 'room' + seat;
      download(`vr-workstation-${name}-${id}.json`, new Blob([JSON.stringify(witness, null, 2) + '\n'], { type: 'application/json' }));
      status.textContent = `${roles[seat]}回條已下載。管理服務記錄的來源為 ${witness.source}。`;
    });
  });
  verify.addEventListener('click', () => {
    if (verify.disabled) return;
    const file = inventoryInput.files[0], files = [...receiptsInput.files];
    void perform('正在讀取工作站清單及回條…', '管理服務未確認六台工作站。請檢查實際來源、回條期限及管理服務是否曾重新啟動。', async (id, _, current) => {
      let inventory, witnesses;
      try {
        const { masterAddress, roomAddresses } = await readJson(file) ?? {};
        if (!Array.isArray(roomAddresses) || roomAddresses.length !== roles.length - 1) throw new Error('Invalid room addresses');
        const addresses = [masterAddress, ...roomAddresses];
        if (!addresses.every(privateAddress) || new Set(addresses).size !== roles.length) throw new Error('Invalid workstation addresses');
        inventory = { masterAddress, roomAddresses };
        witnesses = await Promise.all(files.map(async receipt => {
          const value = await readJson(receipt);
          return readWitness(value?.schemaVersion === 1 && value.complete === true ? value.networkWitness : value, id);
        }));
        witnesses.sort((a, b) => a.workstation - b.workstation);
        if (witnesses.some((witness, index) => witness.workstation !== index)) throw new Error('Missing workstation role');
      } catch {
        if (current()) status.textContent = '請選取六個相異的私有 IPv4 位址，以及本輪主控與五房各一份有效格式的 JSON 回條。每檔上限 16 KiB。';
        return;
      }
      if (!current()) return;
      status.textContent = '正在核對實際連線來源與簽章…';
      const value = await api('/operator-network/verify', 'POST', { challenge: id, inventory, witnesses });
      if (!current()) return;
      const expected = [inventory.masterAddress, ...inventory.roomAddresses];
      if (value?.challenge !== id || !Array.isArray(value.workstationAddresses) || value.workstationAddresses.length !== roles.length
          || expected.some((address, index) => value.workstationAddresses[index] !== address)
          || witnesses.some(witness => witness.listener !== value.listener || witness.port !== value.port))
        throw new Error('Unexpected verification response');
      result.replaceChildren(...expected.map((address, index) => {
        const row = document.createElement('li');
        row.textContent = `${roles[index]} · ${address}`;
        return row;
      }));
      status.textContent = `本輪已核對六台工作站的角色與連線來源。管理端 ${value.listener}:${value.port}。`;
    });
  });
  return { active(on) {
    active = on;
    if (!on) {
      generation++;
      pending = false;
      challengeInput.value = inventoryInput.value = receiptsInput.value = '';
      panel.open = false;
      clear();
    } else update();
  } };
}
