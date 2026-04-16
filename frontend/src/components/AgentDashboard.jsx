import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

// ✅ THE NEW UNIFIED WAY
const PROTECTED_URL = 'http://localhost:8000/api/v1/premium-data';
const ORACLE_URL = 'http://localhost:8000/attest';
const AGENT_ADDRESS = 'EUKRBWJBKMYRCRQOHFGEUMXGK2JDXESZ5A2W5SJVJVTF7BW5CWBSUG422Q';

export default function AgentDashboard() {
  const [logs, setLogs] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [verdict, setVerdict] = useState(null);
  const [score, setScore] = useState(null);
  const [features, setFeatures] = useState(null);
  const [txHistory, setTxHistory] = useState([]);
  const [premiumData, setPremiumData] = useState(null);
  const [stats, setStats] = useState({ total: 0, safe: 0, blocked: 0, spend: 0 });
  const [manualValues, setManualValues] = useState({
    amount: '2.2', velocity: '5', timing: '720', wallet: 'weather_api_1'
  });
  const terminalRef = useRef(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  const addLog = (message, type = 'info') => {
    setLogs(prev => [...prev, {
      time: new Date().toLocaleTimeString('en', { hour12: false }),
      message, type
    }]);
  };

  const updateStats = (verdict, amountMicro) => {
    setStats(prev => ({
      total: prev.total + 1,
      safe: prev.safe + (verdict === 'SAFE' ? 1 : 0),
      blocked: prev.blocked + (verdict !== 'SAFE' ? 1 : 0),
      spend: prev.spend + (verdict === 'SAFE' ? amountMicro : 0)
    }));
  };

  const buildPayload = (recipientAddress, amountMicro, velocity, timingDelta) => ({
    agent_address: AGENT_ADDRESS,
    recipient_address: recipientAddress,
    amount_micro: amountMicro,
    velocity: velocity,
    timing_delta: timingDelta
  });

  // ================== REAL END-TO-END EXECUTE FLOW ==================
  const executeFlow = async (payload, manualMode = false) => {
    setIsProcessing(true);
    setPremiumData(null);
    setLogs([]);

    addLog('🤖 [AGENT] Initializing request to Protected API...', 'info');
    addLog('🌐 [API] GET /api/v1/premium-data', 'info');
    addLog('🛑 [API] 402 Payment Required intercepted', 'warning');
    addLog('🛡️ [AGENIZ] Sending to ML Oracle for scoring...', 'info');

    const amountAlgo = payload.amount_micro / 1e6;
    setFeatures({
      amount: amountAlgo,
      velocity: payload.velocity,
      timing: payload.timing_delta,
      wallet: payload.recipient_address
    });

    let oracleData;
    try {
      const res = await axios.post(ORACLE_URL, payload);
      oracleData = res.data;
    } catch (e) {
      addLog('❌ [AGENIZ] Oracle unreachable — is port 8000 running?', 'error');
      setIsProcessing(false);
      return;
    }

    const v = oracleData.verdict;
    const s = oracleData.confidence_score;
    setVerdict(v);
    setScore(s);
    updateStats(v, payload.amount_micro);

    if (v === 'SAFE') {
      addLog(`✅ [AGENIZ] SAFE — Confidence Score: +${s}`, 'success');
      addLog(`🔑 [AGENIZ] Signature received`, 'success');

      addLog('🔗 [ALGORAND] Executing real payment on smart contract...', 'info');

      try {
        const contractCall = await axios.post('http://localhost:8000/execute-payment', {
          agent_address: payload.agent_address,
          amount_micro: payload.amount_micro,
          recipient_address: payload.recipient_address,
          signature_b64: oracleData.signature_b64
        });

        const realTxId = contractCall.data.tx_id;

        addLog(`💸 [ALGORAND] Confirmed! TxID: ${realTxId}`, 'success');
        addLog('🤖 [AGENT] Retrying API with payment receipt...', 'info');

        const finalRes = await axios.get(PROTECTED_URL, {
          headers: { 'x-payment-receipt': realTxId }
        });

        setPremiumData(finalRes.data);
        addLog('🎉 [API] Premium resource unlocked!', 'success');

        setTxHistory(prev => [{ 
          verdict: 'SAFE', 
          txId: realTxId, 
          time: new Date().toLocaleTimeString() 
        }, ...prev].slice(0, 10));

      } catch (err) {
        console.error("Payment Execution Error:", err);
        const errorMsg = err.response?.data?.detail || err.message || "Blockchain execution failed";
        addLog(`❌ [ALGORAND] Error: ${errorMsg}`, 'error');
      }

    } else {
      const reason = oracleData.debug?.reason || 'ML anomaly detected';
      addLog(`❌ [AGENIZ] BLOCKED — ${v}`, 'error');
      addLog(`🔍 [AGENIZ] Reason: ${reason}`, 'error');
      addLog('🚫 No signature issued. Transaction dropped.', 'error');
      setTxHistory(prev => [{ verdict: 'BLOCKED', txId: null, time: new Date().toLocaleTimeString() }, ...prev].slice(0, 10));
    }

    setIsProcessing(false);
  };

  const runSafe = () => executeFlow(buildPayload('EUKRBWJBKMYRCRQOHFGEUMXGK2JDXESZ5A2W5SJVJVTF7BW5CWBSUG422Q', 1000000, 5, 720));

  const runAttack = (type) => {
    const attacks = {
      volume:   { recipient_address: 'weather_api_1', amount_micro: 15000000, velocity: 5,   timing_delta: 720 },
      velocity: { recipient_address: 'weather_api_1', amount_micro: 1000000,  velocity: 100, timing_delta: 10  },
      wallet:   { recipient_address: 'hacker_wallet_99', amount_micro: 1000000, velocity: 5, timing_delta: 720 },
    };
    addLog(`🔴 [ATTACK] Simulating ${type} attack...`, 'warning');
    executeFlow({ agent_address: AGENT_ADDRESS, ...attacks[type] });
  };

  const runManual = () => {
    const payload = buildPayload(
      manualValues.wallet,
      Math.round(parseFloat(manualValues.amount) * 1e6),
      parseInt(manualValues.velocity),
      parseFloat(manualValues.timing)
    );
    addLog(`🔬 [PROBE] amount=${manualValues.amount} ALGO | velocity=${manualValues.velocity}/hr | timing=${manualValues.timing}s | wallet=${manualValues.wallet}`, 'info');
    executeFlow(payload, true);
  };

  const knownWallets = ['weather_api_1', 'traffic_api_2', 'server_cost_3'];
  const getScoreBarWidth = () => {
    if (score === null) return '50%';
    if (score === -1) return '2%';
    return Math.min(95, Math.max(5, 50 + score * 200)) + '%';
  };
  const getScoreColor = () => verdict === 'SAFE' ? '#00ff88' : '#ff3355';

  return (
    <div style={{ minHeight: '100vh', background: '#050810', color: '#e2e8f0', padding: '24px', fontFamily: "'Syne', sans-serif" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');
        * { box-sizing: border-box; }
        body { background: #050810; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1e2d45; border-radius: 2px; }
        input, select { outline: none; }
        input:focus, select:focus { border-color: #00ff88 !important; }
        .btn-safe { transition: all 0.2s; }
        .btn-safe:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(0,255,136,0.3); }
        .attack-btn:hover:not(:disabled) { background: rgba(255,51,85,0.12) !important; }
        .btn-manual:hover:not(:disabled) { background: rgba(0,102,255,0.2) !important; }
        @keyframes fadeIn { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:translateY(0); } }
        @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }
        .log-line { animation: fadeIn 0.2s ease; }
        .grid-bg {
          position: fixed; inset: 0; pointer-events: none; z-index: 0;
          background-image: linear-gradient(rgba(0,255,136,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,136,0.03) 1px, transparent 1px);
          background-size: 40px 40px;
        }
      `}</style>

      <div className="grid-bg" />
      <div style={{ position: 'relative', zIndex: 1, maxWidth: 1400, margin: '0 auto' }}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28, paddingBottom: 20, borderBottom: '1px solid #1e2d45' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 40, height: 40, background: 'linear-gradient(135deg,#00ff88,#0066ff)', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20 }}>🛡️</div>
            <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.5px' }}>Ageniz <span style={{ color: '#4a5568', fontWeight: 400 }}>| Web3 Firewall</span></h1>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 14px', borderRadius: 100, border: '1px solid rgba(0,255,136,0.2)', background: 'rgba(0,255,136,0.05)', fontFamily: 'Space Mono', fontSize: 11, color: '#00ff88' }}>
            <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#00ff88', animation: 'pulse 2s infinite' }} />
            Oracle Online · App ID  758871176
          </div>
        </div>

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 24 }}>
          {[
            { label: 'Total Requests', value: stats.total, color: '#00ff88', sub: 'this session' },
            { label: 'Approved', value: stats.safe, color: '#00ff88', sub: 'passed firewall' },
            { label: 'Blocked', value: stats.blocked, color: '#ff3355', sub: 'threats stopped' },
            { label: 'Daily Spend', value: (stats.spend / 1e6).toFixed(1), color: '#ffaa00', sub: '/ 5 ALGO limit' },
          ].map(s => (
            <div key={s.label} style={{ background: '#0c1020', border: '1px solid #1e2d45', borderRadius: 12, padding: '16px 20px', position: 'relative', overflow: 'hidden' }}>
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: s.color }} />
              <div style={{ fontFamily: 'Space Mono', fontSize: 10, color: '#4a5568', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>{s.label}</div>
              <div style={{ fontFamily: 'Space Mono', fontSize: 26, fontWeight: 700, color: s.color }}>{s.value}</div>
              <div style={{ fontSize: 11, color: '#4a5568', marginTop: 4, fontFamily: 'Space Mono' }}>{s.sub}</div>
            </div>
          ))}
        </div>

        {/* Main Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 20, marginBottom: 20 }}>

          {/* Left Controls */}
          <div style={{ background: '#0c1020', border: '1px solid #1e2d45', borderRadius: 14, overflow: 'hidden' }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid #1e2d45', display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'Space Mono', fontSize: 11, color: '#4a5568', textTransform: 'uppercase', letterSpacing: 1 }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#00ff88' }} /> Agent Simulation
            </div>
            <div style={{ padding: 20 }}>

              {/* Safe button */}
              <button className="btn-safe" onClick={runSafe} disabled={isProcessing}
                style={{ width: '100%', padding: '13px 20px', borderRadius: 10, border: 'none', cursor: 'pointer', background: 'linear-gradient(135deg,#00c96e,#00ff88)', color: '#050810', fontFamily: 'Syne', fontSize: 14, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: 10, opacity: isProcessing ? 0.5 : 1 }}>
                ⚡ Run Safe Transaction
              </button>

              {/* Attack Scenarios */}
              <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #1e2d45' }}>
                <div style={{ fontFamily: 'Space Mono', fontSize: 10, color: '#4a5568', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>⚠ Attack Scenarios</div>
                {[
                  { id: 'volume', label: '🔴 High Volume Attack', sub: '15 ALGO spike' },
                  { id: 'velocity', label: '🔴 Velocity Attack', sub: '100 txns/hr' },
                  { id: 'wallet', label: '🔴 Prompt Injection', sub: 'unknown wallet' },
                ].map(a => (
                  <button key={a.id} className="attack-btn" onClick={() => runAttack(a.id)} disabled={isProcessing}
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid rgba(255,51,85,0.2)', background: 'rgba(255,51,85,0.05)', color: '#ff7799', fontFamily: 'Space Mono', fontSize: 11, cursor: 'pointer', textAlign: 'left', marginBottom: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between', opacity: isProcessing ? 0.4 : 1 }}>
                    <span>{a.label}</span>
                    <span style={{ color: '#4a5568', fontSize: 10 }}>{a.sub}</span>
                  </button>
                ))}
              </div>

              {/* Manual Probe */}
              <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #1e2d45' }}>
                <div style={{ fontFamily: 'Space Mono', fontSize: 10, color: '#4a5568', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>🔬 Manual ML Probe</div>
                {[
                  { label: 'Amount (ALGO)', key: 'amount', type: 'number' },
                  { label: 'Velocity (txns/hr)', key: 'velocity', type: 'number' },
                  { label: 'Timing Delta (seconds)', key: 'timing', type: 'number' },
                ].map(f => (
                  <div key={f.key} style={{ marginBottom: 10 }}>
                    <label style={{ display: 'block', fontFamily: 'Space Mono', fontSize: 10, color: '#4a5568', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 5 }}>{f.label}</label>
                    <input type={f.type} value={manualValues[f.key]}
                      onChange={e => setManualValues(p => ({ ...p, [f.key]: e.target.value }))}
                      style={{ width: '100%', background: '#050810', border: '1px solid #1e2d45', borderRadius: 8, padding: '8px 12px', color: '#e2e8f0', fontFamily: 'Space Mono', fontSize: 12, transition: 'border-color 0.2s' }} />
                  </div>
                ))}
                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: 'block', fontFamily: 'Space Mono', fontSize: 10, color: '#4a5568', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 5 }}>Recipient Wallet</label>
                  <select value={manualValues.wallet} onChange={e => setManualValues(p => ({ ...p, wallet: e.target.value }))}
                    style={{ width: '100%', background: '#050810', border: '1px solid #1e2d45', borderRadius: 8, padding: '8px 12px', color: '#e2e8f0', fontFamily: 'Space Mono', fontSize: 11 }}>
                    <option value="weather_api_1">weather_api_1 (known)</option>
                    <option value="traffic_api_2">traffic_api_2 (known)</option>
                    <option value="server_cost_3">server_cost_3 (known)</option>
                    <option value="hacker_wallet_99">hacker_wallet_99 (unknown ⚠)</option>
                    <option value="drain_wallet_xyz">drain_wallet_xyz (unknown ⚠)</option>
                  </select>
                </div>
                <button className="btn-manual" onClick={runManual} disabled={isProcessing}
                  style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #0066ff', background: 'rgba(0,102,255,0.1)', color: '#66aaff', fontFamily: 'Space Mono', fontSize: 11, cursor: 'pointer', opacity: isProcessing ? 0.4 : 1 }}>
                  → Submit to ML Oracle
                </button>
              </div>

            </div>
          </div>

          {/* Right: Terminal + Score */}
          <div style={{ background: '#0c1020', border: '1px solid #1e2d45', borderRadius: 14, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid #1e2d45', display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'Space Mono', fontSize: 11, color: '#4a5568', textTransform: 'uppercase', letterSpacing: 1 }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#00ff88' }} />
              ageniz-core-execution-log
              <span style={{ marginLeft: 'auto', cursor: 'pointer' }} onClick={() => { setLogs([]); setVerdict(null); setScore(null); setFeatures(null); setPremiumData(null); }}>clear</span>
            </div>

            {/* Terminal */}
            <div ref={terminalRef} style={{ background: '#020408', flex: 1, minHeight: 300, overflowY: 'auto', padding: '16px 20px', fontFamily: 'Space Mono', fontSize: 12, lineHeight: 1.8 }}>
              {logs.length === 0 ? (
                <div style={{ color: '#4a5568', display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 8, fontSize: 11 }}>
                  <span style={{ fontSize: 20 }}>⬡</span> Awaiting Agent Execution...
                </div>
              ) : logs.map((log, i) => (
                <div key={i} className="log-line" style={{ display: 'flex', gap: 12 }}>
                  <span style={{ color: '#2d4a6b', flexShrink: 0 }}>[{log.time}]</span>
                  <span style={{ color: log.type === 'success' ? '#00ff88' : log.type === 'warning' ? '#ffaa00' : log.type === 'error' ? '#ff3355' : '#94a3b8', fontWeight: log.type === 'error' ? 700 : 400 }}>{log.message}</span>
                </div>
              ))}
            </div>

            {/* Score + Features */}
            <div style={{ padding: '16px 20px', borderTop: '1px solid #1e2d45' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <span style={{ fontFamily: 'Space Mono', fontSize: 10, color: '#4a5568', textTransform: 'uppercase', letterSpacing: 1 }}>ML Decision</span>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 12px', borderRadius: 6, fontFamily: 'Space Mono', fontSize: 11, fontWeight: 700,
                  background: verdict === 'SAFE' ? 'rgba(0,255,136,0.1)' : verdict ? 'rgba(255,51,85,0.1)' : 'rgba(74,85,104,0.2)',
                  color: verdict === 'SAFE' ? '#00ff88' : verdict ? '#ff3355' : '#4a5568',
                  border: `1px solid ${verdict === 'SAFE' ? 'rgba(0,255,136,0.2)' : verdict ? 'rgba(255,51,85,0.2)' : '#1e2d45'}` }}>
                  {verdict === 'SAFE' ? '✓ SAFE' : verdict ? '✕ ANOMALY' : '— IDLE'}
                </div>
              </div>

              <div style={{ background: '#050810', border: '1px solid #1e2d45', borderRadius: 8, padding: '12px 16px', marginBottom: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'Space Mono', fontSize: 10, color: '#4a5568', marginBottom: 8 }}>
                  <span>ANOMALY ←</span>
                  <span style={{ color: verdict ? getScoreColor() : '#4a5568', fontWeight: 700, fontSize: 13 }}>
                    {score === null ? '—' : score === -1 ? 'INSTANT BLOCK' : (score > 0 ? '+' : '') + score.toFixed(4)}
                  </span>
                  <span>→ SAFE</span>
                </div>
                <div style={{ height: 6, background: '#1e2d45', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ height: '100%', borderRadius: 3, width: getScoreBarWidth(), background: verdict ? getScoreColor() : '#4a5568', transition: 'width 0.6s cubic-bezier(0.4,0,0.2,1), background 0.3s' }} />
                </div>
              </div>

              {/* Feature breakdown */}
              {features && (
                <div>
                  <div style={{ fontFamily: 'Space Mono', fontSize: 10, color: '#4a5568', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>Feature Vector</div>
                  {[
                    { name: 'volume', value: features.amount.toFixed(2) + ' ALGO', pct: Math.min(100, (features.amount / 20) * 100), danger: features.amount > 5 },
                    { name: 'velocity', value: features.velocity + '/hr', pct: Math.min(100, (features.velocity / 100) * 100), danger: features.velocity > 20 },
                    { name: 'timing_δ', value: features.timing + 's', pct: Math.min(100, (features.timing / 1800) * 100), danger: features.timing < 60 },
                    { name: 'wallet', value: knownWallets.includes(features.wallet) ? features.wallet : '⚠ UNKNOWN', pct: knownWallets.includes(features.wallet) ? 33 : 95, danger: !knownWallets.includes(features.wallet) },
                  ].map(f => (
                    <div key={f.name} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8, fontFamily: 'Space Mono', fontSize: 11 }}>
                      <span style={{ color: '#4a5568', width: 80, flexShrink: 0 }}>{f.name}</span>
                      <div style={{ flex: 1, height: 4, background: '#1e2d45', borderRadius: 2, overflow: 'hidden' }}>
                        <div style={{ height: '100%', borderRadius: 2, width: f.pct + '%', background: f.danger ? '#ff3355' : '#0066ff', transition: 'width 0.5s ease' }} />
                      </div>
                      <span style={{ color: f.danger ? '#ff3355' : '#e2e8f0', width: 70, textAlign: 'right', fontSize: 10, flexShrink: 0 }}>{f.value}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Bottom Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

          {/* Tx History */}
          <div style={{ background: '#0c1020', border: '1px solid #1e2d45', borderRadius: 14, overflow: 'hidden' }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid #1e2d45', fontFamily: 'Space Mono', fontSize: 11, color: '#4a5568', textTransform: 'uppercase', letterSpacing: 1, display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#00ff88' }} /> Transaction History
            </div>
            <div style={{ padding: '8px 16px' }}>
              {txHistory.length === 0 ? (
                <div style={{ color: '#4a5568', fontFamily: 'Space Mono', fontSize: 11, textAlign: 'center', padding: 20 }}>No transactions yet</div>
              ) : txHistory.map((tx, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: i < txHistory.length - 1 ? '1px solid #1e2d45' : 'none', fontFamily: 'Space Mono', fontSize: 11 }}>
                  <span style={{ padding: '3px 8px', borderRadius: 4, fontSize: 10, fontWeight: 700, flexShrink: 0, background: tx.verdict === 'SAFE' ? 'rgba(0,255,136,0.1)' : 'rgba(255,51,85,0.1)', color: tx.verdict === 'SAFE' ? '#00ff88' : '#ff3355' }}>{tx.verdict}</span>
                  <span style={{ color: '#0066ff', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{tx.txId || '— blocked'}</span>
                  <span style={{ color: '#4a5568', flexShrink: 0 }}>{tx.time}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Premium Data */}
          <div style={{ background: '#0c1020', border: '1px solid #1e2d45', borderRadius: 14, overflow: 'hidden' }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid #1e2d45', fontFamily: 'Space Mono', fontSize: 11, color: '#4a5568', textTransform: 'uppercase', letterSpacing: 1, display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#0066ff' }} /> Premium API Payload
            </div>
            <div style={{ padding: 20 }}>
              {premiumData ? (
                <pre style={{ fontFamily: 'Space Mono', fontSize: 11, color: '#66aaff', lineHeight: 1.8, overflow: 'auto', maxHeight: 200 }}>{JSON.stringify(premiumData, null, 2)}</pre>
              ) : (
                <div style={{ color: '#4a5568', fontFamily: 'Space Mono', fontSize: 11, textAlign: 'center', padding: 20 }}>Awaiting successful transaction...</div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}